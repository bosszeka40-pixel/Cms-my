import hashlib
import hmac
import os
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

DATABASE_URL = os.getenv("CMS_DATABASE_URL") or ("sqlite:////tmp/cms_core.db" if os.getenv("VERCEL") else "sqlite:///./cms_core.db")
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


class DemoSession(Base):
    __tablename__ = "demo_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    demo_active = Column(Boolean, default=False)
    demo_balance = Column(Float, default=100.0)
    demo_pnl = Column(Float, default=0.0)
    demo_trades_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    strategy_type = Column(String, default="pure_harvester")
    leverage = Column(Float, default=1.5)
    risk_tolerance = Column(Float, default=0.03)
    fee_rate = Column(Float, default=0.001)
    parameters = Column(Text, default="{}")
    is_public = Column(Boolean, default=False)
    trial_days = Column(Integer, default=15)
    price_eur = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class CMSEngine:
    def __init__(self, db_name: str = "cms_core.db"):
        self.db_name = db_name
        if db_name == "cms_core.db" and os.getenv("VERCEL"):
            database_url = os.getenv("CMS_DATABASE_URL") or "sqlite:////tmp/cms_core.db"
        else:
            database_url = db_name if db_name.startswith("sqlite://") else f"sqlite:///./{Path(db_name)}"
        self.engine = create_engine(database_url, connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.init_db()

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)
        self.ensure_user_plugin_access_column()
        self.ensure_strategy_plugins()
        self._ensure_demo_column()


    def ensure_demo_session(self, email: str):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return
            existing = session.query(DemoSession).filter(DemoSession.user_id == user.id).first()
            if not existing:
                demo = DemoSession(user_id=user.id, demo_active=True, demo_balance=100.0)
                session.add(demo)
                session.commit()
        finally:
            session.close()

    def get_demo_session(self, email: str) -> dict:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return {"demo_active": False, "demo_balance": 100.0, "demo_pnl": 0.0, "demo_trades_count": 0}
            demo = session.query(DemoSession).filter(DemoSession.user_id == user.id).first()
            if not demo:
                demo = DemoSession(user_id=user.id, demo_active=True, demo_balance=100.0)
                session.add(demo)
                session.commit()
                session.refresh(demo)
            return {
                "demo_active": demo.demo_active,
                "demo_balance": demo.demo_balance,
                "demo_pnl": demo.demo_pnl,
                "demo_trades_count": demo.demo_trades_count,
            }
        finally:
            session.close()

    def toggle_demo_mode(self, email: str, active: bool) -> dict:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return {"demo_active": False, "demo_balance": 100.0}
            demo = session.query(DemoSession).filter(DemoSession.user_id == user.id).first()
            if not demo:
                demo = DemoSession(user_id=user.id, demo_active=active, demo_balance=100.0)
                session.add(demo)
            else:
                demo.demo_active = active
            session.commit()
            session.refresh(demo)
            return {"demo_active": demo.demo_active, "demo_balance": demo.demo_balance}
        finally:
            session.close()

    def update_demo_balance(self, email: str, pnl: float) -> dict:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return {"demo_active": False, "demo_balance": 100.0}
            demo = session.query(DemoSession).filter(DemoSession.user_id == user.id).first()
            if not demo:
                demo = DemoSession(user_id=user.id, demo_active=True, demo_balance=100.0)
                session.add(demo)
            demo.demo_balance = max(0.0, demo.demo_balance + pnl)
            demo.demo_pnl = demo.demo_pnl + pnl
            demo.demo_trades_count = demo.demo_trades_count + 1
            session.commit()
            session.refresh(demo)
            return {
                "demo_active": demo.demo_active,
                "demo_balance": demo.demo_balance,
                "demo_pnl": demo.demo_pnl,
                "demo_trades_count": demo.demo_trades_count,
            }
        finally:
            session.close()

    def reset_demo_balance(self, email: str) -> dict:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return {"demo_active": False, "demo_balance": 100.0}
            demo = session.query(DemoSession).filter(DemoSession.user_id == user.id).first()
            if not demo:
                demo = DemoSession(user_id=user.id, demo_active=True, demo_balance=100.0)
                session.add(demo)
            else:
                demo.demo_balance = 100.0
                demo.demo_pnl = 0.0
                demo.demo_trades_count = 0
            session.commit()
            session.refresh(demo)
            return {"demo_active": demo.demo_active, "demo_balance": demo.demo_balance}
        finally:
            session.close()

    def create_strategy(self, email: str, name: str, description: str, strategy_type: str,
                       leverage: float = 1.5, risk_tolerance: float = 0.03, fee_rate: float = 0.001,
                       is_public: bool = False, price_eur: float = 0.0) -> dict | None:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return None
            template = StrategyTemplate(
                user_id=user.id, name=name, description=description,
                strategy_type=strategy_type, leverage=leverage,
                risk_tolerance=risk_tolerance, fee_rate=fee_rate,
                is_public=is_public, price_eur=price_eur,
            )
            session.add(template)
            session.commit()
            session.refresh(template)
            if is_public:
                plugin_name = f"user_{user.id}_{template.id}"
                existing = session.query(Plugin).filter(Plugin.name == plugin_name).first()
                if not existing:
                    session.add(Plugin(name=plugin_name, price=price_eur, description=f"{name}: {description}"))
                    session.commit()
            return {"id": template.id, "name": name, "strategy_type": strategy_type, "is_public": is_public}
        finally:
            session.close()

    def list_user_strategies(self, email: str) -> list:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return []
            templates = session.query(StrategyTemplate).filter(StrategyTemplate.user_id == user.id).all()
            return [
                {"id": t.id, "name": t.name, "description": t.description, "strategy_type": t.strategy_type,
                 "leverage": t.leverage, "risk_tolerance": t.risk_tolerance, "fee_rate": t.fee_rate,
                 "is_public": t.is_public, "price_eur": t.price_eur, "trial_days": t.trial_days,
                 "created_at": t.created_at.isoformat()}
                for t in templates
            ]
        finally:
            session.close()

    def list_public_strategies(self) -> list:
        session = self.SessionLocal()
        try:
            templates = session.query(StrategyTemplate).filter(StrategyTemplate.is_public == True).all()
            return [
                {"id": t.id, "name": t.name, "description": t.description, "strategy_type": t.strategy_type,
                 "leverage": t.leverage, "price_eur": t.price_eur, "trial_days": t.trial_days}
                for t in templates
            ]
        finally:
            session.close()

    def _ensure_demo_column(self):
        with self.engine.begin() as connection:
            try:
                connection.exec_driver_sql("PRAGMA table_info(demo_sessions)")
            except Exception:
                pass

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
            session.commit()
            session.refresh(user)
            return user
        finally:
            session.close()

    def get_user(self, email: str):
        if not email:
            return None
        session = self.SessionLocal()
        try:
            return session.query(User).filter(User.email == email.strip().lower()).first()
        finally:
            session.close()

    def authenticate_user(self, email: str, password: str):
        if not email or not password:
            return None
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email.strip().lower()).first()
            if not user:
                return None
            valid = False
            is_legacy = False
            try:
                valid = check_password_hash(user.password_hash, password)
            except (ValueError, TypeError):
                legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
                valid = hmac_compare(user.password_hash, legacy_hash)
                is_legacy = valid
            if not valid:
                return None
            if is_legacy:
                user.password_hash = self.hash_password(password)
                session.commit()
            return user
        finally:
            session.close()

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

    def update_plugin(self, plugin_id: int, name: str, price: float, description: str = "") -> bool:
        session = self.SessionLocal()
        try:
            plugin = session.query(Plugin).filter(Plugin.id == plugin_id).first()
            if not plugin:
                return False
            plugin.name = name
            plugin.price = price
            plugin.description = description
            session.commit()
            return True
        finally:
            session.close()

    def delete_plugin(self, plugin_id: int) -> bool:
        session = self.SessionLocal()
        try:
            plugin = session.query(Plugin).filter(Plugin.id == plugin_id).first()
            if not plugin:
                return False
            session.query(UserPlugin).filter(UserPlugin.plugin_id == plugin_id).delete()
            session.delete(plugin)
            session.commit()
            return True
        finally:
            session.close()

    def ensure_strategy_plugins(self):
        defaults = [
            ("pure_harvester", 0.0, "Базовая стратегия сбора прибыли. Идеально для начала."),
            ("high_frequency_momentum", 0.0, "Моментум-стратегия для быстрых сделок."),
            ("compound_defender", 0.0, "Защитная стратегия сложного процента."),
            ("trend_breakout_compound", 2.5, "Прорыв тренда с компаундированием. Платиновая стратегия."),
            ("multi_sentiment_scalper", 4.0, "Мульти-сентимент скальпинг. Платиновая стратегия."),
            ("ai_adaptive_momentum", 7.5, "ИИ-адаптивный моментум. Модуль с обучением на рынке."),
            ("quantum_grid_trader", 12.0, "Квантовый сеточный трейдер. Премиум модуль."),
            ("neural_pattern_recognition", 15.0, "Нейросетевой анализ паттернов. Премиум модуль."),
            ("delta_neutral_hedger", 10.0, "Дельта-нейтральный хеджер. Институциональный модуль."),
            ("volatility_harvest", 8.0, "Сбор волатильности. Платиновая стратегия."),
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

    def purchase_plugin(self, email: str, plugin_name: str, price: float | None = None, duration_days: int = 15):
        if duration_days not in {1, 3, 7, 14, 15, 30}:
            raise ValueError("Недопустимый срок доступа.")
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            plugin = session.query(Plugin).filter(Plugin.name == plugin_name).first()
            if not user or not plugin:
                return None
            purchase = session.query(UserPlugin).filter_by(user_id=user.id, plugin_id=plugin.id).first()
            if not purchase:
                purchase = UserPlugin(user_id=user.id, plugin_id=plugin.id, active=False, access_until=datetime.utcnow() + timedelta(days=duration_days))
                session.add(purchase)
            else:
                purchase.access_until = datetime.utcnow() + timedelta(days=duration_days)
            session.commit()
            return {"name": plugin.name, "price_eur": float(plugin.price if price is None else price), "active": purchase.active, "access_until": purchase.access_until.isoformat(), "access_days": duration_days}
        finally:
            session.close()

    def set_plugin_active(self, email: str, plugin_name: str, active: bool):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            plugin = session.query(Plugin).filter(Plugin.name == plugin_name).first()
            if not user or not plugin:
                return False
            purchase = session.query(UserPlugin).filter_by(user_id=user.id, plugin_id=plugin.id).first()
            if not purchase:
                return False
            if purchase.access_until and purchase.access_until <= datetime.utcnow():
                purchase.active = False
                session.commit()
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
            now = datetime.utcnow()
            return [{"name": item[0].name, "price_eur": item[0].price, "active": item[1].active and (item[1].access_until is None or item[1].access_until > now), "access_until": item[1].access_until.isoformat() if item[1].access_until else None, "when": item[1].purchased_at.isoformat() if item[1].purchased_at else None} for item in session.query(Plugin, UserPlugin).join(UserPlugin, UserPlugin.plugin_id == Plugin.id).filter(UserPlugin.user_id == user.id).all()]
        finally:
            session.close()

    def record_memory(self, action: str, result: float, context: str = "", user_id: str | None = None):
        session = self.SessionLocal()
        try:
            memory = LearningMemory(user_id=user_id, action=action, result=float(result), context=context)
            session.add(memory)
            session.commit()
            if action == "strategy_test" and result > 0:
                profitable_tests = session.query(LearningMemory).filter(LearningMemory.action == "strategy_test", LearningMemory.result > 0).count()
                if profitable_tests >= 3 and not session.query(Plugin).filter(Plugin.name == "learned_adaptive_momentum").first():
                    session.add(Plugin(name="learned_adaptive_momentum", price=25.0, description="Стратегия, добавленная после анализа успешных тестов памяти бота."))
                    session.commit()
        finally:
            session.close()

    def recent_memories(self, user_id: str | None = None, limit: int = 20):
        session = self.SessionLocal()
        try:
            query = session.query(LearningMemory).order_by(LearningMemory.created_at.desc())
            if user_id:
                query = query.filter((LearningMemory.user_id == user_id) | (LearningMemory.user_id.is_(None)))
            return [{"action": item.action, "result": item.result, "context": item.context, "created_at": item.created_at.isoformat()} for item in query.limit(limit).all()]
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

    def record_audit(self, action: str, context: str = "", user_id: str | None = None):
        session = self.SessionLocal()
        try:
            entry = AuditLog(user_id=user_id, action=action, context=context)
            session.add(entry)
            session.commit()
        finally:
            session.close()

    def secure_login(self, email: str, password: str):
        return self.authenticate_user(email, password)

    @staticmethod
    def mask_secret(value: str) -> str:
        value = (value or "").strip()
        if len(value) <= 4:
            return "*" * len(value)
        return f"{'*' * (len(value) - 4)}{value[-4:]}"

    def get_or_create_wallet(self, email: str) -> dict:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return self._wallet_to_dict(None)
            wallet = session.query(Wallet).filter(Wallet.user_id == user.id).first()
            if not wallet:
                wallet = Wallet(user_id=user.id)
                session.add(wallet)
                session.commit()
                session.refresh(wallet)
            return self._wallet_to_dict(wallet)
        finally:
            session.close()

    @staticmethod
    def _wallet_to_dict(wallet) -> dict:
        if not wallet:
            return {"credits": 0.0, "balance": 0.0, "provider": None, "address": None, "exchange_provider": None, "exchange_address": None, "telegram": None}
        return {"credits": wallet.credits or 0.0, "balance": wallet.credits or 0.0, "provider": wallet.wallet_provider, "address": wallet.wallet_address, "exchange_provider": wallet.exchange_provider, "exchange_address": wallet.exchange_key_masked, "exchange_sandbox": bool(wallet.exchange_sandbox), "telegram": wallet.telegram_username}

    def update_wallet(self, email: str, **fields) -> dict:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return self._wallet_to_dict(None)
            wallet = session.query(Wallet).filter(Wallet.user_id == user.id).first()
            if not wallet:
                wallet = Wallet(user_id=user.id)
                session.add(wallet)
            for key, value in fields.items():
                setattr(wallet, key, value)
            session.commit()
            session.refresh(wallet)
            return self._wallet_to_dict(wallet)
        finally:
            session.close()

    def add_wallet_credits(self, email: str, amount: float) -> dict:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return self._wallet_to_dict(None)
            wallet = session.query(Wallet).filter(Wallet.user_id == user.id).first()
            if not wallet:
                wallet = Wallet(user_id=user.id)
                session.add(wallet)
            wallet.credits = max(0.0, (wallet.credits or 0.0) + amount)
            session.commit()
            session.refresh(wallet)
            return self._wallet_to_dict(wallet)
        finally:
            session.close()

    def record_trade(self, email: str, pair: str, mode: str, strategy: str, pnl: float, balance: float):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return None
            trade = Trade(user_id=user.id, pair=pair, mode=mode, strategy=strategy, pnl=float(pnl), balance=float(balance))
            session.add(trade)
            session.commit()
            session.refresh(trade)
            return trade
        finally:
            session.close()

    def list_trades(self, email: str, limit: int = 50):
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return []
            trades = session.query(Trade).filter(Trade.user_id == user.id).order_by(Trade.created_at.desc()).limit(limit).all()
            return [{"created_at": trade.created_at.isoformat(), "mode": trade.mode, "pair": trade.pair, "strategy": trade.strategy, "pnl": trade.pnl, "balance": trade.balance} for trade in trades]
        finally:
            session.close()

    def list_users(self):
        session = self.SessionLocal()
        try:
            return [(user.id, user.email, user.kyc_status, user.role) for user in session.query(User).order_by(User.id).all()]
        finally:
            session.close()

    def update_user_role(self, user_id: int, role: str) -> bool:
        session = self.SessionLocal()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            user.role = role
            session.commit()
            return True
        finally:
            session.close()

    def list_all_wallets(self):
        session = self.SessionLocal()
        try:
            rows = session.query(User, Wallet).join(Wallet, Wallet.user_id == User.id).order_by(User.id).all()
            return [(user.id, wallet.credits or 0.0, wallet.wallet_provider, wallet.wallet_address, wallet.exchange_provider, wallet.exchange_key_masked, wallet.telegram_username) for user, wallet in rows]
        finally:
            session.close()

    def list_all_purchases(self):
        session = self.SessionLocal()
        try:
            rows = session.query(User, Plugin, UserPlugin).join(UserPlugin, UserPlugin.user_id == User.id).join(Plugin, Plugin.id == UserPlugin.plugin_id).order_by(UserPlugin.purchased_at.desc()).all()
            return [(user.id, plugin.name, purchase.purchased_at.isoformat() if purchase.purchased_at else "") for user, plugin, purchase in rows]
        finally:
            session.close()

    def get_site_settings(self) -> dict:
        defaults = {"site_name": "Super CMS V12", "maintenance_mode": "false", "allowed_exchanges": "binance,bybit,kraken,okx,bitfinex", "allowed_wallets": "MetaMask,Trust Wallet,Binance Wallet,WalletConnect,Ledger,Trezor", "support_contact": ""}
        session = self.SessionLocal()
        try:
            stored = {row.key: row.value for row in session.query(SiteSetting).all()}
            return {**defaults, **stored}
        finally:
            session.close()

    def save_site_settings(self, **fields):
        session = self.SessionLocal()
        try:
            for key, value in fields.items():
                row = session.query(SiteSetting).filter(SiteSetting.key == key).first()
                if row:
                    row.value = str(value)
                else:
                    session.add(SiteSetting(key=key, value=str(value)))
            session.commit()
        finally:
            session.close()


def hmac_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left or "", right or "")
