import random
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import get_db_connection, get_cursor
from routes.admin_routes import admin_required, login_required, user_or_admin_required

sim_bp = Blueprint("sim", __name__)


def get_team_strength(cur, team_id):
    cur.execute("SELECT rating FROM players WHERE team_id = %s", (team_id,))
    players = cur.fetchall()
    if not players:
        return 50
    return sum([p["rating"] for p in players]) / len(players)


def simulate_match(cur, team1_id, team2_id):
    strength1 = get_team_strength(cur, team1_id)
    strength2 = get_team_strength(cur, team2_id)

    base1 = 140 + (strength1 - 50) * 1.2 + random.randint(-15, 20)
    base2 = 140 + (strength2 - 50) * 1.2 + random.randint(-15, 20)

    score1 = int(max(100, min(250, base1)))
    score2 = int(max(100, min(250, base2)))

    if score1 == score2:
        if random.random() > 0.5:
            score1 += 1
        else:
            score2 += 1

    winner_id = team1_id if score1 > score2 else team2_id
    return score1, score2, winner_id


def generate_ball_by_ball(conn, cur, match_id, team1_id, team2_id, score1, score2):
    cur.execute("DELETE FROM ball_by_ball WHERE match_id = %s", (match_id,))

    for innings, (team_id, total_score) in enumerate([(team1_id, score1), (team2_id, score2)], start=1):
        strength = get_team_strength(cur, team_id)
        remaining_runs = total_score
        wickets_fallen = 0

        for over in range(1, 21):
            for ball in range(1, 7):
                balls_left = (20 - over) * 6 + (6 - ball) + 1
                avg_needed = remaining_runs / balls_left if balls_left > 0 else 0

                possible_runs = [0, 1, 1, 2, 2, 3, 4, 4, 6]
                weights = [3, 4, 3, 2, 2, 1, 2, 1, 1]

                if avg_needed > 9:
                    weights = [1, 2, 2, 2, 2, 1, 3, 2, 2]
                elif avg_needed < 5:
                    weights = [4, 4, 3, 2, 1, 1, 1, 1, 0.5]

                run = random.choices(possible_runs, weights=weights, k=1)[0]

                if run > remaining_runs and balls_left == 1:
                    run = max(0, remaining_runs)

                wicket_chance = max(0.02, (60 - strength) / 1000)
                is_wicket = 0
                if wickets_fallen < 9 and random.random() < wicket_chance:
                    is_wicket = 1
                    wickets_fallen += 1

                remaining_runs = max(0, remaining_runs - run)

                cur.execute("""
                    INSERT INTO ball_by_ball (match_id, innings, over_number, ball_number, runs, is_wicket, extra)
                    VALUES (%s, %s, %s, %s, %s, %s, '')
                """, (match_id, innings, over, ball, run, is_wicket))

    conn.commit()


@sim_bp.route("/api/league/generate", methods=["POST"])
@user_or_admin_required
def generate_league():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("DELETE FROM matches WHERE stage = 'league'")
    cur.execute("SELECT * FROM teams")
    teams = cur.fetchall()
    team_ids = [t["id"] for t in teams]

    for i in range(len(team_ids)):
        for j in range(i + 1, len(team_ids)):
            cur.execute("""
                INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (%s, %s, 'league', 0)
            """, (team_ids[i], team_ids[j]))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "message": "League fixtures generated!"})


@sim_bp.route("/api/league/simulate", methods=["POST"])
@user_or_admin_required
def simulate_league():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM matches WHERE stage='league' AND played=0")
    pending = cur.fetchall()

    if not pending:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "No pending matches. Generate league first."})

    for match in pending:
        score1, score2, winner_id = simulate_match(cur, match["team1_id"], match["team2_id"])
        loser_id = match["team2_id"] if winner_id == match["team1_id"] else match["team1_id"]

        cur.execute("""
            UPDATE matches SET team1_score=%s, team2_score=%s, winner_id=%s, played=1 WHERE id=%s
        """, (score1, score2, winner_id, match["id"]))

        cur.execute("""
            UPDATE teams SET matches_played=matches_played+1, wins=wins+1, points=points+2 WHERE id=%s
        """, (winner_id,))

        cur.execute("""
            UPDATE teams SET matches_played=matches_played+1, losses=losses+1 WHERE id=%s
        """, (loser_id,))

        conn.commit()
        generate_ball_by_ball(conn, cur, match["id"], match["team1_id"], match["team2_id"], score1, score2)

    cur.close()
    conn.close()
    return jsonify({"success": True, "message": f"Simulated {len(pending)} matches!"})


@sim_bp.route("/api/playoffs/generate", methods=["POST"])
@user_or_admin_required
def generate_playoffs():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT COUNT(*) as c FROM matches WHERE stage='league' AND played=0")
    pending = cur.fetchone()["c"]

    if pending > 0:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Complete all league matches first!"})

    cur.execute("DELETE FROM matches WHERE stage != 'league'")
    cur.execute("SELECT * FROM teams ORDER BY points DESC, wins DESC LIMIT 4")
    top4 = cur.fetchall()

    if len(top4) < 4:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Not enough teams!"})

    cur.execute("INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (%s, %s, 'semifinal', 0)",
                (top4[0]["id"], top4[3]["id"]))
    cur.execute("INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (%s, %s, 'semifinal', 0)",
                (top4[1]["id"], top4[2]["id"]))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True, "message": "Playoff semifinals generated!"})


@sim_bp.route("/api/playoffs/simulate", methods=["POST"])
@user_or_admin_required
def simulate_playoffs():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM matches WHERE stage='semifinal' AND played=0")
    semis = cur.fetchall()

    if semis:
        for match in semis:
            score1, score2, winner_id = simulate_match(cur, match["team1_id"], match["team2_id"])
            cur.execute("""
                UPDATE matches SET team1_score=%s, team2_score=%s, winner_id=%s, played=1 WHERE id=%s
            """, (score1, score2, winner_id, match["id"]))
            conn.commit()
            generate_ball_by_ball(conn, cur, match["id"], match["team1_id"], match["team2_id"], score1, score2)

        cur.execute("SELECT winner_id FROM matches WHERE stage='semifinal' AND played=1")
        sf_winners = cur.fetchall()
        winner_ids = [w["winner_id"] for w in sf_winners]

        cur.execute("SELECT * FROM matches WHERE stage='final'")
        existing_final = cur.fetchone()

        if not existing_final and len(winner_ids) == 2:
            cur.execute("INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (%s, %s, 'final', 0)",
                        (winner_ids[0], winner_ids[1]))
            conn.commit()

        cur.close()
        conn.close()
        return jsonify({"success": True, "message": "Semifinals completed! Final match ready."})

    cur.execute("SELECT * FROM matches WHERE stage='final' AND played=0")
    final = cur.fetchone()

    if final:
        score1, score2, winner_id = simulate_match(cur, final["team1_id"], final["team2_id"])
        cur.execute("""
            UPDATE matches SET team1_score=%s, team2_score=%s, winner_id=%s, played=1 WHERE id=%s
        """, (score1, score2, winner_id, final["id"]))
        conn.commit()
        generate_ball_by_ball(conn, cur, final["id"], final["team1_id"], final["team2_id"], score1, score2)
        cur.close()
        conn.close()
        return jsonify({"success": True, "message": "Final completed! Champion decided.", "champion": True})

    cur.close()
    conn.close()
    return jsonify({"success": False, "message": "Nothing to simulate."})


@sim_bp.route("/playoffs")
@login_required
def playoffs_page():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT matches.*, t1.name as team1_name, t2.name as team2_name, w.name as winner_name
        FROM matches
        LEFT JOIN teams t1 ON matches.team1_id = t1.id
        LEFT JOIN teams t2 ON matches.team2_id = t2.id
        LEFT JOIN teams w ON matches.winner_id = w.id
        WHERE stage='semifinal' ORDER BY matches.id
    """)
    semis = cur.fetchall()

    cur.execute("""
        SELECT matches.*, t1.name as team1_name, t2.name as team2_name, w.name as winner_name
        FROM matches
        LEFT JOIN teams t1 ON matches.team1_id = t1.id
        LEFT JOIN teams t2 ON matches.team2_id = t2.id
        LEFT JOIN teams w ON matches.winner_id = w.id
        WHERE stage='final'
    """)
    final = cur.fetchone()

    cur.execute("SELECT * FROM teams ORDER BY points DESC, wins DESC LIMIT 4")
    top4 = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("playoff.html", semis=semis, final=final, top4=top4)


@sim_bp.route("/champion")
@login_required
def champion_page():
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT matches.*, w.name as winner_name
        FROM matches
        LEFT JOIN teams w ON matches.winner_id = w.id
        WHERE stage='final' AND played=1
    """)
    final = cur.fetchone()

    champion_players = []
    if final:
        cur.execute("""
            SELECT * FROM players WHERE team_id=%s ORDER BY rating DESC LIMIT 5
        """, (final["winner_id"],))
        champion_players = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("champion.html", final=final, champion_players=champion_players)


@sim_bp.route("/match/<int:match_id>/scorecard")
@login_required
def match_scorecard(match_id):
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT matches.*, t1.name as team1_name, t2.name as team2_name, w.name as winner_name
        FROM matches
        LEFT JOIN teams t1 ON matches.team1_id = t1.id
        LEFT JOIN teams t2 ON matches.team2_id = t2.id
        LEFT JOIN teams w ON matches.winner_id = w.id
        WHERE matches.id = %s
    """, (match_id,))
    match = cur.fetchone()

    if not match:
        cur.close()
        conn.close()
        flash("Match not found!", "danger")
        return redirect(url_for("team.matches"))

    cur.execute("SELECT * FROM ball_by_ball WHERE match_id=%s AND innings=1 ORDER BY over_number, ball_number", (match_id,))
    innings1 = cur.fetchall()

    cur.execute("SELECT * FROM ball_by_ball WHERE match_id=%s AND innings=2 ORDER BY over_number, ball_number", (match_id,))
    innings2 = cur.fetchall()

    def group_by_over(balls):
        overs = {}
        for b in balls:
            overs.setdefault(b["over_number"], []).append(b)
        return overs

    overs1 = group_by_over(innings1)
    overs2 = group_by_over(innings2)

    wickets1 = sum([b["is_wicket"] for b in innings1])
    wickets2 = sum([b["is_wicket"] for b in innings2])

    cur.close()
    conn.close()

    return render_template("scorecard.html",
        match=match, overs1=overs1, overs2=overs2,
        wickets1=wickets1, wickets2=wickets2,
        over_range=range(1, 21), ball_range=range(1, 7))


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
    cur = get_cursor(conn)

    cur.execute("""
        SELECT * FROM ball_by_ball WHERE match_id=%s AND innings=%s AND over_number=%s AND ball_number=%s
    """, (match_id, innings, over_number, ball_number))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE ball_by_ball SET runs=%s, is_wicket=%s
            WHERE match_id=%s AND innings=%s AND over_number=%s AND ball_number=%s
        """, (runs, is_wicket, match_id, innings, over_number, ball_number))
    else:
        cur.execute("""
            INSERT INTO ball_by_ball (match_id, innings, over_number, ball_number, runs, is_wicket, extra)
            VALUES (%s, %s, %s, %s, %s, %s, '')
        """, (match_id, innings, over_number, ball_number, runs, is_wicket))

    conn.commit()

    cur.execute("SELECT * FROM ball_by_ball WHERE match_id=%s AND innings=%s", (match_id, innings))
    balls = cur.fetchall()
    total_runs = sum([b["runs"] for b in balls])
    total_wickets = sum([b["is_wicket"] for b in balls])

    cur.execute("SELECT * FROM matches WHERE id=%s", (match_id,))
    match = cur.fetchone()

    if innings == 1:
        cur.execute("UPDATE matches SET team1_score=%s WHERE id=%s", (total_runs, match_id))
        new_score1, new_score2 = total_runs, match["team2_score"]
    else:
        cur.execute("UPDATE matches SET team2_score=%s WHERE id=%s", (total_runs, match_id))
        new_score1, new_score2 = match["team1_score"], total_runs

    if new_score1 is not None and new_score2 is not None:
        old_winner = match["winner_id"]
        new_winner = match["team1_id"] if new_score1 > new_score2 else match["team2_id"]

        if new_winner != old_winner and old_winner is not None:
            old_loser = match["team2_id"] if old_winner == match["team1_id"] else match["team1_id"]
            new_loser = match["team2_id"] if new_winner == match["team1_id"] else match["team1_id"]

            cur.execute("UPDATE teams SET wins=wins-1, points=points-2 WHERE id=%s", (old_winner,))
            cur.execute("UPDATE teams SET losses=losses-1 WHERE id=%s", (old_loser,))
            cur.execute("UPDATE teams SET wins=wins+1, points=points+2 WHERE id=%s", (new_winner,))
            cur.execute("UPDATE teams SET losses=losses+1 WHERE id=%s", (new_loser,))

        cur.execute("UPDATE matches SET winner_id=%s WHERE id=%s", (new_winner, match_id))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True, "message": "Ball updated!", "total_runs": total_runs, "total_wickets": total_wickets})


@sim_bp.route("/api/match/update-total", methods=["POST"])
@user_or_admin_required
def update_total_score():
    data = request.get_json()
    match_id = data.get("match_id")
    innings = int(data.get("innings"))
    new_runs = int(data.get("total_runs"))
    new_wickets = int(data.get("total_wickets"))

    new_runs = max(0, new_runs)
    new_wickets = max(0, min(10, new_wickets))

    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM matches WHERE id=%s", (match_id,))
    match = cur.fetchone()

    if not match:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Match not found!"})

    cur.execute("SELECT * FROM ball_by_ball WHERE match_id=%s AND innings=%s ORDER BY over_number, ball_number", (match_id, innings))
    balls = cur.fetchall()

    if balls:
        old_total = sum([b["runs"] for b in balls])
        remaining = new_runs

        if old_total > 0:
            for i, b in enumerate(balls):
                if i == len(balls) - 1:
                    new_ball_run = max(0, remaining)
                else:
                    proportion = b["runs"] / old_total
                    new_ball_run = round(new_runs * proportion)
                    new_ball_run = min(new_ball_run, remaining)
                    new_ball_run = max(0, min(6, new_ball_run))
                remaining -= new_ball_run
                cur.execute("UPDATE ball_by_ball SET runs=%s WHERE id=%s", (new_ball_run, b["id"]))
        else:
            remaining = new_runs
            for b in reversed(balls):
                give = min(6, remaining)
                cur.execute("UPDATE ball_by_ball SET runs=%s WHERE id=%s", (give, b["id"]))
                remaining -= give
                if remaining <= 0:
                    break

        cur.execute("UPDATE ball_by_ball SET is_wicket=0 WHERE match_id=%s AND innings=%s", (match_id, innings))

        if new_wickets > 0:
            for b in balls[:new_wickets]:
                cur.execute("UPDATE ball_by_ball SET is_wicket=1 WHERE id=%s", (b["id"],))

    conn.commit()

    if innings == 1:
        cur.execute("UPDATE matches SET team1_score=%s WHERE id=%s", (new_runs, match_id))
        new_score1, new_score2 = new_runs, match["team2_score"]
    else:
        cur.execute("UPDATE matches SET team2_score=%s WHERE id=%s", (new_runs, match_id))
        new_score1, new_score2 = match["team1_score"], new_runs

    if new_score1 is not None and new_score2 is not None:
        old_winner = match["winner_id"]
        new_winner = match["team1_id"] if new_score1 > new_score2 else match["team2_id"]

        if new_winner != old_winner and old_winner is not None:
            old_loser = match["team2_id"] if old_winner == match["team1_id"] else match["team1_id"]
            new_loser = match["team2_id"] if new_winner == match["team1_id"] else match["team1_id"]

            cur.execute("UPDATE teams SET wins=wins-1, points=points-2 WHERE id=%s", (old_winner,))
            cur.execute("UPDATE teams SET losses=losses-1 WHERE id=%s", (old_loser,))
            cur.execute("UPDATE teams SET wins=wins+1, points=points+2 WHERE id=%s", (new_winner,))
            cur.execute("UPDATE teams SET losses=losses+1 WHERE id=%s", (new_loser,))

        cur.execute("UPDATE matches SET winner_id=%s WHERE id=%s", (new_winner, match_id))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True, "message": "Score updated successfully!"})


@sim_bp.route("/api/points/update", methods=["POST"])
@user_or_admin_required
def update_points():
    data = request.get_json()
    team_id = data.get("team_id")
    matches_played = max(0, int(data.get("matches_played")))
    wins = max(0, int(data.get("wins")))
    losses = max(0, int(data.get("losses")))
    points = wins * 2

    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM teams WHERE id=%s", (team_id,))
    team = cur.fetchone()

    if not team:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Team not found!"})

    cur.execute("""
        UPDATE teams SET matches_played=%s, wins=%s, losses=%s, points=%s WHERE id=%s
    """, (matches_played, wins, losses, points, team_id))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True, "message": f"{team['name']} stats updated!", "points": points})


@sim_bp.route("/api/match/simulate/<int:match_id>", methods=["POST"])
@user_or_admin_required
def simulate_single_match(match_id):
    conn = get_db_connection()
    cur = get_cursor(conn)

    cur.execute("SELECT * FROM matches WHERE id=%s", (match_id,))
    match = cur.fetchone()

    if not match:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Match not found!"})

    was_played = match["played"] == 1
    old_winner = match["winner_id"]

    if was_played and match["stage"] == "league" and old_winner:
        old_loser = match["team2_id"] if old_winner == match["team1_id"] else match["team1_id"]
        cur.execute("UPDATE teams SET matches_played=matches_played-1, wins=wins-1, points=points-2 WHERE id=%s", (old_winner,))
        cur.execute("UPDATE teams SET matches_played=matches_played-1, losses=losses-1 WHERE id=%s", (old_loser,))

    score1, score2, winner_id = simulate_match(cur, match["team1_id"], match["team2_id"])
    loser_id = match["team2_id"] if winner_id == match["team1_id"] else match["team1_id"]

    cur.execute("""
        UPDATE matches SET team1_score=%s, team2_score=%s, winner_id=%s, played=1 WHERE id=%s
    """, (score1, score2, winner_id, match_id))

    if match["stage"] == "league":
        cur.execute("UPDATE teams SET matches_played=matches_played+1, wins=wins+1, points=points+2 WHERE id=%s", (winner_id,))
        cur.execute("UPDATE teams SET matches_played=matches_played+1, losses=losses+1 WHERE id=%s", (loser_id,))

    conn.commit()
    generate_ball_by_ball(conn, cur, match_id, match["team1_id"], match["team2_id"], score1, score2)

    if match["stage"] == "semifinal":
        cur.execute("SELECT * FROM matches WHERE stage='final'")
        final = cur.fetchone()

        cur.execute("SELECT * FROM matches WHERE stage='semifinal' AND id != %s AND played=1", (match_id,))
        other_semi = cur.fetchone()

        if final and other_semi:
            cur.execute("""
                UPDATE matches SET team1_id=%s, team2_id=%s, team1_score=NULL,
                team2_score=NULL, winner_id=NULL, played=0 WHERE id=%s
            """, (winner_id, other_semi["winner_id"], final["id"]))
            cur.execute("DELETE FROM ball_by_ball WHERE match_id=%s", (final["id"],))
        elif not final and other_semi:
            cur.execute("INSERT INTO matches (team1_id, team2_id, stage, played) VALUES (%s, %s, 'final', 0)",
                        (winner_id, other_semi["winner_id"]))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Match simulated! Score: {score1} - {score2}",
        "team1_score": score1,
        "team2_score": score2
    })