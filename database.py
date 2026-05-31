"""
database.py
───────────
SQLAlchemy engine + session factory for EventFlow.

Design choices:
  - SQLite with check_same_thread=False is correct for FastAPI's async-style
    thread pool; SQLAlchemy's connection pool handles safety.
  - `get_db()` uses a generator + try/finally so the session is always
    closed even if the route handler raises — avoids connection leaks.
  - `Base` is imported by models.py (already done there); we re-export it
    here so every module has a single source of truth for the metadata.
  - `init_db()` is called from main.py lifespan to create tables and seed
    the singleton EventConfig row on first boot.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# DATABASE URL
# ──────────────────────────────────────────────

DATABASE_URL = "sqlite:///./eventflow.db"

# ──────────────────────────────────────────────
# ENGINE
# ──────────────────────────────────────────────
# `check_same_thread=False` — required for SQLite when used with FastAPI's
# threadpool executor (Starlette runs sync routes in a thread pool).
# `StaticPool` is NOT used here (that's for in-memory test DBs); the default
# `NullPool` / `QueuePool` is fine for file-based SQLite.

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,        # set True locally to log all SQL
)

# Enable WAL mode for better concurrent read performance with SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")   # enforce FK constraints
    cursor.close()

# ──────────────────────────────────────────────
# SESSION FACTORY
# ──────────────────────────────────────────────

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ──────────────────────────────────────────────
# DECLARATIVE BASE
# ──────────────────────────────────────────────
# models.py does `from database import Base` — this is that Base.
# All ORM models inherit from it; SQLAlchemy uses its metadata registry
# to know which tables to create.

class Base(DeclarativeBase):
    pass

# ──────────────────────────────────────────────
# FASTAPI DEPENDENCY
# ──────────────────────────────────────────────

def get_db():
    """
    Yields a SQLAlchemy Session for use in a FastAPI route.

    Usage:
        @app.get("/something")
        def my_route(db: Session = Depends(get_db)):
            ...

    The session is always closed in the `finally` block, regardless of
    whether the route succeeds or raises an exception.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ──────────────────────────────────────────────
# INITIALISATION HELPER
# ──────────────────────────────────────────────

def init_db() -> None:
    """
    Creates all tables (safe to call multiple times — uses CREATE IF NOT EXISTS
    semantics under the hood) and seeds the singleton EventConfig row.

    Called once from main.py's lifespan context manager.
    """
    # Import here to avoid circular imports at module load time
    from models import EventConfig  # noqa: F401 — registers model with Base.metadata

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")

    # Seed singleton EventConfig (id=1) if it doesn't exist yet
    db = SessionLocal()
    try:
        existing = db.query(EventConfig).filter(EventConfig.id == 1).first()
        if not existing:
            config = EventConfig(id=1)
            db.add(config)
            db.commit()
            logger.info("EventConfig singleton seeded with defaults.")
    finally:
        db.close()