import os
import time
import json
import psycopg2
import requests
from collections import defaultdict
from datetime import datetime
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
        return False

    schedule_id = data.get("event_id") if schedule_type == "EVENT" else data.get("theater_show_id")
    has_changes = False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO shows (schedule_id, reference_code, title, show_date, event_type)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (schedule_id) DO UPDATE
                SET title = EXCLUDED.title,
                    show_date = EXCLUDED.show_date,
                    event_type = EXCLUDED.event_type
                WHERE shows.title IS DISTINCT FROM EXCLUDED.title
                   OR shows.show_date IS DISTINCT FROM EXCLUDED.show_date
                   OR shows.event_type IS DISTINCT FROM EXCLUDED.event_type
                RETURNING schedule_id
                """,
                (schedule_id, data["code"], data["title"], data["date"], schedule_type)
            )

            if cur.rowcount > 0:
                has_changes = True

            new_members = data.get("jkt48_member", [])
            new_member_ids = {m["member_id"] for m in new_members}

            cur.execute(
                "SELECT member_id FROM show_members WHERE schedule_id = %s",
                (schedule_id,)
            )
            existing_member_ids = {row[0] for row in cur.fetchall()}

            if new_member_ids != existing_member_ids:
                has_changes = True

                if existing_member_ids:
                    cur.execute(
                        "DELETE FROM show_members WHERE schedule_id = %s",
                        (schedule_id,)
                    )

                for member in new_members:
                    cur.execute(
                        """
                        INSERT INTO members (member_id, name, jkt48_member_type)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (member_id) DO UPDATE
                        SET name = EXCLUDED.name,
                            jkt48_member_type = EXCLUDED.jkt48_member_type
                        WHERE members.name IS DISTINCT FROM EXCLUDED.name
                           OR members.jkt48_member_type IS DISTINCT FROM EXCLUDED.jkt48_member_type
                        """,
                        (member["member_id"], member["name"], member["type"])
                    )

                    cur.execute(
                        """
                        INSERT INTO show_members (schedule_id, member_id)
                        VALUES (%s, %s)
                        """,
                        (schedule_id, member["member_id"])
                    )
        conn.commit()

    return has_changes

def run_daily_sync(year, month):
    changes_detected = False
    for schedule_type in ["SHOW", "EVENT"]:
        print(f"Fetching {schedule_type} schedule for {year}-{month:02d}...")
        schedules = fetch_monthly_schedule(year, month, schedule_type)
        
        for item in schedules:
            code = item.get("reference_code")
            if not code:
                continue
                
            try:
                details = fetch_details(code, schedule_type)
                if sync_data(details, schedule_type):
                    changes_detected = True
                    print(f"Updated database for: {code}")
                time.sleep(1)
            except Exception as e:
                print(f"Failed to sync {schedule_type} {code}: {e}")
                continue
                
    return changes_detected

def export_to_static_api():
    output_dir = os.path.join("api", "data", "schedules")
    os.makedirs(output_dir, exist_ok=True)

    grouped_data = defaultdict(lambda: {"members": {}, "schedules": []})

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT 
                    s.schedule_id, 
                    s.reference_code, 
                    s.title, 
                    s.show_date, 
                    COALESCE(s.event_type, 'SHOW') as event_type,
                    COALESCE(
                        json_agg(
                            json_build_object('member_id', m.member_id, 'name', m.name)
                        ) FILTER (WHERE m.member_id IS NOT NULL), 
                        '[]'
                    ) as lineup
                FROM shows s
                LEFT JOIN show_members sm ON s.schedule_id = sm.schedule_id
                LEFT JOIN members m ON sm.member_id = m.member_id
                WHERE s.show_date >= '2024-01-01'
                GROUP BY s.schedule_id
                ORDER BY s.show_date ASC;
            """
            cur.execute(query)
            rows = cur.fetchall()

    for row in rows:
        schedule_id = row[0]
        ref_code = row[1]
        title = row[2]
        show_date = row[3]
        event_type = row[4]
        lineup = row[5]

        year_month = show_date.strftime("%Y-%m")
        timestamp = int(show_date.timestamp())
        
        type_flag = "E" if event_type == "EVENT" else "S"
        
        member_ids = []
        for m in lineup:
            member_id_str = str(m["member_id"])
            grouped_data[year_month]["members"][member_id_str] = m["name"]
            member_ids.append(m["member_id"])
            
        schedule_tuple = [
            schedule_id,
            ref_code,
            title,
            timestamp,
            type_flag,
            member_ids
        ]
        
        grouped_data[year_month]["schedules"].append(schedule_tuple)

    for ym, payload in grouped_data.items():
        filepath = os.path.join(output_dir, f"{ym}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        print(f"Generated {filepath}")

if __name__ == "__main__":
    now = datetime.now()
    
    has_updates = run_daily_sync(now.year, now.month)
    
    if has_updates:
        print("Changes detected. Regenerating static API...")
        export_to_static_api()
        print("Static API regeneration complete.")
    else:
        print("No new data synced. Skipping static JSON generation.")