import os
from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()

db_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
db_url = os.getenv("SUPABASE_URL")

supabase: Client = create_client(db_url, db_key)
