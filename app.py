from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import secrets
from db_setup import (create_user, get_all_interns, get_intern_profile, remove_task, log_in,
get_all_interns, get_intern_profile, add_feedback, add_task, update_task_status,
set_needs_new_task, get_interns_needing_tasks, update_user_path, update_intern_info,
create_intern_invite, get_user_by_invite_token, set_password_with_token)
from email_utils import send_invite_email
import sys
import os
from datetime import datetime

app = Flask(__name__)

app.secret_key = os.environ["SECRET_KEY"]
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_HEADSHOT_EXT = {"png", "jpg", "jpeg"}
ALLOWED_CV_EXT = {"pdf", "doc", "docx"}

os.makedirs(os.path.join(UPLOAD_FOLDER, "headshots"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "CVS"), exist_ok=True)

def allowed_file(filename, allowed_exts):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_exts

#login
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = log_in(email, password)

        if user is None:
            return "Invalid email or password", 401

        session["user_id"] = user["id"]
        session["role"] = user["role"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/set-password/<token>", methods=["GET", "POST"])
def set_password(token):
    user = get_user_by_invite_token(token)

    if user is None:
        return "Invalid or expired invite link.", 404

    if user["invite_expires"] < datetime.now():
        return "This invite link has expired.", 400

    if request.method == "POST":
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if password != confirm:
            return "Passwords do not match.", 400

        success = set_password_with_token(token, password)

        if not success:
            return "This invite link has expired or is invalid.", 400

        return redirect(url_for("login"))

    return render_template("set-password.html", user=user)

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "admin":
        return redirect(url_for("intern_roster"))

    elif session.get("role") == "intern":
        return redirect(url_for(
            "self_view",
            user_id=session["user_id"]
        ))

    else:
        return "Invalid user role", 403

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/create-account", methods=["GET", "POST"])
def create_account():
    if session.get("role") != "admin":
        return "Access denied", 403

    if request.method == "POST":
        first_name = request.form["firstname"]
        last_name = request.form["lastname"]
        email = request.form["email"]
        actual_role = request.form["actual_role"]

        token = create_intern_invite(first_name, last_name, email, actual_role)

        if token is None:
            return "Could not create invite. Email may already exist.", 500

        invite_link = url_for("set_password", token=token, _external=True)

        email_status = "sent"
        try:
            send_invite_email(email, first_name, invite_link)
        except Exception as e:
            print("EMAIL ERROR:", repr(e), file=sys.stderr, flush=True)
            email_status = "failed"

        return f"Invite created for {email}. Email status: {email_status}. Link (send manually if needed): {invite_link}", 200

    return render_template("create-account.html")

@app.route("/add-task/<int:user_id>", methods=["POST"])
def add_task_to_intern(user_id):

    task = request.form["task"]
    status = request.form["status"]

    print(f"STATUS RECEIVED: {status}", flush=True)

    add_task(
        user_id,
        task,
        status
    )

    return redirect(request.referrer)

@app.route("/request-task/<int:user_id>", methods=["POST"])
def request_task(user_id):
    if session.get("role") != "intern":
        return "Access denied", 403
    elif user_id != session["user_id"]:
        return "Access denied", 403

    set_needs_new_task(user_id)
    return redirect(request.referrer)

@app.route("/edit-profile/<int:user_id>", methods=["POST"])
def edit_profile(user_id):
    if session.get("role") != "intern":
        return "Access denied", 403
    elif user_id != session["user_id"]:
        return "Access denied", 403

    first_name = request.form["firstname"]
    last_name = request.form["lastname"]
    email = request.form["email"]
    actual_role = request.form["actual_role"]

    success = update_intern_info(user_id, first_name, last_name, email, actual_role)

    if not success:
        return "Profile update failed. Email may already be in use.", 500

    return redirect(request.referrer)

@app.route("/upload-files/<int:user_id>", methods=["POST"])
def upload_files(user_id):
    if session.get("role") != "intern":
        return "Access denied", 403
    elif user_id != session["user_id"]:
        return "Access denied", 403

    headshot = request.files.get("headshot")
    cv = request.files.get("cv")

    headshot_path = None
    cv_path = None

    if headshot and headshot.filename and allowed_file(headshot.filename, ALLOWED_HEADSHOT_EXT):
        filename = secure_filename(f"user{user_id}_headshot_{headshot.filename}")
        save_path = os.path.join(UPLOAD_FOLDER, "headshots", filename)
        headshot.save(save_path)
        headshot_path = f"{UPLOAD_FOLDER}/headshots/{filename}"

    if cv and cv.filename and allowed_file(cv.filename, ALLOWED_CV_EXT):
        filename = secure_filename(f"user{user_id}_CVS_{cv.filename}")
        save_path = os.path.join(UPLOAD_FOLDER, "CVS", filename)
        cv.save(save_path)
        cv_path = f"{UPLOAD_FOLDER}/CVS/{filename}"

    update_user_path(user_id, headshot_path, cv_path)

    return redirect(request.referrer)

@app.route("/add-feedback/<int:user_id>", methods=["POST"])
def add_feedback_to_intern(user_id):

    if session.get("role") != "admin":
        return "Access denied", 403

    task = request.form["task"]

    add_feedback(
        user_id,
        task
    )

    return redirect(
        url_for(
            "admin_view_profile",
            user_id=user_id
        )
    )

@app.route("/remove-task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    remove_task(task_id)

    return redirect(request.referrer)


@app.route("/update-task-status/<int:task_id>", methods=["POST"])
def update_status(task_id):

    status = request.form["status"]

    update_task_status(task_id, status)

    return redirect(request.referrer)

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/intern-roster")
def intern_roster():
    if session.get("role") != "admin":
        return "Access denied", 403

    interns = get_all_interns()
    needing_tasks = get_interns_needing_tasks()
    needing_tasks_ids = {i['id'] for i in needing_tasks}

    return render_template(
        "intern-roster.html",
        interns=interns,
        needing_tasks=needing_tasks,
        needing_tasks_ids=needing_tasks_ids
    )

@app.route("/self-view/<int:user_id>")
def self_view(user_id):
    if session.get("role") != "intern":
        return "Access denied", 403
    elif user_id != session["user_id"]:
        return "Access denied", 403

    intern, recent_tasks, old_tasks = get_intern_profile(user_id)

    if intern is None:
        return "Intern not found", 404

    return render_template(
        "self-view.html",
        intern=intern,
        tasks=recent_tasks,
        old_tasks=old_tasks
    )

@app.route("/admin-view-profile/<int:user_id>")
def admin_view_profile(user_id):

    if session.get("role") != "admin":
        return "Access denied", 403

    intern, recent_tasks, old_tasks = get_intern_profile(user_id)

    if intern is None:
        return "Intern not found", 404

    return render_template(
        "admin-view-profile.html",
        intern=intern,
        tasks=recent_tasks,
        old_tasks=old_tasks
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )