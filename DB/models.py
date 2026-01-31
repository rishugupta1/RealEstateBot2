from DB.connection import get_db

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            phone TEXT PRIMARY KEY,
            city TEXT,
            bhk TEXT,
            budget INTEGER,
            updated_at TIMESTAMP DEFAULT now()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def get_user(phone):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT city, bhk, budget FROM users WHERE phone=%s", (phone,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def save_user(phone, city, bhk, budget):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (phone, city, bhk, budget)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (phone)
        DO UPDATE SET
            city=EXCLUDED.city,
            bhk=EXCLUDED.bhk,
            budget=EXCLUDED.budget,
            updated_at=now();
    """, (phone, city, bhk, budget))
    conn.commit()
    cur.close()
    conn.close()
