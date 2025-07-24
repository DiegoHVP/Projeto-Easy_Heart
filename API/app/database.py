import sqlite3

db_path = "dados_locais.db"

def inicializar_db():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dados_locais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INT,
                bat TEXT,
                spo2 FLOAT,
                press FLOAT,
                status_local TEXT,
                diagnostico_ia TEXT,
                perda FLOAT,
                data TEXT,
                hora TEXT
            )
        """)
        conn.commit()
