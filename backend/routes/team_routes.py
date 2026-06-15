from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import get_db_connection
from routes.admin_routes import login_required

team_bp = Blueprint("team", __name__)


# ---------------- TEAMS LIST ----------------
@team_bp.route("/teams")
@login_required
def teams():
    conn = get_db_connection()
    teams = conn.execute("SELECT * FROM teams ORDER BY points DESC, wins DESC").fetchall()
    conn.close()
    return render_template("teams.html", teams=teams)


# ---------------- TEAM DETAIL (players bought) ----------------
@team_bp.route("/teams/<int:team_id>")
@login_required
def team_detail(team_id):
    conn = get_db_connection()
    team = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
    players = conn.execute("SELECT * FROM players WHERE team_id = ? ORDER BY rating DESC", (team_id,)).fetchall()
    conn.close()

    spent = sum([p["sold_price"] for p in players]) if players else 0

    return render_template("team_detail.html", team=team, players=players, spent=spent)


# ---------------- POINTS TABLE ----------------
@team_bp.route("/points")
@login_required
def points():
    conn = get_db_connection()
    teams = conn.execute("""
        SELECT *,
        (wins * 2) as calc_points
        FROM teams
        ORDER BY points DESC, wins DESC, nrr DESC
    """).fetchall()
    conn.close()
    return render_template("points.html", teams=teams)


# ---------------- MATCHES PAGE ----------------
@team_bp.route("/matches")
@login_required
def matches():
    conn = get_db_connection()
    matches = conn.execute("""
        SELECT matches.*,
               t1.name as team1_name, t2.name as team2_name,
               w.name as winner_name
        FROM matches
        LEFT JOIN teams t1 ON matches.team1_id = t1.id
        LEFT JOIN teams t2 ON matches.team2_id = t2.id
        LEFT JOIN teams w ON matches.winner_id = w.id
        ORDER BY matches.id
    """).fetchall()
    teams = conn.execute("SELECT * FROM teams ORDER BY name").fetchall()
    conn.close()
    return render_template("matches.html", matches=matches, teams=teams)