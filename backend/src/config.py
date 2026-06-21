import os
from pathlib import Path

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
POSTGRES_USER = get_env("POSTGRES_USER", "gridlock_app")
POSTGRES_PASSWORD = get_env("POSTGRES_PASSWORD", "change_me_strong_password")
SOURCE_CSV = (BASE_DIR / get_env("SOURCE_CSV", "data/jan to may police violation_anonymized791b166.csv")).resolve()
OUTPUT_DIR = (BASE_DIR / get_env("OUTPUT_DIR", "outputs")).resolve()
