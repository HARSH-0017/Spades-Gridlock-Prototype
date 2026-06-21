from db import connect


def main():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version();")
            database, user, version = cur.fetchone()
    print("PostgreSQL connection successful.")
    print(f"Database: {database}")
    print(f"User: {user}")
    print(f"Version: {version}")


if __name__ == "__main__":
    main()
