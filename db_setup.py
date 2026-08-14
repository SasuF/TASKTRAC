import os
import secrets as secrets_lib
import psycopg2
import bcrypt
from flask import Flask, render_template
from datetime import datetime, timedelta, timezone

DB_NAME = 'tasktrac'

def get_connection():
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"]
    )
    return conn

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        task TEXT NOT NULL,
        status TEXT NOT NULL
            CHECK (status IN ('current','next', 'question/request', 'feedback')),
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

def create_user(first_name, last_name, email, plain_password, role, actual_role, headshot_path=None, cv_path=None):
    conn = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users(
                first_name, last_name, email, password_hash,
                role, actual_role, needs_new_task, headshot_path, cv_path
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            first_name, last_name, email, hash_password(plain_password),
            role, actual_role, False, headshot_path, cv_path
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

def add_task(user_id, task, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks(user_id, task, status)
        VALUES (%s, %s, %s)
    """, (user_id, task, status))
    conn.commit()
    conn.close()
    print(f"task added for user {user_id}: {task}")

def set_needs_new_task(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
            SELECT needs_new_task
            FROM users
            WHERE id = %s
            """, (user_id,))

    needs = cur.fetchone()[0]

    if needs == True:
        needs = False
    else:
        needs = True

    cur.execute("""
        UPDATE users
        SET needs_new_task = %s
        WHERE id = %s
    """, (needs, user_id))

    conn.commit()
    conn.close()
    print(f"Set needs_new_task for user {user_id} to {needs}")

def get_interns_needing_tasks():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, first_name, last_name, email
        FROM users
        WHERE role = 'intern' AND needs_new_task = TRUE
    """)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()
    return rows

def add_feedback(user_id, task, status='feedback'):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks(user_id, task, status)
        VALUES (%s, %s, %s)
    """, (user_id, task, status))
    conn.commit()
    conn.close()
    print(f"task added for user {user_id}: {task}")

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
        return {"id": user_id, "role": role}

    conn.close()
    return None

def get_all_interns():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, first_name, last_name, email, headshot_path, cv_path, actual_role, needs_new_task,
               (password_hash IS NULL) AS is_pending
        FROM users
        WHERE role = 'intern' AND is_archived = FALSE
    """)
    interns = cur.fetchall()
    conn.close()
    return interns

def get_intern_profile(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, first_name, last_name, email, headshot_path,
               cv_path, actual_role, needs_new_task
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

    recent_tasks = {
        "current": [],
        "next": [],
        "question/request": [],
        "feedback": []
    }

    old_tasks = {}

    one_week_ago = datetime.now() - timedelta(days=7)

    for task in tasks:
        status = task[2]

        if task[3] >= one_week_ago:
            recent_tasks.setdefault(status, []).append(task)
        else:
            old_tasks.setdefault(status, []).append(task)

    conn.close()

    return intern, recent_tasks, old_tasks

def update_intern_info(user_id, first_name, last_name, email, actual_role):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET first_name = %s,
                last_name = %s,
                email = %s,
                actual_role = %s
            WHERE id = %s AND role = 'intern'
        """, (first_name, last_name, email, actual_role, user_id))
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

def add_invite_columns():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_token TEXT UNIQUE")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_expires TIMESTAMP")
    conn.commit()
    conn.close()
    print("invite columns ensured")

def create_intern_invite(first_name, last_name, email, actual_role):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        token = secrets_lib.token_urlsafe(32)
        expires = datetime.now() + timedelta(days=7)
        cur.execute("""
            INSERT INTO users(
                first_name, last_name, email, password_hash,
                role, actual_role, needs_new_task, invite_token, invite_expires
            )
            VALUES (%s, %s, %s, NULL, 'intern', %s, %s, %s, %s)
        """, (first_name, last_name, email, actual_role, False, token, expires))
        conn.commit()
        conn.close()
        return token
    except Exception as e:
        if conn:
            conn.rollback()
        print("DATABASE ERROR:", repr(e))
        if conn:
            conn.close()
        return None

def get_user_by_invite_token(token):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, first_name, email, invite_expires
        FROM users
        WHERE invite_token = %s
    """, (token,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "first_name": row[1], "email": row[2], "invite_expires": row[3]}

def set_password_with_token(token, plain_password):
    user = get_user_by_invite_token(token)
    if user is None or user["invite_expires"] < datetime.now():
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET password_hash = %s, invite_token = NULL, invite_expires = NULL
        WHERE id = %s
    """, (hash_password(plain_password), user["id"]))
    conn.commit()
    conn.close()
    return True

def update_user_path(user_id, headshot_path=None, cv_path=None):
    conn = get_connection()
    cur = conn.cursor()

    if headshot_path is not None:
        cur.execute("""
            UPDATE users
            SET headshot_path = %s
            WHERE id = %s
        """, (headshot_path, user_id))

    if cv_path is not None:
        cur.execute("""
            UPDATE users
            SET cv_path = %s
            WHERE id = %s
        """, (cv_path, user_id))

    conn.commit()
    conn.close()

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
    show_all()

def get_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, first_name, last_name, email, role FROM users")
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
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
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()
    return rows

def remove_task(task_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    conn.commit()
    conn.close()

def add_archived_column():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_archived BOOL NOT NULL DEFAULT FALSE
    """)
    conn.commit()
    conn.close()
    print("is_archived column ensured")

def archive_intern(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET is_archived = TRUE
        WHERE id = %s
    """, (user_id,))
    conn.commit()
    conn.close()

def unarchive_intern(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET is_archived = FALSE
        WHERE id = %s
    """, (user_id,))
    conn.commit()
    conn.close()    