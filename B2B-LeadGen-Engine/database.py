import sqlite3
import os

DB_PATH = "leads.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sent_jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            budget TEXT,
            description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_job_sent(job_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM sent_jobs WHERE job_id = ?", (job_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_job_sent(job_id: str, title: str, url: str, budget: str, description: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO sent_jobs (job_id, title, url, budget, description) VALUES (?, ?, ?, ?, ?)", 
              (job_id, title, url, budget, description))
    conn.commit()
    conn.close()

def get_all_jobs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT job_id, title, url, budget, description, timestamp FROM sent_jobs ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    
    jobs = []
    for row in rows:
        jobs.append({
            "id": row[0],
            "title": row[1],
            "url": row[2],
            "budget": row[3],
            "description": row[4],
            "timestamp": row[5]
        })
    return jobs

# Initialize on import
init_db()
