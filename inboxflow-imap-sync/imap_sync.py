import asyncio
import aioimaplib
import asyncpg
import logging
import os
import boto3
import json
from email.parser import BytesParser

# Configuration from environment or defaults
EMAIL_SERVER = os.getenv("EMAIL_SERVER", "imap.mail.yahoo.com")
EMAIL_USER = os.getenv("EMAIL_USER", "you@example.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "REDACTED_APP_PASSWORD")  # app password
DB_URL = os.getenv("DB_URL")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
LAMBDA_FUNCTION_NAME = os.getenv("AWS_LAMBDA_FUNCTION_NAME")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

async def connect_imap():
    """
    Establish and return an asynchronous IMAP connection using aioimaplib.
    Retries on failure.
    """
    try:
        client = aioimaplib.IMAP4_SSL(EMAIL_SERVER)
        await client.wait_hello_from_server()
        await client.login(EMAIL_USER, EMAIL_PASSWORD)
        await client.select("INBOX")
        logger.info("Connected to IMAP server.")
        return client
    except Exception as e:
        logger.error(f"IMAP connection error: {e}. Retrying in 10 seconds...")
        await asyncio.sleep(10)
        return await connect_imap()

async def fetch_uids(client):
    """
    Fetch all message UIDs from the server.
    """
    resp = await client.uid("SEARCH", "ALL")
    if resp.result != 'OK':
        logger.error("Error fetching UIDs.")
        return []
    # Combine response lines and split into UIDs.
    uids_line = b" ".join(resp.lines).decode()
    uids = uids_line.split()
    return uids

async def bulk_fetch_headers(client, uid_list):
    """
    Fetch email headers in bulk (FROM, SUBJECT, DATE) for the given list of UIDs.
    Here we concurrently pipeline header fetches.
    """
    headers = {}
    async def fetch_header(uid):
        resp = await client.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        if resp.result == 'OK' and resp.lines:
            header = b" ".join(resp.lines).decode(errors="ignore")
            headers[uid] = header
        else:
            logger.error(f"Failed to fetch header for UID {uid}")
    await asyncio.gather(*(fetch_header(uid) for uid in uid_list))
    return headers

async def fetch_full_email(client, uid):
    """
    Fetch the full email (RFC822) for a given UID.
    """
    resp = await client.uid("FETCH", uid, "(RFC822)")
    if resp.result == 'OK' and resp.lines:
        raw_email = b"".join(resp.lines)
        return raw_email
    else:
        logger.error(f"Failed to fetch full email for UID {uid}")
        return None

async def fetch_and_process(client, uid, db_pool):
    """
    For a given UID, fetch the full email, parse it, and store it in the database.
    """
    raw_email = await fetch_full_email(client, uid)
    if raw_email:
        try:
            msg = BytesParser().parsebytes(raw_email)
            subject = msg.get("Subject", "No Subject")
            sender = msg.get("From", "Unknown Sender")
            content = raw_email.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Error parsing email {uid}: {e}")
            subject = "Parsing Error"
            sender = "Parsing Error"
            content = raw_email.decode("utf-8", errors="ignore")
        async with db_pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO emails (id, subject, sender, content, status)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    uid, subject, sender, content, "pending"
                )
                logger.info(f"Email {uid} inserted into DB.")
            except Exception as e:
                logger.error(f"DB insertion error for email {uid}: {e}")

async def process_batch(uid_batch, db_pool):
    """
    Process a batch of UIDs concurrently:
      - Optionally fetch headers for preliminary filtering/display.
      - Concurrently fetch full emails and store them.
    """
    client = await connect_imap()
    if not client:
        logger.error("IMAP client connection failed for batch processing.")
        return

    # Fetch headers concurrently (this can be used for lightweight processing if desired)
    headers = await bulk_fetch_headers(client, uid_batch)
    logger.info(f"Fetched headers for UIDs: {list(headers.keys())}")

    # Concurrently fetch and process each email in the batch
    await asyncio.gather(*(fetch_and_process(client, uid, db_pool) for uid in uid_batch))

    await client.logout()

async def cleanup_deleted_emails(all_server_uids, db_pool):
    """
    Remove emails from the database that are no longer present on the server.
    """
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id FROM emails")
        db_uids = {row["id"] for row in rows}
        server_uids_set = set(all_server_uids)
        uids_to_delete = db_uids - server_uids_set
        for uid in uids_to_delete:
            try:
                await conn.execute("DELETE FROM emails WHERE id = $1", uid)
                logger.info(f"Email {uid} deleted from DB (cleanup).")
            except Exception as e:
                logger.error(f"DB deletion error for email {uid}: {e}")

async def invoke_lambda(next_index):
    """
    Asynchronously re-invoke the AWS Lambda function for the next batch.
    """
    lambda_client = boto3.client("lambda")
    payload = {"start_index": next_index}
    try:
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps(payload)
        )
        logger.info(f"Lambda re-invoked for batch starting at index {next_index}: {response}")
    except Exception as e:
        logger.error(f"Failed to invoke Lambda for next batch: {e}")

async def main_handler(event):
    """
    Main asynchronous handler:
      - Connects to IMAP to retrieve all UIDs.
      - Processes emails in batches using asynchronous techniques.
      - Cleans up deleted emails.
      - Re-invokes Lambda if additional batches remain.
    """
    start_index = int(event.get("start_index", 0))
    logger.info(f"Lambda invoked with start_index: {start_index}")

    # Initial connection to get all UIDs
    client = await connect_imap()
    uids = await fetch_uids(client)
    total_msgs = len(uids)
    logger.info(f"Total emails on server: {total_msgs}")
    await client.logout()

    # Set up asynchronous database connection pool
    db_pool = await asyncpg.create_pool(DB_URL)
    try:
        for i in range(start_index, total_msgs, BATCH_SIZE):
            uid_batch = uids[i:i+BATCH_SIZE]
            await process_batch(uid_batch, db_pool)
            # If there are more emails, re-invoke Lambda for the next batch
            if i + BATCH_SIZE < total_msgs:
                await invoke_lambda(i + BATCH_SIZE)
    finally:
        await cleanup_deleted_emails(uids, db_pool)
        await db_pool.close()

    return {"status": "completed", "processed": total_msgs, "total": total_msgs}

def lambda_handler(event, context):
    return asyncio.run(main_handler(event))

if __name__ == "__main__":
    # For local testing:
    test_event = {"start_index": 0}
    result = asyncio.run(main_handler(test_event))
    print(result)