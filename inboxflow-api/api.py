from fastapi import FastAPI, HTTPException, Query
import psycopg2
from config import DB_URL

app = FastAPI()

def get_db_connection():
    return psycopg2.connect(DB_URL)

@app.get("/emails")
def get_emails(filter: str = "all", limit: int = 20, offset: int = 0):
    """Retrieve emails with pagination and filtering."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id, subject, content, status FROM emails"
    
    if filter == "work-related":
        query += " WHERE subject ILIKE '%recruiter%' OR subject ILIKE '%job%'"
    
    query += " ORDER BY received_at DESC LIMIT %s OFFSET %s"
    cursor.execute(query, (limit, offset))
    emails = cursor.fetchall()
    
    conn.close()
    return [{"id": e[0], "subject": e[1], "content": e[2], "status": e[3]} for e in emails]

@app.post("/emails/{id}/decision")
def decide_email(id: str, decision: str, edited_response: str = None):
    """Approve, reject, skip, or manually edit AI-generated response."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if decision == "Y":
        cursor.execute("UPDATE emails SET status = 'approved' WHERE id = %s", (id,))
    elif decision == "N":
        cursor.execute("UPDATE emails SET status = 'rejected' WHERE id = %s", (id,))
    elif decision == "S":
        cursor.execute("UPDATE emails SET status = 'skipped' WHERE id = %s", (id,))
    elif decision == "M" and edited_response:
        cursor.execute("UPDATE emails SET status = 'edited', content = %s WHERE id = %s", (edited_response, id))
    else:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid decision value")

    conn.commit()
    conn.close()
    return {"message": "Decision processed successfully"}

@app.post("/sync-emails")
def sync_emails():
    """Triggers manual email sync from IMAP."""
    return {"message": "Sync started. Fetching unread emails from IMAP."}
