"""
database.py
SQLAlchemy engine/session setup.

Local dev (no setup required): defaults to a SQLite file, adas.db.
Deployment (Docker Compose / Railway / Render): set DATABASE_URL to a
Postgres connection string, e.g.
    postgresql://user:password@db:5432/adas
and everything else in this file works unchanged -- SQLAlchemy abstracts
the dialect difference away from models.py/crud.py.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./adas.db")

# SQLite needs this connect_arg for multi-threaded FastAPI access; Postgres does not.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
