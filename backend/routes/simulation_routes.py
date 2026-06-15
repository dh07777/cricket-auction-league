import random
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import get_db_connection
from routes.admin_routes import admin_required, login_required, user_or_admin_required

sim_bp = Blueprint("sim", __name__)


# ---------------- HELPER: CALCULATE TEAM STRENGTH ----------------
def get_team_strength(conn, team_id):
    """Calculate average rating of a team's players (used for match simulation)."""
    players = conn.execute("SELECT * FROM players WHERE team_id = ?", (team_id,)).fetchall()
    if not players:
        return 50  # default strength if no players bought
    total = sum([p["rating"] for p in players])
    return total / len(players)


# ---------------- SIMULATE A SINGLE MATCH ----------------
def simulate_match(conn, team1_id, team2_id):
    """
    Simulate a cricket match score using team strength + randomness.
    Higher rated teams have higher chance & higher scores.
    """
    strength1 = get_team_strength(conn, team1_id)
    strength2 = get_team_strength(conn, team2_id)

    # Base score range 140-220, influenced by strength (weighted random)
    base1 = 140 + (strength1 - 50) * 1.2 + random.randint(-15, 20)
    base2 = 140 + (strength2 - 50) * 1.2 + random.randint(-15, 20)

    score1 = int(max(100, min(250, base1)))
    score2 = int(max(100, min(250, base2)))

    # Avoid ties - if tied, give random team +1 (super over logic)
    if score1 == score2:
        if random.random() > 0.5:
            score1 += 1
        else:
            score2 += 1

    winner_id = team1_id if score1 > score2 else team2_id
    return score1, score2, winner_id


# ---------------- GENERATE ROUND ROBIN LEAGUE FIXTURES ----------------
@sim_bp.route("/api/league/generate", methods=["POST"])
@user_or_admin_required
def generate_league():
    conn = get_db_connection()

    # Clear old league matches
    conn.execute("DELETE FROM matches WHERE stage = 'league'")

    teams = conn.execute("SELECT * FROM teams").fetchall()
    team_ids = [t["id"] for t in teams]

    # Round robin: every team plays every other team once
    for i in range(len(team_ids)):
        for j in range(i + 1, len(team_ids)):
            conn.execute("""
                INSERT INTO matches (team1_id, team2_id, stage, played)
                VALUES (?, ?, 'league', 0)
            """, (team_ids[i], team_ids[j]))

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "League fixtures generated!"})


# ---------------- SIMULATE ALL LEAGUE MATCHES ----------------
@sim_bp.route("/api/league/simulate", methods=["POST"])
@user_or_admin_required
def simulate_league():
    conn = get_db_connection()

    pending = conn.execute("SELECT * FROM matches WHERE stage='league' AND played=0").fetchall()

    if not pending:
        conn.close()
        return jsonify({"success": False, "message": "No pending matches. Generate league first."})

    for match in pending:
        score1, score2, winner_id = simulate_match(conn, match["team1_id"], match["team2_id"])
        loser_id = match["team2_id"] if winner_id == match["team1_id"] else match["team1_id"]

        # Update match record
        conn.execute("""
            UPDATE matches SET team1_score=?, team2_score=?, winner_id=?, played=1
            WHERE id=?
        """, (score1, score2, winner_id, match["id"]))

        # Generate ball-by-ball scorecard (20 overs x 6 balls per innings)
        generate_ball_by_ball(conn, match["id"], match["team1_id"], match["team2_id"], score1, score2)

        # Update points table: winner +2 points +1 win, loser +1 loss
        conn.execute("""
            UPDATE teams SET matches_played = matches_played + 1,
            wins = wins + 1, points = points + 2 WHERE id = ?
        """, (winner_id,))

        conn.execute("""
            UPDATE teams SET matches_played = matches_played + 1,
            losses = losses + 1 WHERE id = ?
        """, (loser_id,))

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Simulated {len(pending)} matches!"})


# ---------------- GENERATE PLAYOFFS (Top 4) ----------------
@sim_bp.route("/api/playoffs/generate", methods=["POST"])
@user_or_admin_required
def generate_playoffs():
    conn = get_db_connection()

    # Check league completed
    pending_league = conn.execute("SELECT COUNT(*) FROM matches WHERE stage='league' AND played=0").fetchone()[0]
    if pending_league > 0:
        conn.close()
        return jsonify({"success": False, "message": "Complete all league matches first!"})

    # Clear old playoff matches
    conn.execute("DELETE FROM matches WHERE stage != 'league'")

    top4 = conn.execute("""
        SELECT * FROM teams ORDER BY points DESC, wins DESC LIMIT 4
    """).fetchall()

    if len(top4) < 4:
        conn.close()
        return jsonify({"success": False, "message": "Not enough teams for playoffs!"})

    # Semi Final 1: Rank 1 vs Rank 4
    conn.execute("""
        INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (?, ?, 'semifinal', 0)
    """, (top4[0]["id"], top4[3]["id"]))

    # Semi Final 2: Rank 2 vs Rank 3
    conn.execute("""
        INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (?, ?, 'semifinal', 0)
    """, (top4[1]["id"], top4[2]["id"]))

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Playoff semifinals generated!"})


# ---------------- SIMULATE PLAYOFFS (Semis + Final) ----------------
@sim_bp.route("/api/playoffs/simulate", methods=["POST"])
@user_or_admin_required
def simulate_playoffs():
    conn = get_db_connection()

    semis = conn.execute("SELECT * FROM matches WHERE stage='semifinal' AND played=0").fetchall()

    if semis:
        # Simulate both semifinals
        for match in semis:
            score1, score2, winner_id = simulate_match(conn, match["team1_id"], match["team2_id"])
            conn.execute("""
                UPDATE matches SET team1_score=?, team2_score=?, winner_id=?, played=1 WHERE id=?
            """, (score1, score2, winner_id, match["id"]))
            generate_ball_by_ball(conn, match["id"], match["team1_id"], match["team2_id"], score1, score2)

        conn.commit()

        # Create Final match using semifinal winners
        sf_winners = conn.execute("""
            SELECT winner_id FROM matches WHERE stage='semifinal' AND played=1
        """).fetchall()

        winner_ids = [w["winner_id"] for w in sf_winners]

        # Check if final already exists
        existing_final = conn.execute("SELECT * FROM matches WHERE stage='final'").fetchone()
        if not existing_final and len(winner_ids) == 2:
            conn.execute("""
                INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (?, ?, 'final', 0)
            """, (winner_ids[0], winner_ids[1]))
            conn.commit()

        conn.close()
        return jsonify({"success": True, "message": "Semifinals completed! Final match ready."})

    # If semis done, simulate final
    final = conn.execute("SELECT * FROM matches WHERE stage='final' AND played=0").fetchone()
    if final:
        score1, score2, winner_id = simulate_match(conn, final["team1_id"], final["team2_id"])
        conn.execute("""
            UPDATE matches SET team1_score=?, team2_score=?, winner_id=?, played=1 WHERE id=?
        """, (score1, score2, winner_id, final["id"]))
        generate_ball_by_ball(conn, final["id"], final["team1_id"], final["team2_id"], score1, score2)
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Final completed! Champion decided.", "champion": True})

    conn.close()
    return jsonify({"success": False, "message": "Nothing to simulate. Generate playoffs first."})


# ---------------- PLAYOFF PAGE ----------------
@sim_bp.route("/playoffs")
@login_required
def playoffs_page():
    conn = get_db_connection()

    semis = conn.execute("""
        SELECT matches.*, t1.name as team1_name, t2.name as team2_name, w.name as winner_name
        FROM matches
        LEFT JOIN teams t1 ON matches.team1_id = t1.id
        LEFT JOIN teams t2 ON matches.team2_id = t2.id
        LEFT JOIN teams w ON matches.winner_id = w.id
        WHERE stage='semifinal'
        ORDER BY matches.id
    """).fetchall()

    final = conn.execute("""
        SELECT matches.*, t1.name as team1_name, t2.name as team2_name, w.name as winner_name
        FROM matches
        LEFT JOIN teams t1 ON matches.team1_id = t1.id
        LEFT JOIN teams t2 ON matches.team2_id = t2.id
        LEFT JOIN teams w ON matches.winner_id = w.id
        WHERE stage='final'
    """).fetchone()

    top4 = conn.execute("SELECT * FROM teams ORDER BY points DESC, wins DESC LIMIT 4").fetchall()

    conn.close()
    return render_template("playoff.html", semis=semis, final=final, top4=top4)


# ---------------- CHAMPION PAGE ----------------
@sim_bp.route("/champion")
@login_required
def champion_page():
    conn = get_db_connection()
    final = conn.execute("""
        SELECT matches.*, w.name as winner_name, w.id as winner_id_full
        FROM matches
        LEFT JOIN teams w ON matches.winner_id = w.id
        WHERE stage='final' AND played=1
    """).fetchone()

    champion_players = []
    if final:
        champion_players = conn.execute("""
            SELECT * FROM players WHERE team_id = ? ORDER BY rating DESC LIMIT 5
        """, (final["winner_id"],)).fetchall()

    conn.close()
    return render_template("champion.html", final=final, champion_players=champion_players)

# ---------------- GENERATE BALL-BY-BALL DATA FOR A MATCH ----------------
def generate_ball_by_ball(conn, match_id, team1_id, team2_id, score1, score2):
    """
    Generates 20 overs x 6 balls = 120 balls per innings for both teams,
    distributing the total score realistically across balls, with random wickets.
    """
    # Clear any existing ball data for this match (re-simulation safety)
    conn.execute("DELETE FROM ball_by_ball WHERE match_id = ?", (match_id,))

    for innings, (team_id, total_score) in enumerate([(team1_id, score1), (team2_id, score2)], start=1):
        strength = get_team_strength(conn, team_id)

        remaining_runs = total_score
        wickets_fallen = 0
        max_wickets = 10

        for over in range(1, 21):  # 20 overs
            for ball in range(1, 7):  # 6 balls
                balls_left = (20 - over) * 6 + (6 - ball) + 1

                # Average runs needed per remaining ball
                avg_needed = remaining_runs / balls_left if balls_left > 0 else 0

                # Weighted random run outcome based on average needed & team strength
                possible_runs = [0, 1, 1, 2, 2, 3, 4, 4, 6]
                weights = [3, 4, 3, 2, 2, 1, 2, 1, 1]

                # Bias towards higher runs if avg_needed is high, lower if low
                if avg_needed > 9:
                    weights = [1, 2, 2, 2, 2, 1, 3, 2, 2]
                elif avg_needed < 5:
                    weights = [4, 4, 3, 2, 1, 1, 1, 1, 0.5]

                run = random.choices(possible_runs, weights=weights, k=1)[0]

                # Cap run so we don't exceed remaining_runs drastically near the end
                if run > remaining_runs and balls_left == 1:
                    run = max(0, remaining_runs)

                # Wicket chance (lower for higher team strength)
                wicket_chance = max(0.02, (60 - strength) / 1000)
                is_wicket = 0
                if wickets_fallen < max_wickets - 1 and random.random() < wicket_chance:
                    is_wicket = 1
                    wickets_fallen += 1

                remaining_runs = max(0, remaining_runs - run)

                conn.execute("""
                    INSERT INTO ball_by_ball (match_id, innings, over_number, ball_number, runs, is_wicket, extra)
                    VALUES (?, ?, ?, ?, ?, ?, '')
                """, (match_id, innings, over, ball, run, is_wicket))

    conn.commit()


# ---------------- SCORECARD PAGE ----------------
@sim_bp.route("/match/<int:match_id>/scorecard")
@login_required
def match_scorecard(conn=None, match_id=None):
    match_id = request.view_args["match_id"]
    conn = get_db_connection()

    match = conn.execute("""
        SELECT matches.*, t1.name as team1_name, t2.name as team2_name, w.name as winner_name
        FROM matches
        LEFT JOIN teams t1 ON matches.team1_id = t1.id
        LEFT JOIN teams t2 ON matches.team2_id = t2.id
        LEFT JOIN teams w ON matches.winner_id = w.id
        WHERE matches.id = ?
    """, (match_id,)).fetchone()

    if not match:
        conn.close()
        flash("Match not found!", "danger")
        return redirect(url_for("team.matches"))

    # Get ball by ball for both innings, grouped by over
    innings1 = conn.execute("""
        SELECT * FROM ball_by_ball WHERE match_id=? AND innings=1 ORDER BY over_number, ball_number
    """, (match_id,)).fetchall()

    innings2 = conn.execute("""
        SELECT * FROM ball_by_ball WHERE match_id=? AND innings=2 ORDER BY over_number, ball_number
    """, (match_id,)).fetchall()

    # Group balls by over number for display
    def group_by_over(balls):
        overs = {}
        for b in balls:
            overs.setdefault(b["over_number"], []).append(b)
        return overs

    overs1 = group_by_over(innings1)
    overs2 = group_by_over(innings2)

    # Calculate total wickets per innings
    wickets1 = sum([b["is_wicket"] for b in innings1])
    wickets2 = sum([b["is_wicket"] for b in innings2])

    conn.close()

    return render_template(
        "scorecard.html",
        match=match,
        overs1=overs1,
        overs2=overs2,
        wickets1=wickets1,
        wickets2=wickets2,
        over_range=range(1, 21),
        ball_range=range(1, 7)
    )


# ---------------- UPDATE A SINGLE BALL (Edit option) ----------------
@sim_bp.route("/api/match/update-ball", methods=["POST"])
@user_or_admin_required
def update_ball():
    data = request.get_json()
    match_id = data.get("match_id")
    innings = data.get("innings")
    over_number = data.get("over_number")
    ball_number = data.get("ball_number")
    runs = int(data.get("runs"))
    is_wicket = 1 if data.get("is_wicket") else 0

    conn = get_db_connection()

    # Check if this ball record exists
    existing = conn.execute("""
        SELECT * FROM ball_by_ball WHERE match_id=? AND innings=? AND over_number=? AND ball_number=?
    """, (match_id, innings, over_number, ball_number)).fetchone()

    if existing:
        conn.execute("""
            UPDATE ball_by_ball SET runs=?, is_wicket=? 
            WHERE match_id=? AND innings=? AND over_number=? AND ball_number=?
        """, (runs, is_wicket, match_id, innings, over_number, ball_number))
    else:
        conn.execute("""
            INSERT INTO ball_by_ball (match_id, innings, over_number, ball_number, runs, is_wicket, extra)
            VALUES (?, ?, ?, ?, ?, ?, '')
        """, (match_id, innings, over_number, ball_number, runs, is_wicket))

    conn.commit()

    # Recalculate total score & wickets for this innings and update matches table
    balls = conn.execute("""
        SELECT * FROM ball_by_ball WHERE match_id=? AND innings=?
    """, (match_id, innings)).fetchall()

    total_runs = sum([b["runs"] for b in balls])
    total_wickets = sum([b["is_wicket"] for b in balls])

    match = conn.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()

    if innings == 1:
        conn.execute("UPDATE matches SET team1_score=? WHERE id=?", (total_runs, match_id))
        new_score1, new_score2 = total_runs, match["team2_score"]
    else:
        conn.execute("UPDATE matches SET team2_score=? WHERE id=?", (total_runs, match_id))
        new_score1, new_score2 = match["team1_score"], total_runs

    # Recalculate winner if both scores exist
    if new_score1 is not None and new_score2 is not None:
        old_winner = match["winner_id"]

        if new_score1 != new_score2:
            new_winner = match["team1_id"] if new_score1 > new_score2 else match["team2_id"]
        else:
            new_winner = old_winner  # keep old winner on tie to avoid recalculation issues

        if new_winner != old_winner and old_winner is not None:
            # Adjust points table: revert old result, apply new result
            old_loser = match["team2_id"] if old_winner == match["team1_id"] else match["team1_id"]
            new_loser = match["team2_id"] if new_winner == match["team1_id"] else match["team1_id"]

            # Revert old winner/loser stats
            conn.execute("UPDATE teams SET wins = wins - 1, points = points - 2 WHERE id = ?", (old_winner,))
            conn.execute("UPDATE teams SET losses = losses - 1 WHERE id = ?", (old_loser,))

            # Apply new winner/loser stats
            conn.execute("UPDATE teams SET wins = wins + 1, points = points + 2 WHERE id = ?", (new_winner,))
            conn.execute("UPDATE teams SET losses = losses + 1 WHERE id = ?", (new_loser,))

        conn.execute("UPDATE matches SET winner_id=? WHERE id=?", (new_winner, match_id))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Ball updated!",
        "total_runs": total_runs,
        "total_wickets": total_wickets
    })

    # ---------------- UPDATE TOTAL SCORE/WICKETS DIRECTLY (auto-syncs ball data proportionally) ----------------
@sim_bp.route("/api/match/update-total", methods=["POST"])
@user_or_admin_required
def update_total_score():
    """
    Allows editing the total runs and wickets for an innings directly.
    Automatically:
      - Recalculates winner
      - Adjusts points table if winner changes
      - Rescales ball-by-ball data proportionally to match the new total
    """
    data = request.get_json()
    match_id = data.get("match_id")
    innings = int(data.get("innings"))
    new_runs = int(data.get("total_runs"))
    new_wickets = int(data.get("total_wickets"))

    new_runs = max(0, new_runs)
    new_wickets = max(0, min(10, new_wickets))

    conn = get_db_connection()

    match = conn.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
    if not match:
        conn.close()
        return jsonify({"success": False, "message": "Match not found!"})

    # ---- Rescale ball-by-ball runs proportionally to new total ----
    balls = conn.execute("""
        SELECT * FROM ball_by_ball WHERE match_id=? AND innings=? ORDER BY over_number, ball_number
    """, (match_id, innings)).fetchall()

    if balls:
        old_total = sum([b["runs"] for b in balls])

        if old_total > 0:
            # Distribute new_runs proportionally across existing balls
            remaining = new_runs
            ball_list = list(balls)
            for i, b in enumerate(ball_list):
                if i == len(ball_list) - 1:
                    # Last ball gets whatever remains (avoids rounding loss)
                    new_ball_run = max(0, remaining)
                else:
                    proportion = b["runs"] / old_total
                    new_ball_run = round(new_runs * proportion)
                    new_ball_run = min(new_ball_run, remaining)
                    new_ball_run = max(0, min(6, new_ball_run))

                remaining -= new_ball_run
                conn.execute("UPDATE ball_by_ball SET runs=? WHERE id=?", (new_ball_run, b["id"]))
        else:
            # If old total was 0, just put all new runs on the last ball (capped at 6 per ball, spill to previous balls)
            ball_list = list(balls)
            remaining = new_runs
            for b in reversed(ball_list):
                give = min(6, remaining)
                conn.execute("UPDATE ball_by_ball SET runs=? WHERE id=?", (give, b["id"]))
                remaining -= give
                if remaining <= 0:
                    break

        # ---- Adjust wickets: reset all, then mark first N balls (in order) as wickets ----
        conn.execute("UPDATE ball_by_ball SET is_wicket=0 WHERE match_id=? AND innings=?", (match_id, innings))

        if new_wickets > 0:
            wicket_balls = list(balls)[:new_wickets]
            for b in wicket_balls:
                conn.execute("UPDATE ball_by_ball SET is_wicket=1 WHERE id=?", (b["id"],))

    conn.commit()

    # ---- Update match totals ----
    if innings == 1:
        conn.execute("UPDATE matches SET team1_score=? WHERE id=?", (new_runs, match_id))
        new_score1, new_score2 = new_runs, match["team2_score"]
    else:
        conn.execute("UPDATE matches SET team2_score=? WHERE id=?", (new_runs, match_id))
        new_score1, new_score2 = match["team1_score"], new_runs

    # ---- Recalculate winner & points table ----
    if new_score1 is not None and new_score2 is not None:
        old_winner = match["winner_id"]

        if new_score1 != new_score2:
            new_winner = match["team1_id"] if new_score1 > new_score2 else match["team2_id"]
        else:
            new_winner = old_winner

        if new_winner != old_winner and old_winner is not None:
            old_loser = match["team2_id"] if old_winner == match["team1_id"] else match["team1_id"]
            new_loser = match["team2_id"] if new_winner == match["team1_id"] else match["team1_id"]

            conn.execute("UPDATE teams SET wins = wins - 1, points = points - 2 WHERE id = ?", (old_winner,))
            conn.execute("UPDATE teams SET losses = losses - 1 WHERE id = ?", (old_loser,))

            conn.execute("UPDATE teams SET wins = wins + 1, points = points + 2 WHERE id = ?", (new_winner,))
            conn.execute("UPDATE teams SET losses = losses + 1 WHERE id = ?", (new_loser,))

        conn.execute("UPDATE matches SET winner_id=? WHERE id=?", (new_winner, match_id))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Score updated successfully!",
        "total_runs": new_runs,
        "total_wickets": new_wickets
    })


# ---------------- UPDATE POINTS TABLE DIRECTLY (admin/user edit) ----------------
@sim_bp.route("/api/points/update", methods=["POST"])
@user_or_admin_required
def update_points():
    """
    Allows directly editing a team's Matches Played, Wins, Losses.
    Points are auto-calculated as wins * 2 (standard cricket league scoring).
    """
    data = request.get_json()
    team_id = data.get("team_id")
    matches_played = int(data.get("matches_played"))
    wins = int(data.get("wins"))
    losses = int(data.get("losses"))

    matches_played = max(0, matches_played)
    wins = max(0, wins)
    losses = max(0, losses)

    # Auto-generate points = wins * 2
    points = wins * 2

    conn = get_db_connection()

    team = conn.execute("SELECT * FROM teams WHERE id=?", (team_id,)).fetchone()
    if not team:
        conn.close()
        return jsonify({"success": False, "message": "Team not found!"})

    conn.execute("""
        UPDATE teams SET matches_played=?, wins=?, losses=?, points=? WHERE id=?
    """, (matches_played, wins, losses, points, team_id))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"{team['name']} stats updated!",
        "points": points
    })

# ---------------- SIMULATE A SINGLE MATCH (by match ID) ----------------
@sim_bp.route("/api/match/simulate/<int:match_id>", methods=["POST"])
@user_or_admin_required
def simulate_single_match(match_id):
    """
    Simulates one specific match (league, semifinal, or final) on demand.
    Re-simulating an already played match will:
      - Revert old points table effects (if league/playoff stage with points impact)
      - Apply new result and points
      - Regenerate ball-by-ball scorecard
    """
    conn = get_db_connection()

    match = conn.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
    if not match:
        conn.close()
        return jsonify({"success": False, "message": "Match not found!"})

    # If this is a semifinal/final and prerequisite teams aren't set, block
    if not match["team1_id"] or not match["team2_id"]:
        conn.close()
        return jsonify({"success": False, "message": "Match teams not set yet!"})

    was_played = match["played"] == 1
    old_winner = match["winner_id"]

    # ---- If league stage and was already played, revert old points table effects ----
    if was_played and match["stage"] == "league" and old_winner:
        old_loser = match["team2_id"] if old_winner == match["team1_id"] else match["team1_id"]
        conn.execute("UPDATE teams SET matches_played = matches_played - 1, wins = wins - 1, points = points - 2 WHERE id = ?", (old_winner,))
        conn.execute("UPDATE teams SET matches_played = matches_played - 1, losses = losses - 1 WHERE id = ?", (old_loser,))

    # ---- Simulate new result ----
    score1, score2, winner_id = simulate_match(conn, match["team1_id"], match["team2_id"])
    loser_id = match["team2_id"] if winner_id == match["team1_id"] else match["team1_id"]

    conn.execute("""
        UPDATE matches SET team1_score=?, team2_score=?, winner_id=?, played=1 WHERE id=?
    """, (score1, score2, winner_id, match_id))

    # ---- Apply points table effects only for league stage ----
    if match["stage"] == "league":
        conn.execute("""
            UPDATE teams SET matches_played = matches_played + 1, wins = wins + 1, points = points + 2 WHERE id = ?
        """, (winner_id,))
        conn.execute("""
            UPDATE teams SET matches_played = matches_played + 1, losses = losses + 1 WHERE id = ?
        """, (loser_id,))

    conn.commit()

    # ---- Generate ball-by-ball scorecard ----
    generate_ball_by_ball(conn, match_id, match["team1_id"], match["team2_id"], score1, score2)

    # ---- If this was a semifinal, update/create the Final match with the new winner ----
    if match["stage"] == "semifinal":
        # If a final already exists, update the relevant team slot
        final = conn.execute("SELECT * FROM matches WHERE stage='final'").fetchone()

        # Find the other semifinal to determine both finalists
        other_semi = conn.execute("""
            SELECT * FROM matches WHERE stage='semifinal' AND id != ? AND played=1
        """, (match_id,)).fetchone()

        if final:
            # Update final's teams based on both semifinal winners
            if other_semi:
                team1 = winner_id
                team2 = other_semi["winner_id"]
                # Reset final result since finalists changed
                conn.execute("""
                    UPDATE matches SET team1_id=?, team2_id=?, team1_score=NULL, team2_score=NULL,
                    winner_id=NULL, played=0 WHERE id=?
                """, (team1, team2, final["id"]))
                # Clear old final ball-by-ball
                conn.execute("DELETE FROM ball_by_ball WHERE match_id=?", (final["id"],))
        elif other_semi:
            # Both semis played, create final
            conn.execute("""
                INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (?, ?, 'final', 0)
            """, (winner_id, other_semi["winner_id"]))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Match simulated! Score: {score1} - {score2}",
        "team1_score": score1,
        "team2_score": score2
    })