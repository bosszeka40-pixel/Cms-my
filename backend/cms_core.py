import hashlib
from datetime import datetime, timedelta
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
    def __init__(self, db_name: str = "cms_core.db"):
        self.db_name = db_name
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.init_db()

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)
        self.ensure_user_plugin_access_column()
        self.ensure_strategy_plugins()

    def ensure_user_plugin_access_column(self):
        with self.engine.begin() as connection:
            columns = connection.exec_driver_sql("PRAGMA table_info(user_plugins)").fetchall()
            if not any(column[1] == "access_until" for column in columns):
                connection.exec_driver_sql(
                    "ALTER TABLE user_plugins ADD COLUMN access_until DATETIME"
                )

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

    def purchase_plugin(
        self, email: str, plugin_name: str, price: float | None = None,
        duration_days: int = 15,
    ):
        if duration_days not in {1, 3, 7, 14, 15, 30}:
            raise ValueError("Недопустимый срок доступа.")
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
                purchase = UserPlugin(
                    user_id=user.id,
                    plugin_id=plugin.id,
                    active=False,
                    access_until=datetime.utcnow() + timedelta(days=duration_days),
                )
                session.add(purchase)
            else:
                purchase.access_until = datetime.utcnow() + timedelta(days=duration_days)
            session.commit()
            return {
                "name": plugin.name,
                "price_eur": float(plugin.price if price is None else price),
                "active": purchase.active,
                "access_until": purchase.access_until.isoformat(),
                "access_days": duration_days,
            }
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
            return [
                {
                    "name": item[0].name,
                    "price_eur": item[0].price,
                    "active": item[1].active and (
                        item[1].access_until is None or item[1].access_until > now
                    ),
                    "access_until": item[1].access_until.isoformat()
                    if item[1].access_until else None,
                    "when": item[1].purchased_at.isoformat()
                    if item[1].purchased_at else None,
                }
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
            return {
                "credits": 0.0, "balance": 0.0, "provider": None, "address": None,
                "exchange_provider": None, "exchange_address": None,
                "telegram": None,
            }
        return {
            "credits": wallet.credits or 0.0,
            "balance": wallet.credits or 0.0,
            "provider": wallet.wallet_provider,
            "address": wallet.wallet_address,
            "exchange_provider": wallet.exchange_provider,
            "exchange_address": wallet.exchange_key_masked,
            "telegram": wallet.telegram_username,
        }

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
            trade = Trade(
                user_id=user.id, pair=pair, mode=mode, strategy=strategy,
                pnl=float(pnl), balance=float(balance),
            )
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
            trades = (
                session.query(Trade)
                .filter(Trade.user_id == user.id)
                .order_by(Trade.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "created_at": trade.created_at.isoformat(),
                    "mode": trade.mode,
                    "pair": trade.pair,
                    "strategy": trade.strategy,
                    "pnl": trade.pnl,
                    "balance": trade.balance,
                }
                for trade in trades
            ]
        finally:
            session.close()

    def list_users(self):
        session = self.SessionLocal()
        try:
            return [
                (user.id, user.email, user.kyc_status, user.role)
                for user in session.query(User).order_by(User.id).all()
            ]
        finally:
            session.close()

    def list_all_wallets(self):
        session = self.SessionLocal()
        try:
            rows = (
                session.query(User, Wallet)
                .join(Wallet, Wallet.user_id == User.id)
                .order_by(User.id)
                .all()
            )
            return [
                (
                    user.id, wallet.credits or 0.0, wallet.wallet_provider,
                    wallet.wallet_address, wallet.exchange_provider,
                    wallet.exchange_key_masked, wallet.telegram_username,
                )
                for user, wallet in rows
            ]
        finally:
            session.close()

    def list_all_purchases(self):
        session = self.SessionLocal()
        try:
            rows = (
                session.query(User, Plugin, UserPlugin)
                .join(UserPlugin, UserPlugin.user_id == User.id)
                .join(Plugin, Plugin.id == UserPlugin.plugin_id)
                .order_by(UserPlugin.purchased_at.desc())
                .all()
            )
            return [
                (
                    user.id, plugin.name,
                    purchase.purchased_at.isoformat() if purchase.purchased_at else "",
                )
                for user, plugin, purchase in rows
            ]
        finally:
            session.close()

    def get_site_settings(self) -> dict:
        defaults = {
            "site_name": "Super CMS V12",
            "maintenance_mode": "false",
            "allowed_exchanges": "binance,bybit,kraken,okx,bitfinex",
            "allowed_wallets": "MetaMask,Trust Wallet,Binance Wallet,WalletConnect,Ledger,Trezor",
            "support_contact": "",
        }
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
