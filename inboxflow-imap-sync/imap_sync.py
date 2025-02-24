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
    logger.info(f"✅ Updated last sync marker for folder '{folder}' to {timestamp}")


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
    """
    Fetches all UIDs in this folder and returns the last 100 (sorted ascending).
    Uses resp.lines instead of resp.data.
    """
    try:
        logger.info("Fetching last 100 email UIDs using FETCH instead of SEARCH")

        # Example command: UID FETCH 1:* (UID)
        resp = await client.uid("FETCH", "1:*", "(UID)")
        if resp.result != "OK":
            logger.error(f"Error fetching UIDs. Response: {resp}")
            return []

        # In older aioimaplib, the server's raw reply is in resp.lines
        uids = []
        for raw_line in resp.lines:
            line = raw_line.decode(errors="ignore")
            # Typically looks like: '* 37 FETCH (UID 19 FLAGS (\Seen))'
            uid_match = re.search(r"UID (\d+)", line)
            if uid_match:
                uids.append(uid_match.group(1))

        if not uids:
            logger.warning("No UIDs found. Mailbox may be empty.")
            return []

        # Sort numerically, then keep only the last 100
        uids = sorted(uids, key=lambda x: int(x))
        last_100 = uids[-100:] if len(uids) > 100 else uids
        logger.info(f"Fetched {len(last_100)} UIDs (most recent emails).")

        return last_100

    except Exception as e:
        logger.error(f"Exception during email fetch: {e}")
        return []

####################################
# Batch fetching of headers (combined fetch for a list of message sequence numbers)
####################################
async def fetch_headers_batch(client, uid_batch):
    """
    Fetch email headers using multiple approaches (RFC822.HEADER, BODY[HEADER], or BODY[]).
    Logs every line to debug why headers might be missing.
    """
    try:
        uid_list = ",".join(uid_batch)
        logger.info(f"Fetching headers for batch: {uid_list}")

        # First, try fetching just the headers (this should work, but Yahoo may return NIL)
        resp = await client.uid("FETCH", uid_list, "(UID FLAGS RFC822.HEADER)")

        # Debug: Log everything the server sends back
        logger.debug(f"--- FETCH response result: {resp.result}")
        for i, raw_line in enumerate(resp.lines):
            logger.debug(f"FETCH line {i}: {raw_line.decode(errors='ignore')}")

        if resp.result != "OK":
            logger.error(f"Error fetching headers for batch {uid_list}: {resp}")
            return {}

        headers_map = {}
        current_uid = None
        buffer = []
        reading_header = False

        for raw_line in resp.lines:
            line = raw_line.decode(errors="ignore")

            # Debugging: Log raw line data
            logger.debug(f"Parsing line: {line}")

            # Start of a new FETCH response
            if line.startswith("* "):
                # Store previous UID's headers if any
                if current_uid and buffer:
                    headers_map[current_uid] = "\n".join(buffer)

                current_uid = None
                buffer.clear()
                reading_header = False

                # Extract UID from response line
                uid_match = re.search(r"UID (\d+)", line)
                if uid_match:
                    current_uid = uid_match.group(1)

                # Detect if headers will follow
                if "RFC822.HEADER" in line and line.strip().endswith("}"):
                    reading_header = True
                elif "RFC822.HEADER NIL" in line:
                    logger.warning(f"IMAP returned NIL for UID {current_uid}. Headers not available.")

            # If we hit just a ")", this closes the FETCH block
            elif line.strip() == ")":
                if current_uid and buffer:
                    headers_map[current_uid] = "\n".join(buffer)
                current_uid = None
                buffer.clear()
                reading_header = False

            # Otherwise, if we're in the header block, store the lines
            elif reading_header and current_uid:
                buffer.append(line)

        # Final save for last UID
        if current_uid and buffer:
            headers_map[current_uid] = "\n".join(buffer)

        logger.info(f"Fetched headers for UIDs: {list(headers_map.keys())}")

        # If still no headers, try BODY[HEADER.FIELDS]
        if not headers_map:
            logger.warning("RFC822.HEADER returned no headers. Trying BODY[HEADER.FIELDS]...")

            fields = "(DATE FROM TO CC SUBJECT CONTENT-TYPE)"
            resp = await client.uid("FETCH", uid_list, f"(UID FLAGS BODY[HEADER.FIELDS {fields}])")

            # Debug: Log raw response
            logger.debug(f"--- FETCH BODY[HEADER.FIELDS] response result: {resp.result}")
            for i, raw_line in enumerate(resp.lines):
                logger.debug(f"FETCH line {i}: {raw_line.decode(errors='ignore')}")

            if resp.result != "OK":
                logger.error(f"Error fetching headers using BODY[HEADER.FIELDS]: {resp}")
                return {}

            headers_map = {}
            current_uid = None
            buffer = []
            reading_header = False

            for raw_line in resp.lines:
                line = raw_line.decode(errors="ignore")
                logger.debug(f"Parsing line: {line}")

                if line.startswith("* "):
                    if current_uid and buffer:
                        headers_map[current_uid] = "\n".join(buffer)

                    current_uid = None
                    buffer.clear()
                    reading_header = False

                    uid_match = re.search(r"UID (\d+)", line)
                    if uid_match:
                        current_uid = uid_match.group(1)

                    if "BODY[HEADER.FIELDS" in line and line.strip().endswith("}"):
                        reading_header = True

                elif line.strip() == ")":
                    if current_uid and buffer:
                        headers_map[current_uid] = "\n".join(buffer)
                    current_uid = None
                    buffer.clear()
                    reading_header = False

                elif reading_header and current_uid:
                    buffer.append(line)

            logger.info(f"Fetched headers from BODY[HEADER.FIELDS]: {list(headers_map.keys())}")

        # If still no headers, last resort: Fetch full email headers using BODY[]
        if not headers_map:
            logger.warning("BODY[HEADER.FIELDS] also returned no headers. Trying BODY[] (full message)...")

            resp = await client.uid("FETCH", uid_list, "(UID FLAGS BODY[])")

            # Debug: Log raw response
            logger.debug(f"--- FETCH BODY[] response result: {resp.result}")
            for i, raw_line in enumerate(resp.lines):
                logger.debug(f"FETCH line {i}: {raw_line.decode(errors='ignore')}")

            if resp.result != "OK":
                logger.error(f"Error fetching full message using BODY[]: {resp}")
                return {}

            headers_map = {}
            current_uid = None
            buffer = []
            reading_header = False

            for raw_line in resp.lines:
                line = raw_line.decode(errors="ignore")
                logger.debug(f"Parsing line: {line}")

                if line.startswith("* "):
                    if current_uid and buffer:
                        headers_map[current_uid] = "\n".join(buffer)

                    current_uid = None
                    buffer.clear()
                    reading_header = False

                    uid_match = re.search(r"UID (\d+)", line)
                    if uid_match:
                        current_uid = uid_match.group(1)

                    if "BODY[" in line and line.strip().endswith("}"):
                        reading_header = True

                elif line.strip() == ")":
                    if current_uid and buffer:
                        headers_map[current_uid] = "\n".join(buffer)
                    current_uid = None
                    buffer.clear()
                    reading_header = False

                elif reading_header and current_uid:
                    buffer.append(line)

            logger.info(f"Fetched headers from BODY[]: {list(headers_map.keys())}")

        return headers_map

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
    """
    Parses and stores email headers in the database.
    """
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

        logger.info(f"Stored email UID {uid} in folder '{folder}'")

    except Exception as e:
        logger.error(f"Error storing email UID {uid} in folder '{folder}': {e}")


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

        headers_map = await fetch_headers_batch(client, uid_batch)
        if not headers_map:
            logger.warning(
                f"No headers found in batch for folder '{folder}', skipping DB insert."
            )
            return

        # Now store them in the DB
        tasks = []
        for uid, header in headers_map.items():
            tasks.append(store_email_header(db_pool, uid, header, folder))
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
        await client.select(f'"{folder}"')
    except Exception as e:
        logger.error(f"Error selecting folder '{folder}': {e}")
        await client.logout()
        return

    last_sync = await get_folder_last_sync(db_pool, folder)
    uids = await search_emails(client, last_sync)

    await client.logout()

    if not uids:
        logger.warning(
            f"No messages found in folder '{folder}', skipping last_sync update."
        )
        return

    logger.info(f"Folder '{folder}': {len(uids)} message sequence numbers found.")
    batches = [uids[i : i + BATCH_SIZE] for i in range(0, len(uids), BATCH_SIZE)]
    logger.info(f"Folder '{folder}': Divided into {len(batches)} batches.")

    await asyncio.gather(*(process_batch(b, folder, db_pool) for b in batches))

    # Update last_sync
    await update_folder_last_sync(db_pool, folder, datetime.utcnow())

    # Clean up emails that no longer exist on the server
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