from flask import Blueprint, render_template, request
from models import get_db_connection, get_cursor
from routes.admin_routes import login_required

team_bp = Blueprint("team", __name__)


@team_bp.route("/teams")
@login_required
def teams():
    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("SELECT * FROM teams ORDER BY points DESC, wins DESC")
    teams = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("teams.html", teams=teams)


@team_bp.route("/teams/<int:team_id>")
@login_required
def team_detail(team_id):
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM teams WHERE id = %s", (team_id,))
    team = cur.fetchone()

    cur.execute("SELECT * FROM players WHERE team_id = %s ORDER BY rating DESC", (team_id,))
    players = cur.fetchall()

    cur.close()
    conn.close()

    spent = sum([p["sold_price"] for p in players]) if players else 0
    return render_template("team_detail.html", team=team, players=players, spent=spent)


@team_bp.route("/points")
@login_required
def points():
    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("SELECT * FROM teams ORDER BY points DESC, wins DESC, nrr DESC")
    teams = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("points.html", teams=teams)


@team_bp.route("/matches")
@login_required
def matches():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT matches.*,
               t1.name as team1_name, t2.name as team2_name,
               w.name as winner_name
        FROM matches
        LEFT JOIN teams t1 ON matches.team1_id = t1.id
        LEFT JOIN teams t2 ON matches.team2_id = t2.id
        LEFT JOIN teams w ON matches.winner_id = w.id
        ORDER BY matches.id
    """)
    matches = cur.fetchall()

    cur.execute("SELECT * FROM teams ORDER BY name")
    teams = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("matches.html", matches=matches, teams=teams)