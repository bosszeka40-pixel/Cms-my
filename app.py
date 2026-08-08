from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = 'super_secret_key_v12'

DATABASE = 'cms_v12.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        email TEXT UNIQUE,
                        password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS wallets (
                        user_id INTEGER,
                        balance REAL)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE (username = ? OR email = ?) AND password = ?', (username, username, hashed_pw))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        message = 'Неверный логин или пароль.'

    return render_template('login.html', message=message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            message = 'Пароли не совпадают.'
        else:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            try:
                conn = sqlite3.connect(DATABASE)
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, hashed_pw))
                user_id = cursor.lastrowid
                cursor.execute('INSERT INTO wallets (user_id, balance) VALUES (?, ?)', (user_id, 100.0))
                conn.commit()
                conn.close()
                session['user_id'] = user_id
                return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError:
                message = 'Пользователь с таким именем или email уже существует.'
            except Exception as e:
                message = f'Ошибка регистрации: {e}'

    return render_template('register.html', message=message)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        message = 'Инструкции по восстановлению пароля отправлены на указанный email.'
    return render_template('forgot_password.html', message=message)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT username, email FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    cursor.execute('SELECT balance FROM wallets WHERE user_id = ?', (session['user_id'],))
    wallet = cursor.fetchone()
    conn.close()

    return render_template('dashboard.html', username=user[0], email=user[1], balance=wallet[0])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
