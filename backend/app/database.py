import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Ensure data directory exists
# sqlite:///./foo.db → relative path; sqlite:////data/foo.db → absolute path
_raw_url = settings.database_url
if _raw_url.startswith("sqlite:////"):
    _db_path = "/" + _raw_url[len("sqlite:////"):]
elif _raw_url.startswith("sqlite:///"):
    _db_path = _raw_url[len("sqlite:///"):]
else:
    _db_path = ""

if _db_path:
    _db_dir = os.path.dirname(_db_path)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import user, product, order, wallet, escrow, dispute, payout, refund, audit, drive  # noqa: F401
    Base.metadata.create_all(bind=engine)
