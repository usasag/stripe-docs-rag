import psycopg
from urllib.parse import quote_plus

# Try to connect
db_url = "postgresql://postgres:testpassworddb2026!@db.hxmpdytlsejvbkasrhlb.supabase.co:5432/postgres"

# Try percent encoding the password
encoded_password = quote_plus("testpassworddb2026!")
encoded_db_url = f"postgresql://postgres:{encoded_password}@db.hxmpdytlsejvbkasrhlb.supabase.co:5432/postgres"

for url in [db_url, encoded_db_url]:
    print(f"Trying: {url}")
    try:
        with psycopg.connect(url) as conn:
            print("Success!")
            break
    except Exception as e:
        print(f"Failed: {e}")
