import os
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_config
from .db_models import Base


class Database:
    _instance: Optional["Database"] = None
    _engine = None
    _SessionLocal = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self, db_path: Optional[str] = None):
        if self._engine is not None:
            return
        if db_path is None:
            cfg = get_config()
            data_dir = cfg.get("data_dir", "./data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "aiaccountpool.db")

        db_url = f"sqlite:///{db_path}"
        self._engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        self._SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )
        Base.metadata.create_all(bind=self._engine)
        print(f"[Database] 数据库已初始化: {db_path}")

    @contextmanager
    def get_session(self):
        if self._SessionLocal is None:
            self.init()
        session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_direct(self) -> Session:
        if self._SessionLocal is None:
            self.init()
        return self._SessionLocal()


db = Database()


def get_db():
    with db.get_session() as session:
        yield session
