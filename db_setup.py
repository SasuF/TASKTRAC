import sqlite3
import bcrypt

DB_NAME = 'tracker.db'

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('intern', 'admin')),
        headshot_path TEXT,
        cv_path TEXT,
        is_logged_in INTEGER NOT NULL DEFAULT 0 CHECK (is_logged_in IN (0,1))
        )
    """)
    
    # TASKS table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task TEXT NOT NULL,
        status TEXT NOT NULL default 'planning'
            CHECK (status IN ('planning','start', 'in progress', 'completed')),
        upload_date TEXT NOT NULL DEFAULT (datetime('now')),
        edit_date TEXT,
        awaiting_tasks INTEGER NOT NULL DEFAULT 0 CHECK (awaiting_tasks IN (0,1)),
        FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        admin_id INTEGER NOT NULL,
        comment TEXT NOT NULL,
        comment_create_date TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
        FOREIGN KEY (admin_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()
    print(f'tables created in {DB_NAME}')

def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")   

def check_password(plain_password: str, stored_hash:str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))

def create_user(first_name, last_name, email, plain_password, role):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users(first_name, last_name, email, password_hash, role)
        values(?,?,?,?,?)
    """, (first_name, last_name, email, hash_password(plain_password), role))
    conn.commit()
    conn.close()

def add_task(user_id, task, status='planning'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks(user_id, task, status)
        VALUES (?, ?, ?)
    """, (user_id, task, status))
    conn.commit()
    conn.close()
    print(f"task added for user {user_id}: {task}")

def add_feedback(task_id, admin_id, comment):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback(task_id, admin_id, comment)
        VALUES (?, ?, ?)
    """, (task_id, admin_id, comment))
    conn.commit()
    conn.close()
    print(f"feedback added to task{task_id}")

def show_all():
    conn = get_connection()
    cur = conn.cursor()
    print("USERS:")
    for row in cur.execute("SELECT id, first_name, last_name, role FROM users"):
        print(row)
    print("TASKS:")    
    for row in cur.execute("SELECT id, user_id, task FROM tasks"):
        print(row)
    conn.close()

if __name__ == "__main__":
   # add_task(1, "Complete the project documentation", "in progress")
   # add_feedback(1, 2, "Great job on completing the task!")
    show_all()
   # create_tables()  
  #  create_user("John", "Doe", "john.doe@example.com", "password123", "intern")
  #  create_user("Jane", "Smith", "jane.smith@example.com", "password456", "admin")