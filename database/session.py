import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .models import Base

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

# Если DATABASE_URL не установлена, используем SQLite для разработки
if not DATABASE_URL:
    logger.info("DATABASE_URL not set, using SQLite for development")
    DATABASE_URL = "sqlite:///./buildflow.db"

logger.info(f"Using database: {DATABASE_URL}")

engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def init_db() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created or verified")
    except SQLAlchemyError as exc:
        logger.exception("Failed to initialize database: %s", exc)
        raise


def get_session():
    """Get a new database session."""
    return SessionLocal()


def reset_db() -> None:
    """Drop all tables and recreate them (use only for development!)"""
    try:
        logger.warning("⚠️ Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.warning("✅ All tables dropped")
        init_db()
        logger.info("✅ Database reset and recreated")
    except SQLAlchemyError as exc:
        logger.exception("Failed to reset database: %s", exc)
        raise
