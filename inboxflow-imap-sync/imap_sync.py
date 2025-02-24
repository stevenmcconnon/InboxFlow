import os
import logging
import asyncpg
import asyncio
from imapclient import IMAPClient
from email.parser import BytesParser
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Environment configuration
EMAIL_SERVER = os.getenv("EMAIL_SERVER", "imap.mail.yahoo.com")
EMAIL_USER = os.getenv("EMAIL_USER", "your_email@yahoo.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_app_password")
DB_URL = os.getenv("DB_URL")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))  # Configurable batch size

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

logger.info("Environment loaded. (Sensitive values are not logged.)")

####################################
# Database helper functions
####################################
async def get_folder_last_sync(db_pool, folder):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT last_sync FROM folder_sync WHERE folder = $1", folder)
        return row["last_sync"] if row else None

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

####################################
# IMAP Connection using imapclient
####################################
def connect_imap():
    try:
        client = IMAPClient(EMAIL_SERVER, use_uid=True)
        client.login(EMAIL_USER, EMAIL_PASSWORD)
        logger.info("✅ Connected to IMAP server.")
        return client
    except Exception as e:
        logger.error(f"IMAP connection error: {e}")
        return None

####################################
# Fetch all folders
####################################
def get_folders(client):
    try:
        folders = client.list_folders()
        folder_names = [folder[2] for folder in folders]
        logger.info(f"📂 Discovered folders: {folder_names}")
        return folder_names
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        return []

####################################
# Fetch email UIDs (Paginated)
####################################
def search_emails(client, folder):
    try:
        client.select_folder(folder)
        uids = client.search(["ALL"])
        uids = sorted(uids)

        # Split into batches of 100
        batches = [uids[i:i+BATCH_SIZE] for i in range(0, len(uids), BATCH_SIZE)]
        logger.info(f"📩 Folder '{folder}': Found {len(uids)} UIDs, divided into {len(batches)} batches.")
        return batches
    except Exception as e:
        logger.error(f"Error searching emails in folder '{folder}': {e}")
        return []

####################################
# Fetch email headers (Batch Processing)
####################################
def fetch_headers_batch(client, folder, uid_batch):
    try:
        client.select_folder(folder)
        headers = client.fetch(uid_batch, ["RFC822.HEADER"])
        header_map = {}

        for uid, data in headers.items():
            raw_header = data[b'RFC822.HEADER']
            header_text = raw_header.decode(errors="ignore")
            header_map[str(uid)] = header_text  # Store UIDs as strings

        logger.info(f"✅ Retrieved headers for {len(header_map)} emails in folder '{folder}'.")
        return header_map
    except Exception as e:
        logger.error(f"Error fetching headers for UIDs {uid_batch}: {e}")
        return {}

####################################
# Parse header to extract metadata
####################################
def parse_header(header):
    subject, sender, has_attachment = "No Subject", "Unknown", False
    for line in header.splitlines():
        if line.startswith("Subject:"):
            subject = line[len("Subject:"):].strip()
        elif line.startswith("From:"):
            sender = line[len("From:"):].strip()
        elif "multipart/mixed" in line.lower():
            has_attachment = True
    return subject, sender, has_attachment

####################################
# Store email metadata in bulk
####################################
async def store_email_headers(db_pool, headers, folder):
    if not headers:
        return
    
    query = """
    INSERT INTO emails (id, subject, sender, last_synced, folder, has_attachment, status)
    VALUES ($1, $2, $3, $4, $5, $6, 'pending')
    ON CONFLICT (id) DO UPDATE 
        SET subject = EXCLUDED.subject,
            sender = EXCLUDED.sender,
            last_synced = EXCLUDED.last_synced,
            folder = EXCLUDED.folder,
            has_attachment = EXCLUDED.has_attachment
    """
    async with db_pool.acquire() as conn:
        await conn.executemany(query, headers)
    
    logger.info(f"✅ Stored {len(headers)} email headers in folder '{folder}'.")

####################################
# Process a single folder (Parallel Processing)
####################################
async def process_folder(client, folder, db_pool):
    logger.info(f"📂 Processing folder '{folder}'")

    uid_batches = search_emails(client, folder)
    
    for batch in uid_batches:
        headers = fetch_headers_batch(client, folder, batch)
        
        # Convert headers into database-ready tuples
        header_data = [
            (uid, *parse_header(header), datetime.utcnow(), folder)
            for uid, header in headers.items()
        ]
        
        await store_email_headers(db_pool, header_data, folder)

    await update_folder_last_sync(db_pool, folder, datetime.utcnow())

####################################
# Process all folders in parallel
####################################
async def process_all_folders(db_pool):
    client = connect_imap()
    if not client:
        return

    folders = get_folders(client)

    # Process all folders in parallel
    await asyncio.gather(*(process_folder(client, folder, db_pool) for folder in folders))

    client.logout()

####################################
# Main Lambda Handler
####################################
async def main_handler(event):
    logger.info("🚀 Starting IMAP sync process.")
    db_pool = await asyncpg.create_pool(DB_URL)

    try:
        await process_all_folders(db_pool)
    finally:
        await db_pool.close()

    logger.info("✅ IMAP sync process completed.")
    return {"status": "completed"}

def lambda_handler(event, context):
    logger.info("Lambda invoked. Starting IMAP sync...")
    return asyncio.run(main_handler(event))

if __name__ == "__main__":
    test_event = {}
    result = asyncio.run(main_handler(test_event))
    print(result)