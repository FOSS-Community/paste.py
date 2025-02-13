from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import get_settings

SQLALCHEMY_DATABASE_URL = get_settings().SQLALCHEMY_DATABASE_URL

# Check if the database URL is for SQLite
is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite specific argument
    )

else:
    # PostgreSQL configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={},
        future=True,
        # Common PostgreSQL settings
        pool_size=5,  # Maximum number of permanent connections
        max_overflow=10,  # Maximum number of additional connections
        pool_timeout=30,  # Timeout in seconds for getting a connection from pool
        pool_recycle=1800,  # Recycle connections after 30 minutes
    )


Session_Local = sessionmaker(bind=engine, autocommit=False, autoflush=False)


Base = declarative_base()


def get_db():
    db = Session_Local()
    try:
        yield db
    finally:
        db.close()


# Example database URLs in config.py:
# SQLite: "sqlite:///./sql_app.db"
# PostgreSQL: "postgresql://user:password@localhost:5432/db_name"
