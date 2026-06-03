import os
import json
import psycopg2
from dotenv import load_dotenv

def extract_data():
    load_dotenv()
    
    db_url = os.environ.get("NEON_DB_URL")
    
    if not db_url:
        raise ValueError("NEON_DB_URL environment variable is missing or empty.")
        
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(schedule_id) FROM attendance")
    total_attendance = cur.fetchone()[0]
    
    query = """
        SELECT m.name, COUNT(sm.schedule_id) as meet_count
        FROM attendance a
        JOIN show_members sm ON a.schedule_id = sm.schedule_id
        JOIN members m ON sm.member_id = m.member_id
        GROUP BY m.member_id, m.name
        ORDER BY meet_count DESC, m.name ASC
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    members_data = [{"name": row[0], "meet_count": row[1]} for row in rows]
    
    data = {
        "total_attendance": total_attendance,
        "members": members_data
    }
    
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    extract_data()