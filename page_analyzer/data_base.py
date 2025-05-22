import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def save_url(url):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO urls (name) VALUES (%s) RETURNING id', (url,))
            url_id = cur.fetchone()[0]
            conn.commit()
            return url_id

def get_existing_urls():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, name FROM urls')
            return cur.fetchall()