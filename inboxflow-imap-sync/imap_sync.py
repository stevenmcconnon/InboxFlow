import os
import asyncio
import aioimaplib
import asyncpg
import logging
import re
from email.parser import BytesParser
from datetime import datetime
from dotenv import load_dotenv
import sys

# Load environment variables from .env
load_dotenv()

# Environment configuration
EMAIL_SERVER = os.getenv("EMAIL_SERVER", "imap.mail.yahoo.com")
EMAIL_USER = os.getenv("EMAIL_USER", "you@example.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "REDACTED_APP_PASSWORD")
DB_URL = os.getenv("DB_URL")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))  # Configurable batch size

# Configure logging: flush logs to STDOUT immediately
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

logger.info("Environment loaded. (Sensitive values are not logged.)")

####################################
# Database helper functions for per-folder last sync
####################################
async def get_folder_last_sync(db_pool, folder):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT last_sync FROM folder_sync WHERE folder = $1", folder)
        last_sync = row["last_sync"] if row else None
        logger.info(f"Folder '{folder}': last sync marker = {last_sync}")
        return last_sync

async def update_folder_last_sync(db_pool, folder, timestamp):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO folder_sync (folder, last_sync)
            VALUES ($1, $2)
            ON CONFLICT (folder) DO UPDATE SET last_sync = EXCLUDED.last_sync
            """,
            folder, timestamp
        )
    logger.info(f"Updated last sync marker for folder '{folder}' to {timestamp}")

####################################
# IMAP Connection
####################################
async def connect_imap():
    try:
        client = aioimaplib.IMAP4_SSL(EMAIL_SERVER)
        await client.wait_hello_from_server()
        await client.login(EMAIL_USER, EMAIL_PASSWORD)
        logger.info("Connected to IMAP server.")
        return client
    except Exception as e:
        logger.error(f"IMAP connection error: {e}. Retrying in 10 seconds...")
        await asyncio.sleep(10)
        return await connect_imap()

####################################
# Dynamic Folder Discovery
####################################
async def get_folders():
    client = await connect_imap()
    try:
        logger.info("Listing all folders using client.list('\"\"', '\"*\"')...")
        resp = await client.list('""', '"*"')
        folders = []
        for line in resp.lines:
            try:
                decoded = line.decode(errors="ignore")
                logger.debug(f"Raw folder line: {decoded}")
                match = re.search(r' "([^"]+)"$', decoded)
                if match:
                    folder_name = match.group(1)
                    folders.append(folder_name)
            except Exception as ex:
                logger.error(f"Error parsing folder line: {ex}")
        logger.info(f"Discovered folders: {folders}")
        return folders
    except Exception as e:
        logger.error(f"Error during folder discovery: {e}")
        return []
    finally:
        await client.logout()
        

####################################
# Search Emails
####################################
async def search_emails(client, last_sync):
    try:
        logger.info("Fetching last 100 email UIDs using FETCH instead of SEARCH")

        # Get all UIDs with FETCH
        resp = await client.uid("FETCH", "1:*", "(UID)")
        if resp.result != "OK":
            logger.error(f"Error fetching UIDs. Response: {resp}")
            return []

        # Extract UIDs
        uids = []
        for line in resp.lines:
            try:
                decoded_line = line.decode(errors="ignore")
                match = re.search(r"UID (\d+)", decoded_line)
                if match:
                    uids.append(match.group(1))
            except Exception as e:
                logger.error(f"Error parsing UID line: {e}")

        if not uids:
            logger.warning("No UIDs found. Mailbox may be empty.")
            return []

        # Get only the last 100 messages
        last_100_msgs = uids[-100:] if len(uids) > 100 else uids
        logger.info(f"Fetched {len(last_100_msgs)} UIDs (most recent emails).")
        return last_100_msgs

    except Exception as e:
        logger.error(f"Exception during email fetch: {e}")
        return []

    

####################################
# Batch fetching of headers (combined fetch for a list of message sequence numbers)
####################################
async def fetch_headers_batch(client, uid_batch):
    try:
        uid_list = ",".join(uid_batch)
        logger.info(f"Fetching headers for batch: {uid_list}")
        # Use UID FETCH even if search was non-UID; many servers allow UID FETCH if message sequence numbers are used.
        command = f"UID FETCH {uid_list} (BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE CONTENT-TYPE)])"
        resp = await client.send(command)
        if resp.result != "OK":
            logger.error(f"Error fetching headers for batch: {uid_list}")
            return {}
        headers = {}
        for line in resp.lines:
            try:
                decoded_line = line.decode(errors="ignore")
                if "FETCH" in decoded_line:
                    parts = decoded_line.split(" ")
                    if len(parts) > 1 and parts[1].isdigit():
                        uid = parts[1]
                        headers[uid] = decoded_line
            except Exception as e:
                logger.error(f"Error parsing header line: {e}")
        logger.info(f"Batch {uid_list}: Fetched headers for UIDs: {list(headers.keys())}")
        return headers
    except Exception as e:
        logger.error(f"Exception in fetch_headers_batch: {e}")
        return {}

####################################
# Parse header to extract metadata and attachment flag
####################################
def parse_header(header):
    subject = "No Subject"
    sender = "Unknown"
    has_attachment = False
    for line in header.splitlines():
        if line.startswith("Subject:"):
            subject = line[len("Subject:"):].strip()
        elif line.startswith("From:"):
            sender = line[len("From:"):].strip()
        elif line.startswith("Content-Type:"):
            if "multipart/mixed" in line.lower():
                has_attachment = True
    return subject, sender, has_attachment

####################################
# Store email header (upsert) into the database
####################################
async def store_email_header(db_pool, uid, header, folder):
    try:
        subject, sender, has_attachment = parse_header(header)
        last_synced = datetime.utcnow()
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO emails (id, subject, sender, last_synced, folder, has_attachment, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE 
                    SET subject = EXCLUDED.subject,
                        sender = EXCLUDED.sender,
                        last_synced = EXCLUDED.last_synced,
                        folder = EXCLUDED.folder,
                        has_attachment = EXCLUDED.has_attachment
                """,
                uid, subject, sender, last_synced, folder, has_attachment, "pending"
            )
        logger.info(f"Stored header for UID {uid} in folder '{folder}'")
    except Exception as e:
        logger.error(f"Error storing header for UID {uid} in folder '{folder}': {e}")

####################################
# Cleanup deleted emails for a folder
####################################
async def cleanup_deleted_emails(folder, server_uids, db_pool):
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT id FROM emails WHERE folder = $1", folder)
            stored_uids = {row["id"] for row in rows}
            current_uids = set(server_uids)
            uids_to_delete = stored_uids - current_uids
            for uid in uids_to_delete:
                await conn.execute("DELETE FROM emails WHERE id = $1 AND folder = $2", uid, folder)
                logger.info(f"Deleted UID {uid} from folder '{folder}' (no longer on server).")
    except Exception as e:
        logger.error(f"Error during cleanup in folder '{folder}': {e}")

####################################
# Process a batch: Each batch uses its own IMAP connection for concurrency.
####################################
async def process_batch(uid_batch, folder, db_pool):
    logger.info(f"Processing batch in folder '{folder}': {uid_batch}")
    client = await connect_imap()
    try:
        await client.select(f'"{folder}"')
        headers = await fetch_headers_batch(client, uid_batch)
        tasks = [store_email_header(db_pool, uid, header, folder) for uid, header in headers.items()]
        if tasks:
            await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Error processing batch in folder '{folder}': {e}")
    finally:
        await client.logout()

####################################
# Process a single folder: select folder, search emails, process batches concurrently, update folder marker.
####################################
async def process_folder(folder, db_pool):
    logger.info(f"Starting processing for folder '{folder}'")
    client = await connect_imap()
    try:
        # Attempt to select the folder
        await client.select(f'"{folder}"')
    except Exception as e:
        logger.error(f"Error selecting folder '{folder}': {e}")
        await client.logout()
        return

    # Retrieve last_sync from DB
    last_sync = await get_folder_last_sync(db_pool, folder)
    # Search for emails (could fail or return 0 messages if the server rejects the command)
    uids = await search_emails(client, last_sync)

    # If we got nothing, skip updating last_sync
    if not uids:
        logger.warning(
            f"No messages found or search failed for folder '{folder}'. "
            f"Not updating last_sync."
        )
        await client.logout()
        return

    # We have some message sequence numbers—proceed with normal sync
    logger.info(f"Folder '{folder}': {len(uids)} message sequence numbers found.")
    await client.logout()

    # Batch the UIDs for concurrent processing
    batches = [uids[i : i + BATCH_SIZE] for i in range(0, len(uids), BATCH_SIZE)]
    logger.info(f"Folder '{folder}': Divided into {len(batches)} batches.")

    # Process each batch concurrently
    await asyncio.gather(*(process_batch(batch, folder, db_pool) for batch in batches))

    # Update the folder's last_sync marker only if we actually fetched messages
    await update_folder_last_sync(db_pool, folder, datetime.utcnow())

    # Cleanup any emails in DB that are no longer present on the server
    await cleanup_deleted_emails(folder, uids, db_pool)

    logger.info(f"Completed processing for folder '{folder}'")

####################################
# Discover folders and process each sequentially (can later be parallelized)
####################################
async def process_all_folders(db_pool):
    folders = await get_folders()
    logger.info(f"Processing {len(folders)} folders.")
    for folder in folders:
        logger.info(f"Processing folder: {folder}")
        await process_folder(folder, db_pool)

####################################
# Fetch full email (for lazy loading on demand)
####################################
async def fetch_full_email(client, uid):
    try:
        resp = await client.uid("FETCH", uid, "(RFC822)")
        if resp.result == "OK" and resp.lines:
            full_email = b"".join(resp.lines)
            logger.info(f"Fetched full email for UID {uid}")
            return full_email
        else:
            logger.error(f"Failed to fetch full email for UID {uid}")
            return None
    except Exception as e:
        logger.error(f"Exception fetching full email for UID {uid}: {e}")
        return None

####################################
# Main handler for Lambda
####################################
async def main_handler(event):
    logger.info("IMAP sync process started - v1.0.0")
    db_pool = await asyncpg.create_pool(DB_URL)
    try:
        await process_all_folders(db_pool)
    finally:
        await db_pool.close()
    logger.info("IMAP sync process completed.")
    return {"status": "completed"}

def lambda_handler(event, context):
    logger.info("Lambda invoked. Starting IMAP sync 0.1...")
    return asyncio.run(main_handler(event))

if __name__ == "__main__":
    test_event = {}
    result = asyncio.run(main_handler(test_event))
    print(result)