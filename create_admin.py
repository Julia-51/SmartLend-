import sqlite3
from werkzeug.security import generate_password_hash

# --- CONFIGURATION ---
DB_NAME = 'smartlend.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_admin(username, email, password):
    hashed_pw = generate_password_hash(password)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
                    (username,email,hashed_pw,'admin'))
        conn.commit()
        print(f"✅ Admin '{username}' créé avec succès !")
    except sqlite3.IntegrityError:
        print("❌ Nom d'utilisateur ou email déjà utilisé !")
    finally:
        conn.close()

if __name__ == "__main__":
    # Modifier ici les identifiants de l'admin
    username = "Casa"
    email = "smartlendoutlook.fr"
    password = "Casa6390"
    create_admin(username, email, password)
