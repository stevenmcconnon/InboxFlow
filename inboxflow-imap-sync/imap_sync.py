import imaplib
import os

def lambda_handler(event, context):
    # Get values from environment variables (or use defaults)
    EMAIL_SERVER = "imap.mail.yahoo.com"
    EMAIL_USER = "you@example.com"
    EMAIL_PASSWORD = "redacted"  # app password

    try:
        # Connect using IMAP over SSL on port 993
        mail = imaplib.IMAP4_SSL(EMAIL_SERVER, 993)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        print("Logged in successfully!")
        mail.logout()
        return {
            "statusCode": 200,
            "body": "Logged in successfully!"
        }
    except Exception as e:
        print("Error:", e)
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }
        
        
        
# import imaplib
# import logging
# import os
# import time
# import psycopg2
# import boto3
# import json
# from email import message_from_bytes

# # Configuration from environment
# EMAIL_SERVER = os.getenv("EMAIL_SERVER")
# EMAIL_USER = os.getenv("EMAIL_USER")
# EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
# DB_URL = os.getenv("DB_URL")
# BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
# LAMBDA_FUNCTION_NAME = os.getenv("AWS_LAMBDA_FUNCTION_NAME")  # Automatically injected in Lambda

# # Configure logging
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)

# def connect_imap():
#     """Establish and return an IMAP connection."""
#     try:
#         conn = imaplib.IMAP4_SSL(EMAIL_SERVER)
#         conn.login(EMAIL_USER, EMAIL_PASSWORD)
#         conn.select("inbox")
#         logger.info("Connected to IMAP server.")
#         return conn
#     except imaplib.IMAP4.abort as e:
#         logger.error(f"IMAP connection aborted: {e}. Retrying in 10 seconds...")
#         time.sleep(10)
#         return connect_imap()
#     except imaplib.IMAP4.error as e:
#         logger.error(f"IMAP error: {e}")
#         return None

# def insert_email(email_uid, subject, sender, content):
#     """Insert email into the PostgreSQL database."""
#     conn = None
#     try:
#         conn = psycopg2.connect(DB_URL)
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO emails (id, subject, sender, content, status) VALUES (%s, %s, %s, %s, %s) "
#             "ON CONFLICT (id) DO NOTHING",
#             (email_uid, subject, sender, content, "pending")
#         )
#         conn.commit()
#         logger.info(f"Email {email_uid} inserted into DB successfully.")
#     except Exception as e:
#         logger.error(f"DB insertion error for email {email_uid}: {e}")
#     finally:
#         if conn:
#             conn.close()

# def delete_email(email_uid):
#     """Delete email from the PostgreSQL database."""
#     conn = None
#     try:
#         conn = psycopg2.connect(DB_URL)
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM emails WHERE id = %s", (email_uid,))
#         conn.commit()
#         logger.info(f"Email {email_uid} deleted from DB.")
#     except Exception as e:
#         logger.error(f"DB deletion error for email {email_uid}: {e}")
#     finally:
#         if conn:
#             conn.close()

# def process_email(email_uid, raw_email):
#     """
#     Process a raw email message.
#     Minimal parsing: extract subject and sender.
#     """
#     try:
#         msg = message_from_bytes(raw_email)
#         subject = msg.get("Subject", "No Subject")
#         sender = msg.get("From", "Unknown Sender")
#         content = raw_email.decode("utf-8", errors="ignore")
#     except Exception as e:
#         logger.error(f"Error parsing email {email_uid}: {e}")
#         subject = "Parsing Error"
#         sender = "Parsing Error"
#         content = raw_email.decode("utf-8", errors="ignore")
#     insert_email(email_uid, subject, sender, content)

# def fetch_emails(start_index=0):
#     """Fetch emails from the IMAP server, return list of email UIDs and raw data."""
#     conn = connect_imap()
#     if not conn:
#         logger.error("Failed to connect to IMAP server.")
#         return None, []

#     status, messages = conn.search(None, "ALL")
#     if status != "OK":
#         logger.error("Error fetching messages.")
#         conn.logout()
#         return None, []

#     all_uids = messages[0].split()
#     total_msgs = len(all_uids)
#     logger.info(f"Total emails on server: {total_msgs}")

#     # Determine current batch of UIDs
#     end_index = min(start_index + BATCH_SIZE, total_msgs)
#     batch_uids = all_uids[start_index:end_index]
#     emails = []

#     for uid in batch_uids:
#         try:
#             status, msg_data = conn.fetch(uid, "(RFC822)")
#             if status != "OK":
#                 logger.warning(f"Failed to fetch email UID {uid.decode()}")
#                 continue
#             emails.append((uid.decode(), msg_data[0][1]))
#             logger.info(f"Fetched email UID {uid.decode()}")
#         except imaplib.IMAP4.abort as e:
#             logger.error(f"IMAP server disconnected while fetching email UID {uid.decode()}: {e}")
#             conn = connect_imap()
#             continue

#     conn.logout()
#     return all_uids, emails

# def cleanup_deleted_emails(server_uids):
#     """Remove emails from DB that are not present on the server anymore."""
#     conn = None
#     try:
#         conn = psycopg2.connect(DB_URL)
#         cursor = conn.cursor()
#         cursor.execute("SELECT id FROM emails")
#         db_uids = {str(row[0]) for row in cursor.fetchall()}
#         server_uids_set = {uid.decode() if isinstance(uid, bytes) else uid for uid in server_uids}
#         uids_to_delete = db_uids - server_uids_set

#         for uid in uids_to_delete:
#             delete_email(uid)
#     except Exception as e:
#         logger.error(f"Error during cleanup: {e}")
#     finally:
#         if conn:
#             conn.close()

# def invoke_lambda(next_index):
#     """Invoke this Lambda function asynchronously for the next batch."""
#     lambda_client = boto3.client("lambda")
#     payload = {"start_index": next_index}
#     try:
#         response = lambda_client.invoke(
#             FunctionName=LAMBDA_FUNCTION_NAME,
#             InvocationType="Event",
#             Payload=json.dumps(payload)
#         )
#         logger.info(f"Lambda re-invoked for next batch starting at index {next_index}: {response}")
#     except Exception as e:
#         logger.error(f"Failed to re-invoke Lambda: {e}")

# def lambda_handler(event, context):
#     """
#     Lambda entry point.
#     Event may contain 'start_index' for pagination; defaults to 0.
#     Performs full/incremental sync and cleanup.
#     """
#     start_index = int(event.get("start_index", 0))
#     logger.info(f"Lambda invoked with start_index: {start_index}")

#     server_uids, emails = fetch_emails(start_index)
#     if server_uids is None:
#         return {"status": "failed", "message": "IMAP connection failed."}

#     # Process each fetched email
#     for email_uid, raw_email in emails:
#         process_email(email_uid, raw_email)

#     # Cleanup: remove emails from DB that no longer exist on the server
#     cleanup_deleted_emails(server_uids)

#     total_msgs = len(server_uids)
#     next_index = start_index + len(emails)
#     if next_index < total_msgs:
#         logger.info("More emails remain; invoking Lambda recursively for next batch.")
#         invoke_lambda(next_index)
#     else:
#         logger.info("All emails processed and cleanup complete.")

#     return {"status": "completed", "processed": next_index, "total": total_msgs}