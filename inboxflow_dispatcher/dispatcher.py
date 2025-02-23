import logging
import psycopg2
import time
from config import DB_URL

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def fetch_unprocessed_emails():
    """Fetches emails from PostgreSQL instead of IMAP."""
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT id, subject FROM emails WHERE status = 'pending'")
    emails = cursor.fetchall()
    conn.close()
    return emails

def process_emails():
    """Processes emails using database instead of IMAP."""
    emails = fetch_unprocessed_emails()
    for email in emails:
        logger.info(f"Processing email: {email[1]}")
        # Placeholder for classification or flow logic
        mark_as_processed(email[0])

def mark_as_processed(email_id):
    """Marks email as processed in DB."""
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE emails SET status = 'processed' WHERE id = %s", (email_id,))
    conn.commit()
    conn.close()
    logger.info(f"Marked email {email_id} as processed.")

if __name__ == "__main__":
    logger.info("📬 Dispatcher Service Started")
    while True:
        process_emails()
        logger.info("🔄 Waiting 10 seconds before checking for new emails...")
        time.sleep(10)  # Adjust polling interval as needed