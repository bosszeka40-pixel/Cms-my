import hashlib
import hmac
import os
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

# Vercel/serverless filesystems are read-only except /tmp.  Keep the database
# location configurable so local deployments can use a persistent path while
# serverless deployments can still start successfully.
DEFAULT_DATABASE_URL = os.getenv("CMS_DATABASE_URL", "sqlite:////tmp/cms_core.db" if os.getenv("VERCEL") else "sqlite:///./cms_core.db")
engine = create_engine(DEFAULT_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    kyc_status = Column(Boolean, default=False)
    role = Column(String, default="user")

class Plugin(Base):
    __tablename__ = "plugins"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text, default="")

class UserPlugin(Base):
    __tablename__ = "user_plugins"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False, index=True)
    active = Column(Boolean, default=False, nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    access_until = Column(DateTime, nullable=True)

class LearningMemory(Base):
    __tablename__ = "learning_memory"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)
    action = Column(String, nullable=False)
    result = Column(Float, nullable=False)
    context = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class BotStat(Base):
    __tablename__ = "bot_stats"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)
    action = Column(String, nullable=False)
    context = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    credits = Column(Float, default=0.0)
    wallet_provider = Column(String, nullable=True)
    wallet_address = Column(String, nullable=True)
    exchange_provider = Column(String, nullable=True)
    exchange_key_masked = Column(String, nullable=True)
    exchange_sandbox = Column(Boolean, default=True)
    telegram_username = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pair = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    strategy = Column(String, default="")
    pnl = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class SiteSetting(Base):
    __tablename__ = "site_settings"
    key = Column(String, primary_key=True)
    value = Column(Text, default="")

class CMSEngine:
    def __init__(self, db_name: str | None = None):
        # CMS_DATABASE_URL takes precedence. On Vercel, /tmp is the only
        # writable filesystem; local development keeps the existing DB path.
        db_name = db_name or os.getenv("CMS_DATABASE_URL") or ("sqlite:////tmp/cms_core.db" if os.getenv("VERCEL") else "cms_core.db")
        self.db_name = db_name
        if db_name.startswith("sqlite://"):
            database_url = db_name
        else:
            database_url = f"sqlite:///{Path(db_name)}"
        self.engine = create_engine(database_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_db()

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)
        self.ensure_user_plugin_access_column()
        self.ensure_strategy_plugins()

    def ensure_user_plugin_access_column(self):
        with self.engine.begin() as connection:
            columns = connection.exec_driver_sql("PRAGMA table_info(user_plugins)").fetchall()
            if not any(column[1] == "access_until" for column in columns):
                connection.exec_driver_sql("ALTER TABLE user_plugins ADD COLUMN access_until DATETIME")

    @staticmethod
    def hash_password(password: str) -> str:
        if not password:
            raise ValueError("Пароль не может быть пустым.")
        return generate_password_hash(password, method="scrypt")

    def create_user(self, email: str, password: str, kyc_status: bool = False, role: str = "user") -> User:
        session = self.SessionLocal()
        try:
            email = email.strip().lower()
            if not email:
                raise ValueError("Email не может быть пустым.")
            password_hash = self.hash_password(password)
            user = User(email=email, password_hash=password_hash, kyc_status=kyc_status, role=role)
            session.add(user)