import imaplib

EMAIL_SERVER = "imap.mail.yahoo.com"
EMAIL_USER = "you@example.com"
EMAIL_PASSWORD = "REDACTED_APP_PASSWORD"  # app password

try:
    # Connect using IMAP over SSL on port 993
    mail = imaplib.IMAP4_SSL(EMAIL_SERVER, 993)
    mail.login(EMAIL_USER, EMAIL_PASSWORD)
    print("Logged in successfully!")
    mail.logout()
except Exception as e:
    print("Error:", e)