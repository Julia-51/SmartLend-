import sqlite3
from datetime import datetime

conn = sqlite3.connect('smartlend.db')
c = conn.cursor()

# ------------------- Table users -------------------
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('client','admin')),
    created_at TEXT NOT NULL
)
''')

# Crée l'admin par défaut
c.execute('''
INSERT OR IGNORE INTO users (id, username, password, role, created_at)
VALUES (1, 'Casa del Papa', 'Casa6390', 'admin', ?)
''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

# ------------------- Table loans -------------------
c.execute('''
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    fullname TEXT NOT NULL,
    birthdate TEXT NOT NULL,
    country TEXT NOT NULL,
    address TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    bank_account TEXT NOT NULL,
    amount REAL NOT NULL,
    income REAL NOT NULL,
    duration INTEGER NOT NULL,
    purpose TEXT NOT NULL,
    id_document TEXT NOT NULL,
    fees REAL NOT NULL,
    interest REAL NOT NULL,
    total REAL NOT NULL,
    monthly_payment REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

conn.commit()
conn.close()

print("Base SQLite SmartLend initialisée ✅")
