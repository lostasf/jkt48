import os
import requests
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.environ.get("NEON_DB_URL"))

def get_latest_sync_date(default_date="2025-01-01"):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(attended_at) FROM attendance")
            result = cur.fetchone()
            if result and result[0]:
                return result[0].strftime("%Y-%m-%d")
    return default_date

def resolve_reference_code(ticket_code):
    if not ticket_code:
        return None
    
    parts = ticket_code.split("-")
    
    if len(parts) > 1 and parts[1].isdigit():
        return f"{parts[0]}-{parts[1]}"
        
    return parts[0]

def fetch_my_tickets(start_date, end_date, token):
    page = 1
    total_pages = 1
    headers = {"Authorization": f"Bearer {token}"}
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            while page <= total_pages:
                url = f"https://jkt48.com/api/v1/accounts/my-tickets?lang=id&limit=10&page={page}&from={start_date}&to={end_date}"
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if page == 1:
                    total_pages = data.get("_meta", {}).get("total_page", 1)
                    
                for ticket in data.get("data", []):
                    if ticket.get("ticket_type") not in ("SHOW", "EVENT"):
                        continue
                        
                    if ticket.get("raffle_status") == "LOSE":
                        continue
                        
                    if int(ticket.get("used_count", 0)) == 0:
                        continue
                        
                    db_ref_code = resolve_reference_code(ticket.get("reference_code", ""))
                    if not db_ref_code:
                        continue
                    
                    cur.execute(
                        """
                        INSERT INTO attendance (schedule_id, attended_at)
                        SELECT schedule_id, %s FROM shows WHERE reference_code = %s
                        ON CONFLICT (schedule_id) DO NOTHING
                        """,
                        (ticket.get("date"), db_ref_code)
                    )
                
                conn.commit()
                page += 1

if __name__ == "__main__":
    jkt48_token = os.environ.get("JKT48_TOKEN")
    if not jkt48_token:
        raise ValueError("Missing JKT48_TOKEN in .env")
        
    end_date = "2026-06-01"
    start_date = "2024-01-01"
    
    print(f"Syncing attendance from {start_date} to {end_date}...")
    fetch_my_tickets(start_date, end_date, jkt48_token)
    print("Sync complete.")