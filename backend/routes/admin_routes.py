from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import get_db_connection
from functools import wraps

admin_bp = Blueprint("admin", __name__)


# ---------------- LOGIN REQUIRED DECORATOR ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- ADMIN REQUIRED DECORATOR ----------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for("admin.dashboard"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- LOGGED-IN USER REQUIRED (Admin OR User) ----------------
# Used for auction, simulation, playoffs - both admin and normal users can perform these
def user_or_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------- DASHBOARD (Admin + User) ----------------
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()

    total_teams = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    total_players = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    remaining_players = conn.execute("SELECT COUNT(*) FROM players WHERE is_sold = 0").fetchone()[0]
    sold_players = conn.execute("SELECT COUNT(*) FROM players WHERE is_sold = 1").fetchone()[0]

    teams = conn.execute("SELECT * FROM teams ORDER BY name").fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_teams=total_teams,
        total_players=total_players,
        remaining_players=remaining_players,
        sold_players=sold_players,
        teams=teams
    )


# ---------------- ADMIN PANEL (Home) ----------------
@admin_bp.route("/admin")
@admin_required
def admin_panel():
    conn = get_db_connection()
    total_players = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    total_teams = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    sold = conn.execute("SELECT COUNT(*) FROM players WHERE is_sold = 1").fetchone()[0]
    conn.close()
    return render_template("admin_panel.html", total_players=total_players, total_teams=total_teams, sold=sold)


# ---------------- ADMIN: MANAGE PLAYERS ----------------
@admin_bp.route("/admin/players")
@admin_required
def admin_players():
    conn = get_db_connection()
    search = request.args.get("search", "")
    role_filter = request.args.get("role", "")

    query = "SELECT players.*, teams.name as team_name FROM players LEFT JOIN teams ON players.team_id = teams.id WHERE 1=1"
    params = []

    if search:
        query += " AND players.name LIKE ?"
        params.append(f"%{search}%")
    if role_filter:
        query += " AND players.role = ?"
        params.append(role_filter)

    query += " ORDER BY players.id"
    players = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("admin_players.html", players=players, search=search, role_filter=role_filter)


# ---------------- ADMIN: ADD PLAYER ----------------
@admin_bp.route("/admin/players/add", methods=["POST"])
@admin_required
def add_player():
    name = request.form["name"]
    role = request.form["role"]
    rating = int(request.form["rating"])
    batting = int(request.form["batting"])
    bowling = int(request.form["bowling"])
    fielding = int(request.form["fielding"])
    base_price = float(request.form["base_price"])
    image = request.form.get("image") or "https://ui-avatars.com/api/?name=" + name.replace(" ", "+")

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO players (name, role, rating, batting, bowling, fielding, base_price, image, is_sold)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (name, role, rating, batting, bowling, fielding, base_price, image))
    conn.commit()
    conn.close()

    flash("Player added successfully!", "success")
    return redirect(url_for("admin.admin_players"))


# ---------------- ADMIN: EDIT PLAYER ----------------
@admin_bp.route("/admin/players/edit/<int:player_id>", methods=["GET", "POST"])
@admin_required
def edit_player(player_id):
    conn = get_db_connection()

    if request.method == "POST":
        name = request.form["name"]
        role = request.form["role"]
        rating = int(request.form["rating"])
        batting = int(request.form["batting"])
        bowling = int(request.form["bowling"])
        fielding = int(request.form["fielding"])
        base_price = float(request.form["base_price"])
        image = request.form.get("image")

        conn.execute("""
            UPDATE players
            SET name=?, role=?, rating=?, batting=?, bowling=?, fielding=?, base_price=?, image=?
            WHERE id=?
        """, (name, role, rating, batting, bowling, fielding, base_price, image, player_id))
        conn.commit()
        conn.close()

        flash("Player updated successfully!", "success")
        return redirect(url_for("admin.admin_players"))

    player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    conn.close()
    return render_template("admin_players.html", edit_player=player, players=[], search="", role_filter="")


# ---------------- ADMIN: DELETE PLAYER ----------------
@admin_bp.route("/admin/players/delete/<int:player_id>")
@admin_required
def delete_player(player_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
    conn.commit()
    conn.close()
    flash("Player deleted!", "success")
    return redirect(url_for("admin.admin_players"))


# ---------------- ADMIN: RESET AUCTION (unsold all players, reset budgets) ----------------
@admin_bp.route("/admin/reset")
@admin_required
def reset_auction():
    conn = get_db_connection()
    conn.execute("UPDATE players SET is_sold=0, sold_price=0, team_id=NULL")
    conn.execute("UPDATE teams SET budget=120, matches_played=0, wins=0, losses=0, points=0, nrr=0.0")
    conn.execute("DELETE FROM matches")
    conn.commit()
    conn.close()
    flash("Auction & League reset successfully!", "success")
    return redirect(url_for("admin.admin_panel"))