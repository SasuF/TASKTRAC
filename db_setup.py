import psycopg2
import bcrypt
from flask import Flask, render_template

DB_NAME = 'tasktrac'

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="tasktrac",
        user="tasktrac_admin",
        password="admin1@3"
    )
    return conn

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    # users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('intern', 'admin')),
        actual_role TEXT NOT NULL,
        headshot_path TEXT,
        cv_path TEXT,
        is_logged_in INTEGER NOT NULL DEFAULT 0 CHECK (is_logged_in IN (0,1)),
        needs_new_task BOOL NOT NULL DEFAULT FALSE
        )
    """)
    
    # TASKS table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        task TEXT NOT NULL,
        status TEXT NOT NULL default 'planning'
            CHECK (status IN ('planning','start', 'in progress', 'completed')),
        upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        edit_date TIMESTAMP,
        awaiting_tasks INTEGER NOT NULL DEFAULT 0 CHECK (awaiting_tasks IN (0,1)),
        FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback(
        id SERIAL PRIMARY KEY,
        task_id INTEGER NOT NULL,
        admin_id INTEGER NOT NULL,
        comment TEXT NOT NULL,
        comment_create_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id),
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

def create_user(first_name, last_name, email, plain_password, role, actual_role):
    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users(
                first_name,
                last_name,
                email,
                password_hash,
                role,
                actual_role
            )
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            first_name,
            last_name,
            email,
            hash_password(plain_password),
            role,
            actual_role
        ))

        conn.commit()

        conn.close()

        return True

    except Exception as e:
        if conn:
            conn.rollback()

        print("DATABASE ERROR:", repr(e))

        if conn:
            conn.close()

        return False

def add_task(user_id, task, status='planning'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks(user_id, task, status)
        VALUES (%s, %s, %s)
    """, (user_id, task, status))
    
    conn.commit()

    conn.close()
    print(f"task added for user {user_id}: {task}")

def add_feedback(task_id, admin_id, comment):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback(task_id, admin_id, comment)
        VALUES (%s, %s, %s)
    """, (task_id, admin_id, comment))
    
    conn.commit()

    conn.close()
    print(f"feedback added to task{task_id}")

def show_all():
    conn = get_connection()
    cur = conn.cursor()
    print("USERS:")
    cur.execute("SELECT id, first_name, last_name, role FROM users")
    for row in cur.fetchall():
        print(row)
    print("TASKS:")    
    cur.execute("SELECT id, user_id, task FROM tasks")
    for row in cur.fetchall():
        print(row)

    conn.close()

def log_in(email, password):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, role, password_hash
        FROM users
        WHERE email = %s
    """, (email,))

    user = cur.fetchone()

    if user is None:

        conn.close()
        return None

    user_id, role, password_hash = user

    if check_password(password, password_hash):

        conn.close()
        return {
            "id": user_id,
            "role": role
        }


    conn.close()
    return None

def get_all_interns():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, first_name, last_name, email, headshot_path, cv_path, actual_role
        FROM users
        WHERE role = 'intern'
    """)

    interns = cur.fetchall()

    conn.close()

    return interns

def get_intern_profile(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, first_name, last_name, email, headshot_path, cv_path, role
        FROM users
        WHERE id = %s AND role = 'intern'
    """, (user_id,))

    intern = cur.fetchone()


    cur.execute("""
        SELECT id, task, status, upload_date, edit_date
        FROM tasks
        WHERE user_id = %s
        ORDER BY upload_date DESC
    """, (user_id,))

    tasks = cur.fetchall()



    task_groups = {
        "planning": [],
        "start": [],
        "in progress": [],
        "completed": []
    }


    for task in tasks:
        task_groups[task[2]].append(task)


    conn.close()
    return intern, task_groups

def update_task_status(task_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE tasks
        SET status = %s,
            edit_date = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (status, task_id))

    
    conn.commit()

    conn.close()

if __name__ == "__main__":
    create_tables()  
   # add_task(1, "Complete the project documentation", "in progress")
   # add_feedback(1, 2, "Great job on completing the task!")
    show_all()
    
    #create_user("John", "Doe", "john.doe@example.com", "password123", "intern")
    #create_user("Jane", "Smith", "jane.smith@example.com", "password456", "admin")

def get_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, first_name, last_name, email, role FROM users")
    columns = [desc[0] for desc in cur.description]
    rows= [dict(zip(columns, row)) for row in cur.fetchall()]

    conn.close()
    return rows

def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, first_name, last_name, email, password_hash, role FROM users WHERE email=%s",
                 (email,))
    row = cur.fetchone()

    conn.close()
    if row is None:
        return None
    columns = ["id", "first_name", "last_name", "email", "password_hash", "role"]
    return dict(zip(columns, row))

def get_tasks(user_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if user_id is not None:
        cur.execute("SELECT id, user_id, task, status, upload_date FROM tasks WHERE user_id=%s", 
                    (user_id,))
    else:
        cur.execute("SELECT id, user_id, task, status FROM tasks")
    columns = [desc[0] for desc in cur.description]
    rows= [dict(zip(columns, row)) for row in cur.fetchall()]

    conn.close()
    return rows

def get_feedback(task_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if task_id is not None:
        cur.execute("SELECT id, task_id, admin_id, comment, comment_create_date FROM feedback WHERE task_id=%s", 
                    (task_id,))
    else:
        cur.execute("SELECT id, task_id, admin_id, comment, comment_create_date FROM feedback")
    columns = [desc[0] for desc in cur.description]
    rows= [dict(zip(columns, row)) for row in cur.fetchall()]

    conn.close()
    return rows

