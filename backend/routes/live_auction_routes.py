import time
import random
from flask import Blueprint, render_template, request, session, jsonify
from models import get_db_connection, get_cursor
from routes.admin_routes import login_required, admin_required

live_bp = Blueprint("live", __name__)

BID_TIMER_SECONDS = 5


@live_bp.route("/live-auction")
@login_required
def live_auction_room():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM auction_seats WHERE user_id = ?", (session["user_id"],))
    my_seat = cur.fetchone()

    cur.execute("SELECT COUNT(*) as c FROM auction_seats")
    seats_taken = cur.fetchone()["c"]

    cur.execute("""
        SELECT auction_seats.*, teams.name as team_name
        FROM auction_seats JOIN teams ON auction_seats.team_id = teams.id
    """)
    all_seats = cur.fetchall()

    claimed_team_ids = [s["team_id"] for s in all_seats]
    cur.execute("SELECT * FROM teams")
    all_teams = cur.fetchall()
    available_teams = [t for t in all_teams if t["id"] not in claimed_team_ids]

    cur.close()
    conn.close()

    return render_template("live_auction.html",
        my_seat=my_seat,
        seats_taken=seats_taken,
        all_seats=all_seats,
        available_teams=available_teams,
        max_seats=8)


@live_bp.route("/api/live/claim-seat", methods=["POST"])
@login_required
def claim_seat():
    data = request.get_json()
    team_id = data.get("team_id")

    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT COUNT(*) as c FROM auction_seats")
    seats_taken = cur.fetchone()["c"]

    if seats_taken >= 8:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "All 8 seats are already taken!"})

    cur.execute("SELECT * FROM auction_seats WHERE user_id = ?", (session["user_id"],))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "You already claimed a team!"})

    cur.execute("SELECT * FROM auction_seats WHERE team_id = ?", (team_id,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "This team is already claimed!"})

    cur.execute("INSERT INTO auction_seats (user_id, team_id, username) VALUES (?, ?, ?)",
                (session["user_id"], team_id, session["username"]))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "message": "Team claimed successfully!"})


@live_bp.route("/api/live/leave-seat", methods=["POST"])
@login_required
def leave_seat():
    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("DELETE FROM auction_seats WHERE user_id = ?", (session["user_id"],))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})


@live_bp.route("/api/live/start", methods=["POST"])
@login_required
def start_live_auction():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT COUNT(*) as c FROM auction_seats")
    if cur.fetchone()["c"] < 1:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "At least 1 seat must be claimed!"})

    cur.execute("SELECT * FROM auction_room ORDER BY id DESC LIMIT 1")
    room = cur.fetchone()

    if room["status"] == "live":
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Auction already live!"})

    cur.execute("SELECT * FROM players WHERE is_sold = 0 ORDER BY RANDOM() LIMIT 1")
    player = cur.fetchone()

    if not player:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "No players left!"})

    timer_end = time.time() + BID_TIMER_SECONDS
    cur.execute("""
        UPDATE auction_room SET current_player_id=?, current_bid=?,
        current_bid_team_id=NULL, timer_end=?, status='live' WHERE id=?
    """, (player["id"], player["base_price"], timer_end, room["id"]))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "message": "Live auction started!"})


@live_bp.route("/api/live/state")
@login_required
def live_state():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM auction_room ORDER BY id DESC LIMIT 1")
    room = cur.fetchone()

    response = {
        "status": room["status"],
        "current_bid": room["current_bid"],
        "timer_end": room["timer_end"],
        "server_time": time.time()
    }

    if room["current_player_id"]:
        cur.execute("SELECT * FROM players WHERE id = ?", (room["current_player_id"],))
        player = cur.fetchone()
        if player:
            response["player"] = {
                "id": player["id"],
                "name": player["name"],
                "role": player["role"],
                "rating": player["rating"],
                "batting": player["batting"],
                "bowling": player["bowling"],
                "fielding": player["fielding"],
                "base_price": player["base_price"],
                "image": player["image"]
            }

    if room["current_bid_team_id"]:
        cur.execute("SELECT * FROM teams WHERE id = ?", (room["current_bid_team_id"],))
        bidding_team = cur.fetchone()
        response["current_bid_team"] = bidding_team["name"]
        response["current_bid_team_id"] = bidding_team["id"]
    else:
        response["current_bid_team"] = None
        response["current_bid_team_id"] = None

    cur.execute("""
        SELECT auction_seats.team_id, auction_seats.username, teams.name, teams.budget
        FROM auction_seats JOIN teams ON auction_seats.team_id = teams.id
    """)
    teams = cur.fetchall()
    response["teams"] = [dict(t) for t in teams]

    cur.execute("SELECT COUNT(*) as c FROM players WHERE is_sold = 0")
    response["remaining"] = cur.fetchone()["c"]

    cur.close()
    conn.close()
    return jsonify(response)


@live_bp.route("/api/live/bid", methods=["POST"])
@login_required
def place_bid():
    data = request.get_json()
    bid_amount = float(data.get("bid_amount"))

    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM auction_seats WHERE user_id = ?", (session["user_id"],))
    seat = cur.fetchone()

    if not seat:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "You don't have a team seat!"})

    cur.execute("SELECT * FROM auction_room ORDER BY id DESC LIMIT 1")
    room = cur.fetchone()

    if room["status"] != "live":
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "No live auction in progress!"})

    if time.time() > room["timer_end"]:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Time's up!"})

    if bid_amount <= room["current_bid"]:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": f"Bid must be higher than ₹{room['current_bid']} Cr"})

    if room["current_bid_team_id"] == seat["team_id"]:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "You are already the highest bidder!"})

    cur.execute("SELECT * FROM teams WHERE id = ?", (seat["team_id"],))
    team = cur.fetchone()

    if bid_amount > team["budget"]:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Insufficient budget!"})

    new_timer_end = time.time() + BID_TIMER_SECONDS
    cur.execute("""
        UPDATE auction_room SET current_bid=?, current_bid_team_id=?, timer_end=? WHERE id=?
    """, (bid_amount, seat["team_id"], new_timer_end, room["id"]))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "message": "Bid placed!"})


@live_bp.route("/api/live/check-timer", methods=["POST"])
@login_required
def check_timer():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM auction_room ORDER BY id DESC LIMIT 1")
    room = cur.fetchone()

    if room["status"] != "live" or time.time() <= room["timer_end"]:
        cur.close()
        conn.close()
        return jsonify({"finalized": False})

    player_id = room["current_player_id"]
    result_message = ""

    if room["current_bid_team_id"]:
        sold_price = room["current_bid"]
        team_id = room["current_bid_team_id"]

        cur.execute("UPDATE players SET is_sold=1, sold_price=?, team_id=? WHERE id=?",
                    (sold_price, team_id, player_id))
        cur.execute("UPDATE teams SET budget=budget-? WHERE id=?", (sold_price, team_id))

        cur.execute("SELECT name FROM teams WHERE id=?", (team_id,))
        team = cur.fetchone()
        cur.execute("SELECT name FROM players WHERE id=?", (player_id,))
        player = cur.fetchone()
        result_message = f"{player['name']} SOLD to {team['name']} for ₹{sold_price} Cr!"
    else:
        cur.execute("UPDATE players SET is_sold=1, sold_price=0, team_id=NULL WHERE id=?", (player_id,))
        cur.execute("SELECT name FROM players WHERE id=?", (player_id,))
        player = cur.fetchone()
        result_message = f"{player['name']} went UNSOLD."

    conn.commit()

    cur.execute("SELECT * FROM players WHERE is_sold=0 ORDER BY RANDOM() LIMIT 1")
    next_player = cur.fetchone()

    if next_player:
        new_timer_end = time.time() + BID_TIMER_SECONDS
        cur.execute("""
            UPDATE auction_room SET current_player_id=?, current_bid=?,
            current_bid_team_id=NULL, timer_end=?, status='live' WHERE id=?
        """, (next_player["id"], next_player["base_price"], new_timer_end, room["id"]))
    else:
        cur.execute("""
            UPDATE auction_room SET status='finished', current_player_id=NULL,
            current_bid=0, current_bid_team_id=NULL WHERE id=?
        """, (room["id"],))
        result_message += " 🎉 AUCTION COMPLETED!"

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"finalized": True, "message": result_message})


@live_bp.route("/api/live/reset-room", methods=["POST"])
@admin_required
def reset_live_room():
    conn = get_db_connection()
    cur = get_cursor(conn)
    cur.execute("DELETE FROM auction_seats")
    cur.execute("""
        UPDATE auction_room SET current_player_id=NULL, current_bid=0,
        current_bid_team_id=NULL, timer_end=0, status='waiting'
    """)
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "message": "Live auction room reset!"})