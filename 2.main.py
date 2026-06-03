import os
import time
import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.environ.get("NEON_DB_URL"))

def fetch_monthly_schedule(year, month, schedule_type):
    url = f"https://jkt48.com/api/v1/schedules?lang=id&month={month}&year={year}&type={schedule_type}"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    return response.json().get("data", [])

def fetch_details(reference_code, schedule_type):
    endpoint = "events" if schedule_type == "EVENT" else "theater-shows"
    url = f"https://jkt48.com/api/v1/{endpoint}/{reference_code}?lang=id"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("data")

def sync_data(data, schedule_type):
    if schedule_type == "EVENT" and not data.get("is_in_theater"):
        return

    schedule_id = data.get("event_id") if schedule_type == "EVENT" else data.get("theater_show_id")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO shows (schedule_id, reference_code, title, show_date, event_type)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (schedule_id) DO NOTHING
                """,
                (schedule_id, data["code"], data["title"], data["date"], schedule_type)
            )
            
            for member in data.get("jkt48_member", []):
                cur.execute(
                    """
                    INSERT INTO members (member_id, name, jkt48_member_type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (member_id) DO NOTHING
                    """,
                    (member["member_id"], member["name"], member["type"])
                )
                
                cur.execute(
                    """
                    INSERT INTO show_members (schedule_id, member_id)
                    VALUES (%s, %s)
                    ON CONFLICT (schedule_id, member_id) DO NOTHING
                    """,
                    (schedule_id, member["member_id"])
                )
        conn.commit()

def run_historical_sync(year, start_month, end_month):
    for schedule_type in ["SHOW", "EVENT"]:
        for month in range(start_month, end_month + 1):
            print(f"Fetching {schedule_type} schedule for {year}-{month:02d}...")
            schedules = fetch_monthly_schedule(year, month, schedule_type)
            
            for item in schedules:
                code = item.get("reference_code")
                if not code:
                    continue
                    
                try:
                    print(f"Syncing {schedule_type} details for code: {code}")
                    details = fetch_details(code, schedule_type)
                    sync_data(details, schedule_type)
                    time.sleep(1)
                except Exception as e:
                    print(f"Failed to sync {schedule_type} {code}: {e}")
                    continue

if __name__ == "__main__":
    run_historical_sync(2026, 1, 6)