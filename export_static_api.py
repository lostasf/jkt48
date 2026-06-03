import os
import json
import psycopg2
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.environ.get("NEON_DB_URL"))

def export_to_static_api():
    # Ensure the output directory exists
    output_dir = os.path.join("api", "data", "schedules")
    os.makedirs(output_dir, exist_ok=True)

    grouped_data = defaultdict(lambda: {"members": {}, "schedules": []})

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # We use JSON_AGG to get the lineup in a single query per show
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

    print(f"Fetched {len(rows)} total events from database.")

    for row in rows:
        schedule_id = row[0]
        ref_code = row[1]
        title = row[2]
        show_date = row[3] # This is a datetime object
        event_type = row[4]
        lineup = row[5] # This is a parsed JSON list from Postgres

        # Determine the shard key (YYYY-MM)
        year_month = show_date.strftime("%Y-%m")
        timestamp = int(show_date.timestamp())
        
        type_flag = "E" if event_type == "EVENT" else "S"
        
        member_ids = []
        for m in lineup:
            # Populate the centralized member dictionary for this month
            member_id_str = str(m["member_id"])
            grouped_data[year_month]["members"][member_id_str] = m["name"]
            member_ids.append(m["member_id"])
            
        # Create the positional array for the schedule
        schedule_tuple = [
            schedule_id,
            ref_code,
            title,
            timestamp,
            type_flag,
            member_ids
        ]
        
        grouped_data[year_month]["schedules"].append(schedule_tuple)

    # Write the sharded data to disk
    for ym, payload in grouped_data.items():
        filepath = os.path.join(output_dir, f"{ym}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            # separators=(",", ":") removes whitespace for minification
            json.dump(payload, f, separators=(",", ":"))
        print(f"Generated {filepath} ({len(payload['schedules'])} events)")

if __name__ == "__main__":
    print("Starting static API export...")
    export_to_static_api()
    print("Export complete.")