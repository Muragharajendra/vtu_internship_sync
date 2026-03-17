import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Use a production-ready DB if provided (e.g. Railway Postgres). Otherwise fall back to the built-in sqlite DB file.
# The default sqlite DB is the existing `api/vtu_sync.db` so that previously-registered users remain available.
DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(__file__), "vtu_sync.db")
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH}"

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

# If the configured sqlite file does not exist, but we have an existing vtu_sync.db, prefer that.
# This covers environments (e.g. Render/Railway) where DATABASE_URL is set to a different sqlite path.
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    sqlite_path = SQLALCHEMY_DATABASE_URL.split("///", 1)[1]

    # If the configured file is missing but the default DB exists, use the default.
    if sqlite_path and not os.path.exists(sqlite_path) and os.path.exists(DEFAULT_SQLITE_PATH):
        SQLALCHEMY_DATABASE_URL = DEFAULT_SQLITE_URL
        sqlite_path = DEFAULT_SQLITE_PATH

    # Ensure the sqlite directory exists (helpful for environments where it might be missing)
    sqlite_dir = os.path.dirname(sqlite_path)
    if sqlite_dir and not os.path.exists(sqlite_dir):
        os.makedirs(sqlite_dir, exist_ok=True)

# For SQLite, we need `check_same_thread=False`.
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
