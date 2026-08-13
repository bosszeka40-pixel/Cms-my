import hashlib
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey
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

class UserPlugin(Base):
    __tablename__ = "user_plugins"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plugin_id = Column(Integer, ForeignKey("plugins.id"), nullable=False, index=True)
    active = Column(Boolean, default=False, nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)

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

class CMSEngine:
    def __init__(self, db_name: str = "cms_core.db"):
        self.db_name = db_name
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.init_db()

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)
        self.ensure_strategy_plugins()

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

    def ensure_strategy_plugins(self):
        defaults = [
            ("pure_harvester", 0.0, "Базовая стратегия сбора прибыли."),
            ("high_frequency_momentum", 0.0, "Моментум-стратегия для тестового режима."),
            ("compound_defender", 0.0, "Защитная стратегия сложного процента."),
        ]
        session = self.SessionLocal()
        try:
            existing = {plugin.name for plugin in session.query(Plugin).all()}
            for name, price, description in defaults:
                if name not in existing:
                    session.add(Plugin(name=name, price=price, description=description))
            session.commit()
        finally:
            session.close()

    def purchase_plugin(self, email: str, plugin_name: str):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            plugin = session.query(Plugin).filter(Plugin.name == plugin_name).first()
            if not user or not plugin:
                return None
            purchase = session.query(UserPlugin).filter_by(
                user_id=user.id, plugin_id=plugin.id
            ).first()
            if not purchase:
                purchase = UserPlugin(user_id=user.id, plugin_id=plugin.id, active=False)
                session.add(purchase)
                session.commit()
            return {"name": plugin.name, "price": plugin.price, "active": purchase.active}
        finally:
            session.close()

    def set_plugin_active(self, email: str, plugin_name: str, active: bool):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            plugin = session.query(Plugin).filter(Plugin.name == plugin_name).first()
            if not user or not plugin:
                return False
            purchase = session.query(UserPlugin).filter_by(
                user_id=user.id, plugin_id=plugin.id
            ).first()
            if not purchase:
                return False
            purchase.active = active
            session.commit()
            return True
        finally:
            session.close()

    def user_plugins(self, email: str):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return []
            return [
                {"name": item[0].name, "price": item[0].price, "active": item[1].active}
                for item in session.query(Plugin, UserPlugin)
                .join(UserPlugin, UserPlugin.plugin_id == Plugin.id)
                .filter(UserPlugin.user_id == user.id)
                .all()
            ]
        finally:
            session.close()

    def record_memory(self, action: str, result: float, context: str = "", user_id: str | None = None):
        session = self.SessionLocal()
        try:
            memory = LearningMemory(
                user_id=user_id, action=action, result=float(result), context=context
            )
            session.add(memory)
            session.commit()
            if action == "strategy_test" and result > 0:
                profitable_tests = session.query(LearningMemory).filter(
                    LearningMemory.action == "strategy_test", LearningMemory.result > 0
                ).count()
                if profitable_tests >= 3 and not session.query(Plugin).filter(
                    Plugin.name == "learned_adaptive_momentum"
                ).first():
                    session.add(Plugin(
                        name="learned_adaptive_momentum",
                        price=25.0,
                        description="Стратегия, добавленная после анализа успешных тестов памяти бота.",
                    ))
                    session.commit()
        finally:
            session.close()

    def recent_memories(self, user_id: str | None = None, limit: int = 20):
        session = self.SessionLocal()
        try:
            query = session.query(LearningMemory).order_by(LearningMemory.created_at.desc())
            if user_id:
                query = query.filter(
                    (LearningMemory.user_id == user_id) | (LearningMemory.user_id.is_(None))
                )
            return [
                {"action": item.action, "result": item.result, "context": item.context,
                 "created_at": item.created_at.isoformat()}
                for item in query.limit(limit).all()
            ]
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
