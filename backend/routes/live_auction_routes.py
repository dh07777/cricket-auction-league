import time
import random
from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, flash
from models import get_db_connection
from routes.admin_routes import login_required, admin_required

live_bp = Blueprint("live", __name__)

BID_TIMER_SECONDS = 5  # countdown duration after each bid


# ---------------- LIVE AUCTION ROOM PAGE ----------------
@live_bp.route("/live-auction")
@login_required
def live_auction_room():
    conn = get_db_connection()

    # Check if user already has a seat
    my_seat = conn.execute("SELECT * FROM auction_seats WHERE user_id = ?", (session["user_id"],)).fetchone()

    seats_taken = conn.execute("SELECT COUNT(*) FROM auction_seats").fetchone()[0]
    all_seats = conn.execute("""
        SELECT auction_seats.*, teams.name as team_name
        FROM auction_seats JOIN teams ON auction_seats.team_id = teams.id
    """).fetchall()

    # Available teams (not yet claimed)
    claimed_team_ids = [s["team_id"] for s in all_seats]
    available_teams = conn.execute("SELECT * FROM teams").fetchall()
    available_teams = [t for t in available_teams if t["id"] not in claimed_team_ids]

    conn.close()

    return render_template(
        "live_auction.html",
        my_seat=my_seat,
        seats_taken=seats_taken,
        all_seats=all_seats,
        available_teams=available_teams,
        max_seats=8
    )


# ---------------- CLAIM A TEAM SEAT ----------------
@live_bp.route("/api/live/claim-seat", methods=["POST"])
@login_required
def claim_seat():
    data = request.get_json()
    team_id = data.get("team_id")

    conn = get_db_connection()

    # Check seat limit
    seats_taken = conn.execute("SELECT COUNT(*) FROM auction_seats").fetchone()[0]
    if seats_taken >= 8:
        conn.close()
        return jsonify({"success": False, "message": "All 8 seats are already taken!"})

    # Check if user already has a seat
    existing = conn.execute("SELECT * FROM auction_seats WHERE user_id = ?", (session["user_id"],)).fetchone()
    if existing:
        conn.close()
        return jsonify({"success": False, "message": "You already claimed a team!"})

    # Check if team already taken
    team_taken = conn.execute("SELECT * FROM auction_seats WHERE team_id = ?", (team_id,)).fetchone()
    if team_taken:
        conn.close()
        return jsonify({"success": False, "message": "This team is already claimed by another user!"})

    conn.execute("""
        INSERT INTO auction_seats (user_id, team_id, username) VALUES (?, ?, ?)
    """, (session["user_id"], team_id, session["username"]))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Team claimed successfully!"})


# ---------------- RELEASE SEAT (leave room) ----------------
@live_bp.route("/api/live/leave-seat", methods=["POST"])
@login_required
def leave_seat():
    conn = get_db_connection()
    conn.execute("DELETE FROM auction_seats WHERE user_id = ?", (session["user_id"],))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ---------------- START LIVE AUCTION (pick first player) ----------------
@live_bp.route("/api/live/start", methods=["POST"])
@login_required
def start_live_auction():
    conn = get_db_connection()

    seats_taken = conn.execute("SELECT COUNT(*) FROM auction_seats").fetchone()[0]
    if seats_taken < 1:
        conn.close()
        return jsonify({"success": False, "message": "At least 1 seat must be claimed to start!"})

    room = conn.execute("SELECT * FROM auction_room ORDER BY id DESC LIMIT 1").fetchone()

    if room["status"] == "live":
        conn.close()
        return jsonify({"success": False, "message": "Auction already live!"})

    # Pick a random unsold player
    player = conn.execute("SELECT * FROM players WHERE is_sold = 0 ORDER BY RANDOM() LIMIT 1").fetchone()

    if not player:
        conn.close()
        return jsonify({"success": False, "message": "No players left to auction!"})

    timer_end = time.time() + BID_TIMER_SECONDS

    conn.execute("""
        UPDATE auction_room SET current_player_id=?, current_bid=?, current_bid_team_id=NULL,
        timer_end=?, status='live' WHERE id=?
    """, (player["id"], player["base_price"], timer_end, room["id"]))

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Live auction started!"})


# ---------------- GET CURRENT AUCTION STATE (polled every 1s by frontend) ----------------
@live_bp.route("/api/live/state")
@login_required
def live_state():
    conn = get_db_connection()
    room = conn.execute("SELECT * FROM auction_room ORDER BY id DESC LIMIT 1").fetchone()

    response = {
        "status": room["status"],
        "current_bid": room["current_bid"],
        "timer_end": room["timer_end"],
        "server_time": time.time()
    }

    if room["current_player_id"]:
        player = conn.execute("SELECT * FROM players WHERE id = ?", (room["current_player_id"],)).fetchone()
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
        bidding_team = conn.execute("SELECT * FROM teams WHERE id = ?", (room["current_bid_team_id"],)).fetchone()
        response["current_bid_team"] = bidding_team["name"]
        response["current_bid_team_id"] = bidding_team["id"]
    else:
        response["current_bid_team"] = None
        response["current_bid_team_id"] = None

    # Get all teams with budgets for sidebar
    teams = conn.execute("""
        SELECT auction_seats.team_id, auction_seats.username, teams.name, teams.budget
        FROM auction_seats JOIN teams ON auction_seats.team_id = teams.id
    """).fetchall()
    response["teams"] = [dict(t) for t in teams]

    # Remaining players count
    response["remaining"] = conn.execute("SELECT COUNT(*) FROM players WHERE is_sold = 0").fetchone()[0]

    conn.close()
    return jsonify(response)


# ---------------- PLACE A BID (only seat holders) ----------------
@live_bp.route("/api/live/bid", methods=["POST"])
@login_required
def place_bid():
    data = request.get_json()
    bid_amount = float(data.get("bid_amount"))

    conn = get_db_connection()

    # Verify user has a seat (team)
    seat = conn.execute("SELECT * FROM auction_seats WHERE user_id = ?", (session["user_id"],)).fetchone()
    if not seat:
        conn.close()
        return jsonify({"success": False, "message": "You don't have a team seat!"})

    room = conn.execute("SELECT * FROM auction_room ORDER BY id DESC LIMIT 1").fetchone()

    if room["status"] != "live":
        conn.close()
        return jsonify({"success": False, "message": "No live auction in progress!"})

    # Check timer hasn't expired (small grace allowed via background check, but validate here too)
    if time.time() > room["timer_end"]:
        conn.close()
        return jsonify({"success": False, "message": "Time's up! Bidding closed for this player."})

    # Bid must be higher than current bid
    if bid_amount <= room["current_bid"]:
        conn.close()
        return jsonify({"success": False, "message": f"Bid must be higher than current bid (₹{room['current_bid']} Cr)"})

    # Check team can't bid on itself again consecutively (optional - allow re-raise by others only is common,
    # but we'll allow same team to NOT bid against itself)
    if room["current_bid_team_id"] == seat["team_id"]:
        conn.close()
        return jsonify({"success": False, "message": "You are already the highest bidder!"})

    # Check team budget
    team = conn.execute("SELECT * FROM teams WHERE id = ?", (seat["team_id"],)).fetchone()
    if bid_amount > team["budget"]:
        conn.close()
        return jsonify({"success": False, "message": "Insufficient budget for this bid!"})

    # Update bid + reset timer
    new_timer_end = time.time() + BID_TIMER_SECONDS
    conn.execute("""
        UPDATE auction_room SET current_bid=?, current_bid_team_id=?, timer_end=? WHERE id=?
    """, (bid_amount, seat["team_id"], new_timer_end, room["id"]))

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Bid placed!"})


# ---------------- CHECK & FINALIZE TIMER (called by frontend polling) ----------------
@live_bp.route("/api/live/check-timer", methods=["POST"])
@login_required
def check_timer():
    """
    If timer has expired:
      - If there's a current bid -> sell the player to the highest bidder
      - If no bid was placed -> mark player unsold
    Then automatically picks the next random player.
    """
    conn = get_db_connection()
    room = conn.execute("SELECT * FROM auction_room ORDER BY id DESC LIMIT 1").fetchone()

    if room["status"] != "live":
        conn.close()
        return jsonify({"finalized": False})

    if time.time() <= room["timer_end"]:
        conn.close()
        return jsonify({"finalized": False})

    player_id = room["current_player_id"]
    result_message = ""

    if room["current_bid_team_id"]:
        # SOLD to highest bidder
        sold_price = room["current_bid"]
        team_id = room["current_bid_team_id"]

        conn.execute("""
            UPDATE players SET is_sold=1, sold_price=?, team_id=? WHERE id=?
        """, (sold_price, team_id, player_id))

        conn.execute("UPDATE teams SET budget = budget - ? WHERE id = ?", (sold_price, team_id))

        team = conn.execute("SELECT name FROM teams WHERE id = ?", (team_id,)).fetchone()
        player = conn.execute("SELECT name FROM players WHERE id = ?", (player_id,)).fetchone()
        result_message = f"{player['name']} SOLD to {team['name']} for ₹{sold_price} Cr!"
    else:
        # UNSOLD - no bids
        conn.execute("""
            UPDATE players SET is_sold=1, sold_price=0, team_id=NULL WHERE id=?
        """, (player_id,))
        player = conn.execute("SELECT name FROM players WHERE id = ?", (player_id,)).fetchone()
        result_message = f"{player['name']} went UNSOLD (no bids)."

    conn.commit()

    # Pick next random unsold player
    next_player = conn.execute("SELECT * FROM players WHERE is_sold = 0 ORDER BY RANDOM() LIMIT 1").fetchone()

    if next_player:
        new_timer_end = time.time() + BID_TIMER_SECONDS
        conn.execute("""
            UPDATE auction_room SET current_player_id=?, current_bid=?, current_bid_team_id=NULL,
            timer_end=?, status='live' WHERE id=?
        """, (next_player["id"], next_player["base_price"], new_timer_end, room["id"]))
    else:
        # No more players - finish auction
        conn.execute("""
            UPDATE auction_room SET status='finished', current_player_id=NULL,
            current_bid=0, current_bid_team_id=NULL WHERE id=?
        """, (room["id"],))
        result_message += " 🎉 AUCTION COMPLETED!"

    conn.commit()
    conn.close()

    return jsonify({"finalized": True, "message": result_message})


# ---------------- RESET LIVE AUCTION ROOM (admin only) ----------------
@live_bp.route("/api/live/reset-room", methods=["POST"])
@admin_required
def reset_live_room():
    conn = get_db_connection()
    conn.execute("DELETE FROM auction_seats")
    conn.execute("""
        UPDATE auction_room SET current_player_id=NULL, current_bid=0,
        current_bid_team_id=NULL, timer_end=0, status='waiting'
    """)
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Live auction room reset!"})