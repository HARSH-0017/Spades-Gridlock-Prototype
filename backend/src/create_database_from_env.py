import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def get_env(name, default=None):
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


POSTGRES_HOST = get_env("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(get_env("POSTGRES_PORT", "5432"))
POSTGRES_DB = get_env("POSTGRES_DB", "gridlock")
POSTGRES_USER = get_env("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = get_env("POSTGRES_PASSWORD")
ADMIN_DB = get_env("POSTGRES_ADMIN_DB", "postgres")


def connect(dbname, autocommit=False):
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=dbname,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    conn.autocommit = autocommit
    return conn


def quote_ident(name):
    return '"' + name.replace('"', '""') + '"'


def main():
    db_exists = False
    conn = connect(ADMIN_DB, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", [POSTGRES_DB])
            db_exists = cur.fetchone() is not None
            if not db_exists:
                cur.execute(f"CREATE DATABASE {quote_ident(POSTGRES_DB)}")
    finally:
        conn.close()

    with connect(POSTGRES_DB) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS gridlock;")
        conn.commit()

    if db_exists:
        print(f"Database '{POSTGRES_DB}' already exists.")
    else:
        print(f"Created database '{POSTGRES_DB}'.")
    print("Ensured schema 'gridlock' exists.")


if __name__ == "__main__":
    main()
