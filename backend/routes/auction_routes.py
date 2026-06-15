import random
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import get_db_connection
from routes.admin_routes import admin_required, login_required, user_or_admin_required

auction_bp = Blueprint("auction", __name__)


# ---------------- AUCTION PAGE ----------------
@auction_bp.route("/auction")
@login_required
def auction():
    conn = get_db_connection()

    # Get a random unsold player for auction
    current_player = conn.execute(
        "SELECT * FROM players WHERE is_sold = 0 ORDER BY RANDOM() LIMIT 1"
    ).fetchone()

    teams = conn.execute("SELECT * FROM teams ORDER BY name").fetchall()
    remaining = conn.execute("SELECT COUNT(*) FROM players WHERE is_sold = 0").fetchone()[0]
    sold = conn.execute("SELECT COUNT(*) FROM players WHERE is_sold = 1").fetchone()[0]

    conn.close()
    return render_template("auction.html", player=current_player, teams=teams, remaining=remaining, sold=sold)


# ---------------- GET NEXT RANDOM PLAYER (AJAX) ----------------
@auction_bp.route("/api/auction/next")
@login_required
def next_player():
    conn = get_db_connection()
    player = conn.execute(
        "SELECT * FROM players WHERE is_sold = 0 ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    remaining = conn.execute("SELECT COUNT(*) FROM players WHERE is_sold = 0").fetchone()[0]
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


# ---------------- PLACE BID / SELL PLAYER ----------------
@auction_bp.route("/api/auction/sell", methods=["POST"])
@user_or_admin_required
def sell_player():
    data = request.get_json()
    player_id = data.get("player_id")
    team_id = data.get("team_id")
    sold_price = float(data.get("sold_price"))

    conn = get_db_connection()
    team = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()

    if not team:
        conn.close()
        return jsonify({"success": False, "message": "Team not found"})

    if team["budget"] < sold_price:
        conn.close()
        return jsonify({"success": False, "message": "Insufficient team budget!"})

    # Update player record
    conn.execute("""
        UPDATE players SET is_sold = 1, sold_price = ?, team_id = ?
        WHERE id = ?
    """, (sold_price, team_id, player_id))

    # Deduct team budget
    conn.execute("UPDATE teams SET budget = budget - ? WHERE id = ?", (sold_price, team_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Player sold successfully!"})


# ---------------- MARK PLAYER AS UNSOLD ----------------
@auction_bp.route("/api/auction/unsold", methods=["POST"])
@user_or_admin_required
def unsold_player():
    data = request.get_json()
    player_id = data.get("player_id")

    conn = get_db_connection()
    # Mark as sold=1 but team_id=NULL so it doesn't appear again, sold_price=0
    conn.execute("UPDATE players SET is_sold = 1, sold_price = 0, team_id = NULL WHERE id = ?", (player_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# ---------------- AUTO SIMULATE ENTIRE AUCTION ----------------
@auction_bp.route("/api/auction/auto-simulate", methods=["POST"])
@user_or_admin_required
def auto_simulate_auction():
    """
    Automatically auctions ALL remaining unsold players.
    For each player:
      - Picks a random subset of teams that can afford the player
      - Higher rated players get higher bids (weighted randomness)
      - Assigns player to a randomly chosen eligible team
      - If no team can afford even the base price, marks player as unsold
    """
    conn = get_db_connection()

    players = conn.execute("SELECT * FROM players WHERE is_sold = 0").fetchall()

    if not players:
        conn.close()
        return jsonify({"success": False, "message": "No players left to auction!"})

    sold_count = 0
    unsold_count = 0

    for player in players:
        # Refresh teams list each time (budgets change as we go)
        teams = conn.execute("SELECT * FROM teams").fetchall()

        base_price = player["base_price"]
        rating = player["rating"]

        # Find teams that can afford at least the base price
        eligible_teams = [t for t in teams if t["budget"] >= base_price]

        if not eligible_teams:
            # No team can afford this player -> mark unsold
            conn.execute("""
                UPDATE players SET is_sold = 1, sold_price = 0, team_id = NULL WHERE id = ?
            """, (player["id"],))
            unsold_count += 1
            continue

        # 15% random chance a player goes unsold (simulates real auction misses)
        if random.random() < 0.15:
            conn.execute("""
                UPDATE players SET is_sold = 1, sold_price = 0, team_id = NULL WHERE id = ?
            """, (player["id"],))
            unsold_count += 1
            continue

        # Pick a random winning team from eligible teams
        winning_team = random.choice(eligible_teams)

        # Calculate a realistic sold price based on player rating + randomness
        # Higher rating => higher bidding multiplier
        rating_factor = 1 + (rating - 50) / 50   # ranges roughly 0.0 - 2.0
        rating_factor = max(0.5, rating_factor)

        max_possible = min(winning_team["budget"], base_price * rating_factor * random.uniform(1, 3))
        sold_price = round(max(base_price, min(max_possible, winning_team["budget"])), 1)

        # Final safety check - never exceed team budget
        if sold_price > winning_team["budget"]:
            sold_price = winning_team["budget"]

        # Update player record
        conn.execute("""
            UPDATE players SET is_sold = 1, sold_price = ?, team_id = ? WHERE id = ?
        """, (sold_price, winning_team["id"], player["id"]))

        # Deduct team budget
        conn.execute("UPDATE teams SET budget = budget - ? WHERE id = ?", (sold_price, winning_team["id"]))

        conn.commit()
        sold_count += 1

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Auto auction completed! {sold_count} players sold, {unsold_count} unsold.",
        "sold": sold_count,
        "unsold": unsold_count
    })
# ---------------- AUCTION SUMMARY (Team-wise bought players) ----------------
@auction_bp.route("/auction/summary")
@login_required
def auction_summary():
    """
    Shows team-wise list of players bought in the auction
    with sold price, role, rating and remaining budget.
    """
    conn = get_db_connection()

    teams = conn.execute("SELECT * FROM teams ORDER BY name").fetchall()

    summary = []
    for team in teams:
        players = conn.execute("""
            SELECT * FROM players WHERE team_id = ? AND is_sold = 1
            ORDER BY sold_price DESC
        """, (team["id"],)).fetchall()

        total_spent = sum([p["sold_price"] for p in players]) if players else 0

        summary.append({
            "team": team,
            "players": players,
            "total_spent": total_spent,
            "player_count": len(players)
        })

    # Unsold players (went unsold during auction)
    unsold_players = conn.execute("""
        SELECT * FROM players WHERE is_sold = 1 AND team_id IS NULL
        ORDER BY rating DESC
    """).fetchall()

    # Players not yet auctioned
    pending_players = conn.execute("SELECT COUNT(*) FROM players WHERE is_sold = 0").fetchone()[0]

    conn.close()

    return render_template(
        "auction_summary.html",
        summary=summary,
        unsold_players=unsold_players,
        pending_players=pending_players
    )