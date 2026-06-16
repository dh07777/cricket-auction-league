from flask import Blueprint, render_template, request, redirect, url_for, sessifrom flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import get_db_connection, get_cursor

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = get_cursor(conn)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            if user["role"] == "admin":
                return redirect(url_for("admin.admin_panel"))
            else:
                return redirect(url_for("admin.dashboard"))
        else:
            flash("Invalid username or password!", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if password != confirm:
            flash("Passwords do not match!", "danger")
            return render_template("register.html")

        conn = get_db_connection()
        cur = get_cursor(conn)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing = cur.fetchone()

        if existing:
            flash("Username already exists!", "danger")
            cur.close()
            conn.close()
            return render_template("register.html")

        hashed_pw = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                    (username, hashed_pw, "user"))
        conn.commit()
        cur.close()
        conn.close()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))