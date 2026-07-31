from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import db_setup

app = FastAPI(title="tasktrac.Conatix")

@app.get("/")
def read_root():
        return {"message": "Welcome to the Task Management API!"}

#requests
class usercreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    role: str

class taskcreate(BaseModel):
    user_id: int
    task: str
    status: Optional[str] = "planning"

class feedbackcreate(BaseModel):
    task_id: int
    admin_id: int
    comment: str

class login(BaseModel):
    email: str
    password: str

#post for user
@app.post("/users")
def create_user_endpoint(User: usercreate):
    if User.role not in ["admin", "intern"]:
        raise HTTPException(status_code=400, detail=" Role must be 'admin' or 'intern'.")

    existing = db_setup.get_user_by_email(User.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists.")
    
    db_setup.create_user(User.first_name, User.last_name, User.email, User.password, User.role)
    return {"message": "User created successfully."}

@app.get("/users")
def list_users():
    users = db_setup.get_users()

@app.get("/users/")
def list_users():
    return db_setup.get_users()

@app.post("/login")
def login(payload: login):
    user = db_setup.get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    
    if not db_setup.check_password(payload.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    
    return {
        "id": user['id'],
        "first_name": user['first_name'],
        "last_name": user['last_name'],
        "email": user['email'],
        "role": user['role']
    }

#post for tasks
def create_task_endpoint(task: taskcreate):
    users = db_setup.get_users()
    if not any(user['id'] == task.user_id for user in users):
        raise HTTPException(status_code=404, detail="User ID does not exist.")

    db_setup.add_task(task.user_id, task.task, task.status)
    return {"message": "Task created successfully."}

@app.get("/tasks")
def list_tasks(user_id: Optional[int] = None):
    return db_setup.get_tasks(user_id)

#post for feedback
@app.post("/feedback")
def create_feedback_endpoint(feedback: feedbackcreate):
    tasks = db_setup.get_tasks()
    if not any(task['id'] == feedback.task_id for task in tasks):
        raise HTTPException(status_code=404, detail="Task ID does not exist.")

    users = db_setup.get_users()
    if not any(user['id'] == feedback.admin_id and user['role'] == 'admin' for user in users):
        raise HTTPException(status_code=404, detail="Admin ID does not exist or is not an admin.")

    db_setup.add_feedback(feedback.task_id, feedback.admin_id, feedback.comment)
    return {"message": "Feedback created successfully."}

@app.get("/feedback")
def list_feedback(task_id: int):
    return db_setup.get_feedback(task_id)
