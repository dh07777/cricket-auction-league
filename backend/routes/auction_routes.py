import random
from flask import Blueprint, render_template, request, session, jsonify
from models import get_db_connection, get_cursor
from routes.admin_routes import admin_required, login_required, user_or_admin_required

auction_bp = Blueprint("auction", __name__)


@auction_bp.route("/auction")
@login_required
def auction():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM players WHERE is_sold = 0 ORDER BY RANDOM() LIMIT 1")
    current_player = cur.fetchone()

    cur.execute("SELECT * FROM teams ORDER BY name")
    teams = cur.fetchall()

    cur.execute("SELECT COUNT(*) as c FROM players WHERE is_sold = 0")
    remaining = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM players WHERE is_sold = 1")
    sold = cur.fetchone()["c"]

    cur.close()
    conn.close()
    return render_template("auction.html", player=current_player,
        teams=teams, remaining=remaining, sold=sold)


@auction_bp.route("/api/auction/next")
@login_required
def next_player():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM players WHERE is_sold = 0 ORDER BY RANDOM() LIMIT 1")
    player = cur.fetchone()

    cur.execute("SELECT COUNT(*) as c FROM players WHERE is_sold = 0")
    remaining = cur.fetchone()["c"]

    cur.close()
    conn.close()

    if not player:
        return jsonify({"done": True, "remaining": 0})

    return jsonify({
        "done": False,
        "id": player["id"],
        "name": player["name"],
        "role": player["role"],
        "rating": player["rating"],
        "batting": player["batting"],
        "bowling": player["bowling"],
        "fielding": player["fielding"],
        "base_price": player["base_price"],
        "image": player["image"],
        "remaining": remaining
    })


@auction_bp.route("/api/auction/sell", methods=["POST"])
@user_or_admin_required
def sell_player():
    data = request.get_json()
    player_id = data.get("player_id")
    team_id = data.get("team_id")
    sold_price = float(data.get("sold_price"))

    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM teams WHERE id = %s", (team_id,))
    team = cur.fetchone()

    if not team:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Team not found"})

    if team["budget"] < sold_price:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Insufficient team budget!"})

    cur.execute("""
        UPDATE players SET is_sold=1, sold_price=%s, team_id=%s WHERE id=%s
    """, (sold_price, team_id, player_id))

    cur.execute("UPDATE teams SET budget = budget - %s WHERE id = %s", (sold_price, team_id))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "message": "Player sold successfully!"})


@auction_bp.route("/api/auction/unsold", methods=["POST"])
@user_or_admin_required
def unsold_player():
    data = request.get_json()
    player_id = data.get("player_id")

    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("UPDATE players SET is_sold=1, sold_price=0, team_id=NULL WHERE id=%s", (player_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})


@auction_bp.route("/api/auction/auto-simulate", methods=["POST"])
@user_or_admin_required
def auto_simulate_auction():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM players WHERE is_sold = 0")
    players = cur.fetchall()

    if not players:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "No players left to auction!"})

    cur.execute("SELECT * FROM teams")
    teams_data = cur.fetchall()
    team_budgets = {t["id"]: t["budget"] for t in teams_data}

    sold_count = 0
    unsold_count = 0

    for player in players:
        base_price = player["base_price"]
        rating = player["rating"]

        eligible_team_ids = [tid for tid, budget in team_budgets.items() if budget >= base_price]

        if not eligible_team_ids or random.random() < 0.15:
            cur.execute("UPDATE players SET is_sold=1, sold_price=0, team_id=NULL WHERE id=%s", (player["id"],))
            unsold_count += 1
            continue

        winning_team_id = random.choice(eligible_team_ids)
        winning_budget = team_budgets[winning_team_id]

        rating_factor = max(0.5, 1 + (rating - 50) / 50)
        raw_price = base_price * rating_factor * random.uniform(1, 3)
        sold_price = round(min(raw_price, winning_budget), 1)
        sold_price = max(base_price, min(sold_price, winning_budget))

        cur.execute("""
            UPDATE players SET is_sold=1, sold_price=%s, team_id=%s WHERE id=%s
        """, (sold_price, winning_team_id, player["id"]))

        team_budgets[winning_team_id] -= sold_price
        sold_count += 1

    for team_id, new_budget in team_budgets.items():
        cur.execute("UPDATE teams SET budget=%s WHERE id=%s", (round(new_budget, 1), team_id))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Auto auction completed! {sold_count} players sold, {unsold_count} unsold.",
        "sold": sold_count,
        "unsold": unsold_count
    })


@auction_bp.route("/auction/summary")
@login_required
def auction_summary():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM teams ORDER BY name")
    teams = cur.fetchall()

    summary = []
    for team in teams:
        cur.execute("""
            SELECT * FROM players WHERE team_id=%s AND is_sold=1 ORDER BY sold_price DESC
        """, (team["id"],))
        players = cur.fetchall()
        total_spent = sum([p["sold_price"] for p in players]) if players else 0
        summary.append({
            "team": team,
            "players": players,
            "total_spent": total_spent,
            "player_count": len(players)
        })

    cur.execute("SELECT * FROM players WHERE is_sold=1 AND team_id IS NULL ORDER BY rating DESC")
    unsold_players = cur.fetchall()

    cur.execute("SELECT COUNT(*) as c FROM players WHERE is_sold=0")
    pending_players = cur.fetchone()["c"]

    cur.close()
    conn.close()

    return render_template("auction_summary.html",
        summary=summary,
        unsold_players=unsold_players,
        pending_players=pending_players)