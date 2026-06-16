from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import get_db_connection, get_cursor
from functools import wraps

admin_bp = Blueprint("admin", __name__)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


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


def user_or_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT COUNT(*) as c FROM teams")
    total_teams = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM players")
    total_players = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM players WHERE is_sold = 0")
    remaining_players = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM players WHERE is_sold = 1")
    sold_players = cur.fetchone()["c"]

    cur.execute("SELECT * FROM teams ORDER BY name")
    teams = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("dashboard.html",
        total_teams=total_teams,
        total_players=total_players,
        remaining_players=remaining_players,
        sold_players=sold_players,
        teams=teams)


@admin_bp.route("/admin")
@admin_required
def admin_panel():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT COUNT(*) as c FROM players")
    total_players = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM teams")
    total_teams = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM players WHERE is_sold = 1")
    sold = cur.fetchone()["c"]

    cur.close()
    conn.close()

    return render_template("admin_panel.html",
        total_players=total_players,
        total_teams=total_teams,
        sold=sold)


@admin_bp.route("/admin/players")
@admin_required
def admin_players():
    conn = get_db_connection()
    cur = get_cursor(conn)

    search = request.args.get("search", "")
    role_filter = request.args.get("role", "")

    query = """
        SELECT players.*, teams.name as team_name
        FROM players LEFT JOIN teams ON players.team_id = teams.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND players.name ILIKE %s"
        params.append(f"%{search}%")
    if role_filter:
        query += " AND players.role = %s"
        params.append(role_filter)

    query += " ORDER BY players.id"
    cur.execute(query, params)
    players = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin_players.html",
        players=players, search=search, role_filter=role_filter)


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
    image = request.form.get("image") or f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}"

    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("""
        INSERT INTO players (name, role, rating, batting, bowling, fielding, base_price, image, is_sold)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
    """, (name, role, rating, batting, bowling, fielding, base_price, image))
    conn.commit()
    cur.close()
    conn.close()

    flash("Player added successfully!", "success")
    return redirect(url_for("admin.admin_players"))


@admin_bp.route("/admin/players/edit/<int:player_id>", methods=["GET", "POST"])
@admin_required
def edit_player(player_id):
    conn = get_db_connection()
    cur = get_cursor(conn)

    if request.method == "POST":
        name = request.form["name"]
        role = request.form["role"]
        rating = int(request.form["rating"])
        batting = int(request.form["batting"])
        bowling = int(request.form["bowling"])
        fielding = int(request.form["fielding"])
        base_price = float(request.form["base_price"])
        image = request.form.get("image")

        cur.execute("""
            UPDATE players SET name=%s, role=%s, rating=%s, batting=%s,
            bowling=%s, fielding=%s, base_price=%s, image=%s WHERE id=%s
        """, (name, role, rating, batting, bowling, fielding, base_price, image, player_id))
        conn.commit()
        cur.close()
        conn.close()

        flash("Player updated successfully!", "success")
        return redirect(url_for("admin.admin_players"))

    cur.execute("SELECT * FROM players WHERE id = %s", (player_id,))
    player = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("admin_players.html",
        edit_player=player, players=[], search="", role_filter="")


@admin_bp.route("/admin/players/delete/<int:player_id>")
@admin_required
def delete_player(player_id):
    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("DELETE FROM players WHERE id = %s", (player_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Player deleted!", "success")
    return redirect(url_for("admin.admin_players"))


@admin_bp.route("/admin/reset")
@admin_required
def reset_auction():
    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("UPDATE players SET is_sold=0, sold_price=0, team_id=NULL")
    cur.execute("UPDATE teams SET budget=120, matches_played=0, wins=0, losses=0, points=0, nrr=0.0")
    cur.execute("DELETE FROM matches")
    cur.execute("DELETE FROM ball_by_ball")
    conn.commit()
    cur.close()
    conn.close()

    flash("Auction & League reset successfully!", "success")
    return redirect(url_for("admin.admin_panel"))