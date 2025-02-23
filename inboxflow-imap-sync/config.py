import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")
EMAIL_SERVER = os.getenv("EMAIL_SERVER")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
REACT_APP_API_URL = os.getenv("REACT_APP_API_URL")
