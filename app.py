from datetime import datetime
import os
from pathlib import Path

from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import hashlib
import yaml
import ccxt

from backend.bot import HFTBot
from backend.cms_core import CMSEngine
from backend.modules.strategy_manager import StrategyManager

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'development-only-change-me')

BASE_DIR = Path(__file__).resolve().parent
DATABASE = str(BASE_DIR / 'cms_v12.db')
cmse = CMSEngine()
bot = HFTBot()
strategy_manager = StrategyManager(config_path='backend/config.yaml')

EXCHANGES = ['binance', 'kraken', 'okx', 'bybit', 'bitfinex']
WALLETS = ['Metamask', 'Trust Wallet', 'Coinbase', 'Phantom', 'Ledger']

DEFAULT_PLUGINS = [
    {'name': 'Sentiment Analyzer', 'price': 29.99, 'description': 'AI-модуль для анализа новостей и торговых сигналов.'},
    {'name': 'Auto-Rebalancer', 'price': 39.99, 'description': 'Автоматическая ребалансировка портфеля по стратегии.'},
    {'name': 'Risk Guard', 'price': 19.99, 'description': 'Защита позиций и контроль риска по правилам.'},
]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        email TEXT UNIQUE,
                        password TEXT,
                        role TEXT DEFAULT 'user')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS wallets (
                        user_id INTEGER PRIMARY KEY,
                        balance REAL,
                        provider TEXT,
                        address TEXT,
                        exchange_provider TEXT,
                        exchange_address TEXT,
                        telegram TEXT,
                        telegram_token TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS plugin_purchases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        plugin_name TEXT,
                        purchased_at TEXT)''')
    conn.commit()
    cursor.execute("PRAGMA table_info('users')")
    user_columns = [row[1] for row in cursor.fetchall()]
    if 'role' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    cursor.execute("PRAGMA table_info('wallets')")
    columns = [row[1] for row in cursor.fetchall()]
    for column, definition in (
        ('provider', 'TEXT'),
        ('address', 'TEXT'),
        ('telegram', 'TEXT'),
        ('telegram_token', 'TEXT'),
    ):
        if column not in columns:
            cursor.execute(f'ALTER TABLE wallets ADD COLUMN {column} {definition}')
    if 'exchange_provider' not in columns:
        cursor.execute('ALTER TABLE wallets ADD COLUMN exchange_provider TEXT')
    if 'exchange_address' not in columns:
        cursor.execute('ALTER TABLE wallets ADD COLUMN exchange_address TEXT')
    conn.commit()
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone() is None:
        password = hash_password('admin123')
        cursor.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                       ('admin', 'admin@cms.local', password, 'admin'))
        admin_id = cursor.lastrowid
        cursor.execute('INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?, ?)', (admin_id, 1000.0))
        conn.commit()
    conn.close()


def load_plugins():
    if not cmse.list_plugins():
        for plugin in DEFAULT_PLUGINS:
            cmse.create_plugin(plugin['name'], plugin['price'], plugin['description'])


def get_user(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, role FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_wallet(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT balance, provider, address, exchange_provider, exchange_address, telegram, telegram_token FROM wallets WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'balance': row[0],
            'provider': row[1],
            'address': row[2],
            'exchange_provider': row[3],
            'exchange_address': row[4],
            'telegram': row[5],
            'telegram_token': row[6],
        }
    return {
        'balance': 0.0,
        'provider': None,
        'address': None,
        'exchange_provider': None,
        'exchange_address': None,
        'telegram': None,
        'telegram_token': None,
    }


def update_wallet(user_id, balance=None, provider=None, address=None, exchange_provider=None, exchange_address=None, telegram=None, telegram_token=None):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM wallets WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO wallets (user_id, balance, provider, address, exchange_provider, exchange_address, telegram, telegram_token) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (user_id, balance or 0.0, provider, address, exchange_provider, exchange_address, telegram, telegram_token))
    else:
        if balance is not None:
            cursor.execute('UPDATE wallets SET balance = ? WHERE user_id = ?', (balance, user_id))
        if provider is not None:
            cursor.execute('UPDATE wallets SET provider = ? WHERE user_id = ?', (provider, user_id))
        if address is not None:
            cursor.execute('UPDATE wallets SET address = ? WHERE user_id = ?', (address, user_id))
        if exchange_provider is not None:
            cursor.execute('UPDATE wallets SET exchange_provider = ? WHERE user_id = ?', (exchange_provider, user_id))
        if exchange_address is not None:
            cursor.execute('UPDATE wallets SET exchange_address = ? WHERE user_id = ?', (exchange_address, user_id))
        if telegram is not None:
            cursor.execute('UPDATE wallets SET telegram = ? WHERE user_id = ?', (telegram, user_id))
        if telegram_token is not None:
            cursor.execute('UPDATE wallets SET telegram_token = ? WHERE user_id = ?', (telegram_token, user_id))
    conn.commit()
    conn.close()


def save_plugin_purchase(user_id, plugin_name):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO plugin_purchases (user_id, plugin_name, purchased_at) VALUES (?, ?, ?)',
                   (user_id, plugin_name, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_purchases(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT plugin_name, purchased_at FROM plugin_purchases WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{'name': row[0], 'when': row[1]} for row in rows]


def get_all_users():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, role FROM users')
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_purchases():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, plugin_name, purchased_at FROM plugin_purchases')
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_wallets():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, balance, provider, address, exchange_provider, exchange_address, telegram FROM wallets')
    rows = cursor.fetchall()
    conn.close()
    return rows


init_db()
load_plugins()


@app.context_processor
def inject_user():
    return {
        'user_id': session.get('user_id'),
        'user_name': session.get('user_name'),
        'user_email': session.get('user_email'),
        'is_admin': session.get('is_admin', False),
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/home')
def home():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_pw = hash_password(password)

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, role FROM users WHERE (username = ? OR email = ?) AND password = ?',
                   (username, username, hashed_pw))
        row = cursor.fetchone()
        conn.close()

        if row:
            session['user_id'] = row[0]
            session['user_name'] = row[1]
            session['user_email'] = row[2]
            session['is_admin'] = row[3] == 'admin'
            return redirect(url_for('dashboard'))
        message = 'Неверный логин или пароль.'

    return render_template('login.html', message=message)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            message = 'Пароли не совпадают.'
        else:
            hashed_pw = hash_password(password)
            try:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                               (username, email, hashed_pw))
                user_id = cursor.lastrowid
                cursor.execute('INSERT INTO wallets (user_id, balance) VALUES (?, ?)', (user_id, 100.0))
                conn.commit()
                conn.close()
                session['user_id'] = user_id
                session['user_name'] = username
                session['user_email'] = email
                session['is_admin'] = False
                return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError:
                message = 'Пользователь с таким именем или email уже существует.'
            except Exception as e:
                message = f'Ошибка регистрации: {e}'

    return render_template('register.html', message=message)


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        message = 'Инструкции по восстановлению пароля отправлены на указанный email.'
    return render_template('forgot_password.html', message=message)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = get_user(session['user_id'])
    wallet = get_wallet(session['user_id'])

    return render_template('dashboard.html', username=user[1], email=user[2], balance=wallet['balance'], wallet=wallet)


def save_strategy_config(strategy: str, leverage: float, risk_tolerance: float):
    cfg = {
        'strategy': strategy,
        'leverage': leverage,
        'risk_tolerance': risk_tolerance,
    }
    with (BASE_DIR / 'backend' / 'config.yaml').open('w', encoding='utf-8') as handle:
        yaml.safe_dump(cfg, handle)
    strategy_manager.config = cfg


@app.route('/marketplace', methods=['GET', 'POST'])
def marketplace():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    message = None
    exchange_info = None
    plugin_message = None
    wallet = get_wallet(session['user_id'])
    purchases = get_purchases(session['user_id'])
    plugins = cmse.list_plugins()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'connect_exchange':
            provider = request.form.get('exchange_name')
            api_key = request.form.get('api_key', '')
            api_secret = request.form.get('api_secret', '')
            try:
                exchange_class = getattr(ccxt, provider)
                exchange = exchange_class({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                })
                markets = exchange.load_markets()
                exchange_info = f'Подключено {provider}. Найдено {len(markets)} рынков.'
                update_wallet(session['user_id'], exchange_provider=provider, exchange_address=api_key[:6] + '...' if api_key else None)
                wallet = get_wallet(session['user_id'])
            except Exception as e:
                message = f'Ошибка подключения: {e}'
        elif action == 'connect_wallet':
            provider = request.form.get('wallet_provider')
            address = request.form.get('wallet_address')
            if provider and address:
                update_wallet(session['user_id'], provider=provider, address=address)
                wallet = get_wallet(session['user_id'])
                message = f'Кошелек {provider} подключен.'
        elif action == 'connect_telegram':
            telegram = request.form.get('telegram_username')
            telegram_token = request.form.get('telegram_token')
            if telegram:
                update_wallet(session['user_id'], telegram=telegram, telegram_token=telegram_token)
                wallet = get_wallet(session['user_id'])
                message = f'Telegram @{telegram} подключен.'
        elif action == 'buy_plugin':
            plugin_name = request.form.get('plugin_name')
            plugin = next((p for p in plugins if p.name == plugin_name), None)
            if plugin:
                if wallet['balance'] >= plugin.price:
                    new_balance = wallet['balance'] - plugin.price
                    update_wallet(session['user_id'], balance=new_balance)
                    save_plugin_purchase(session['user_id'], plugin_name)
                    wallet = get_wallet(session['user_id'])
                    plugin_message = f'Плагин {plugin_name} куплен. Баланс: €{new_balance:.2f}.'
                else:
                    plugin_message = 'Недостаточно средств для покупки плагина.'
            else:
                plugin_message = 'Плагин не найден.'

    return render_template(
        'marketplace.html',
        exchanges=EXCHANGES,
        wallets=WALLETS,
        wallet=wallet,
        plugins=plugins,
        message=message,
        exchange_info=exchange_info,
        plugin_message=plugin_message,
        purchases=purchases,
    )


@app.route('/bot-management', methods=['GET', 'POST'])
def bot_management():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    message = None
    manual_trade_result = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'start_bot':
            bot.start()
            message = 'Бот запущен.'
        elif action == 'stop_bot':
            bot.stop()
            message = 'Бот остановлен.'
        elif action == 'save_strategy':
            strategy = request.form.get('strategy')
            leverage = float(request.form.get('leverage', 1.5))
            risk_tolerance = float(request.form.get('risk_tolerance', 0.03))
            save_strategy_config(strategy, leverage, risk_tolerance)
            message = 'Настройки стратегии сохранены.'
        elif action == 'manual_trade':
            news_sentiment = float(request.form.get('news_sentiment', 0.0))
            price_change = float(request.form.get('price_change', 0.0))
            current_balance = float(request.form.get('current_balance', 100.0))
            manual_trade_result = strategy_manager.execute(news_sentiment, price_change, current_balance)
            message = 'Ручная сделка выполнена.'

    bot_status = bot.status()
    current_strategy = strategy_manager.current_strategy()
    config = strategy_manager.config
    balance_history = [
        {'time': item['time'], 'value': 100 + idx * 3}
        for idx, item in enumerate(bot_status.get('stats', []))
    ]
    if not balance_history:
        balance_history = [{'time': 'start', 'value': 100}]

    return render_template(
        'bot_management.html',
        bot_status=bot_status,
        current_strategy=current_strategy,
        config=config,
        message=message,
        manual_trade_result=manual_trade_result,
        balance_history=balance_history,
    )

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))

    message = None
    if request.method == 'POST':
        name = request.form.get('plugin_name')
        price = float(request.form.get('plugin_price', 0.0))
        description = request.form.get('plugin_description', '')
        if name and price > 0:
            cmse.create_plugin(name, price, description)
            message = f'Плагин {name} добавлен.'

    users = get_all_users()
    plugins = cmse.list_plugins()
    wallets = get_all_wallets()
    purchases = get_all_purchases()
    return render_template('admin.html', users=users, plugins=plugins, purchases=purchases, wallets=wallets, message=message)


@app.route('/wallet', methods=['GET', 'POST'])
def wallet_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    wallet = get_wallet(session['user_id'])
    message = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'buy_usdt':
            try:
                amount = float(request.form.get('amount', '0'))
                if amount <= 0:
                    message = 'Введите положительную сумму.'
                else:
                    # Простая симуляция покупки USDT (1 USD = 1 USDT)
                    new_balance = wallet['balance'] + amount
                    update_wallet(session['user_id'], balance=new_balance)
                    wallet = get_wallet(session['user_id'])
                    message = f'Куплено {amount:.2f} USDT. Новый баланс: {wallet["balance"]:.2f}.'
            except ValueError:
                message = 'Неверная сумма.'

    return render_template('wallet.html', wallet=wallet, message=message)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5000')),
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
    )
