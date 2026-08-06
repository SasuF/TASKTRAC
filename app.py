from flask import Flask, render_template, request, redirect, url_for, session
import secrets
from db_setup import create_user, create_tables, log_in, get_all_interns, get_intern_profile, add_task, update_task_status

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)


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

#directs person after they have logged in
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

#logs out, called automatically when they leave the site
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

#allows creation of new accounts
@app.route("/create-account", methods=["GET", "POST"])
def create_account():

    if request.method == "POST":

        first_name = request.form["firstname"]
        last_name = request.form["lastname"]
        email = request.form["email"]
        password = request.form["password"]
        actual_role = request.form["actual_role"]

        success = create_user(
            first_name,
            last_name,
            email,
            password,
            "intern",
            actual_role
        )

        if not success:
            print("Account creation failed. Email may already exist.")
            return "Account creation failed. Email may already exist.", 500

        return redirect(url_for("login"))
    print("something has gone wrong, evidently")

    return render_template("create-account.html")

@app.route("/add-task/<int:user_id>", methods=["POST"])
def add_task_to_intern(user_id):

    if session.get("role") != "admin":
        return "Access denied", 403

    task = request.form["task"]

    add_task(
        user_id,
        task
    )

    return redirect(
        url_for(
            "admin_view_profile",
            user_id=user_id
        )
    )

@app.route("/update-task-status/<int:task_id>", methods=["POST"])
def update_status(task_id):

    if session.get("role") != "admin":
        return "Access denied", 403

    status = request.form["status"]

    update_task_status(task_id, status)

    return redirect(request.referrer)

#page routes
@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/intern-roster")
def intern_roster():
    if session.get("role") != "admin":
        return "Access denied", 403

    interns = get_all_interns()

    return render_template(
        "intern-roster.html",
        interns=interns
    )

@app.route("/self-view/<int:user_id>")
def self_view(user_id):
    if session.get("role") != "intern":
        return "Access denied", 403
    elif user_id != session["user_id"]:
        return "Access denied", 403

    intern, tasks = get_intern_profile(user_id)

    if intern is None:
        return "Intern not found", 404

    return render_template(
        "Self-View.html",
        intern=intern,
        tasks=tasks
    )

@app.route("/admin-view-profile/<int:user_id>")
def admin_view_profile(user_id):

    if session.get("role") != "admin":
        return "Access denied", 403

    intern, tasks = get_intern_profile(user_id)

    if intern is None:
        return "Intern not found", 404

    return render_template(
        "Admin-View-Profile.html",
        intern=intern,
        tasks=tasks
    )
#end of page routes

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )