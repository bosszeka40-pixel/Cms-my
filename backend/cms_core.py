import hashlib
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./cms_core.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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

class BotStat(Base):
    __tablename__ = "bot_stats"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CMSEngine:
    def __init__(self, db_name: str = "cms_core.db"):
        self.db_name = db_name
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.init_db()

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def create_user(self, email: str, password: str, kyc_status: bool = False, role: str = "user") -> User:
        session = self.SessionLocal()
        try:
            password_hash = self.hash_password(password)
            user = User(email=email, password_hash=password_hash, kyc_status=kyc_status, role=role)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        finally:
            session.close()

    def get_user(self, email: str):
        session = self.SessionLocal()
        try:
            return session.query(User).filter(User.email == email).first()
        finally:
            session.close()

    def authenticate_user(self, email: str, password: str):
        user = self.get_user(email)
        if user and user.password_hash == self.hash_password(password):
            return user
        return None

    def create_plugin(self, name: str, price: float, description: str = "") -> Plugin:
        session = self.SessionLocal()
        try:
            plugin = Plugin(name=name, price=price, description=description)
            session.add(plugin)
            session.commit()
            session.refresh(plugin)
            return plugin
        finally:
            session.close()

    def list_plugins(self):
        session = self.SessionLocal()
        try:
            return session.query(Plugin).all()
        finally:
            session.close()

    def record_bot_stat(self, name: str, value: str) -> BotStat:
        session = self.SessionLocal()
        try:
            stat = BotStat(name=name, value=value)
            session.add(stat)
            session.commit()
            session.refresh(stat)
            return stat
        finally:
            session.close()

    def secure_login(self, email: str, password: str):
        return self.authenticate_user(email, password)
