import sqlite3
import os

# Path to database file (in backend folder)
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows access by column name
    return conn


def init_db():
    """Create all required tables if they don't exist."""
    conn = get_db_connection()
    cur = conn.cursor()

    # ---------- USERS TABLE (Admin + Normal Users) ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'   -- 'admin' or 'user'
        )
    """)

    # ---------- TEAMS TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            budget REAL NOT NULL DEFAULT 120,   -- in Crore
            matches_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            nrr REAL DEFAULT 0.0
        )
    """)

    # ---------- PLAYERS TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,         -- Batsman, Bowler, All-rounder, Wicketkeeper
            rating INTEGER NOT NULL,    -- 1-100
            batting INTEGER NOT NULL,
            bowling INTEGER NOT NULL,
            fielding INTEGER NOT NULL,
            base_price REAL NOT NULL DEFAULT 2,
            sold_price REAL DEFAULT 0,
            image TEXT,
            team_id INTEGER,            -- NULL if unsold
            is_sold INTEGER DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    """)

    # ---------- MATCHES TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team1_id INTEGER NOT NULL,
            team2_id INTEGER NOT NULL,
            team1_score INTEGER,
            team2_score INTEGER,
            winner_id INTEGER,
            stage TEXT DEFAULT 'league',   -- league, semifinal, final
            played INTEGER DEFAULT 0,
            FOREIGN KEY (team1_id) REFERENCES teams(id),
            FOREIGN KEY (team2_id) REFERENCES teams(id),
            FOREIGN KEY (winner_id) REFERENCES teams(id)
        )
    """)

    conn.commit()

    # ---------- BALL BY BALL TABLE (20 overs x 6 balls scorecard) ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ball_by_ball (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            innings INTEGER NOT NULL,        -- 1 or 2
            over_number INTEGER NOT NULL,    -- 1 to 20
            ball_number INTEGER NOT NULL,    -- 1 to 6
            runs INTEGER NOT NULL DEFAULT 0, -- runs scored on this ball (0-6)
            is_wicket INTEGER DEFAULT 0,     -- 1 if wicket fell on this ball
            extra TEXT DEFAULT '',           -- 'wide', 'no ball', 'bye', or ''
            FOREIGN KEY (match_id) REFERENCES matches(id)
        )
    """)

    # ---------- AUCTION ROOM TABLE (Live multiplayer auction state) ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auction_room (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            current_player_id INTEGER,
            current_bid REAL DEFAULT 0,
            current_bid_team_id INTEGER,
            timer_end REAL DEFAULT 0,       -- unix timestamp when timer expires
            status TEXT DEFAULT 'waiting',  -- waiting, live, sold, unsold, finished
            FOREIGN KEY (current_player_id) REFERENCES players(id),
            FOREIGN KEY (current_bid_team_id) REFERENCES teams(id)
        )
    """)

    # ---------- AUCTION SEATS TABLE (First 8 users claim teams) ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auction_seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            team_id INTEGER UNIQUE NOT NULL,
            username TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    """)

    # ---------- INSERT DEFAULT TEAMS ----------
    team_names = [
        "Troopers A", "Troopers B", "Warriors A", "Warriors B",
        "Crusaders A", "Crusaders B", "Sentinels A", "Sentinels B"
    ]
    for name in team_names:
        cur.execute("SELECT id FROM teams WHERE name = ?", (name,))
        if not cur.fetchone():
            cur.execute("INSERT INTO teams (name, budget) VALUES (?, ?)", (name, 120))

    # ---------- INSERT DEFAULT ADMIN ----------
    from werkzeug.security import generate_password_hash
    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

        # Ensure one auction_room row exists
    cur.execute("SELECT id FROM auction_room")
    if not cur.fetchone():
        cur.execute("INSERT INTO auction_room (status) VALUES ('waiting')")

    conn.commit()
    conn.close()