import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db.models import Base

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "zarkaan.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _add_missing_columns():
    # ponytail: no Alembic for a single sqlite dev DB - just patch old tables in place
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(vehicle_detections)"))}
        if cols and "job_id" not in cols:
            conn.execute(text("ALTER TABLE vehicle_detections ADD COLUMN job_id VARCHAR"))
            conn.commit()
        if cols and "plate_number" not in cols:
            conn.execute(text("ALTER TABLE vehicle_detections ADD COLUMN plate_number VARCHAR"))
            conn.execute(text("ALTER TABLE vehicle_detections ADD COLUMN plate_confidence FLOAT"))
            conn.commit()

def init_db():
    logger.info(f"Initializing database at {DB_PATH}...")
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    logger.info("Database tables initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
