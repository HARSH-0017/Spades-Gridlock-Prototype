from pathlib import Path

from db import connect


BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "db"


def main():
    sql_files = ["001_schema.sql", "002_views.sql", "003_ml_schema.sql"]
    with connect() as conn:
        with conn.cursor() as cur:
            for name in sql_files:
                path = DB_DIR / name
                print(f"Applying {path}")
                cur.execute(path.read_text(encoding="utf-8"))
        conn.commit()
    print("Database schema is ready.")


if __name__ == "__main__":
    main()
