import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.connection import ConnectionFactory
from app.core.config import get_settings

def main():
    print("Truncating database to clear corrupted JSON chunks...")
    settings = get_settings()
    factory = ConnectionFactory(db_url=settings.supabase_db_url)
    conn = factory.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE documents CASCADE;")
        conn.commit()
        print("Database successfully truncated!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
