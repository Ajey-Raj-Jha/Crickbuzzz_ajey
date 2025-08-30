import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST","localhost"),
            user=os.getenv("DB_USER","root"),
            password=os.getenv("DB_PASS",""),
            database=os.getenv("DB_NAME","cricbuzz_db"),
            autocommit=True,
        )
    except Error as e:
        raise RuntimeError(f"MySQL connection error: {e}")

def run_query(sql, params=None):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def run_execute(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    cur.close(); conn.close()
