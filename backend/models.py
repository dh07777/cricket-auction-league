import psycopg2
import psycopg2.extras
import os

# Get database URL from environment variable (set on Render)
DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_db_connection():
    """Create and return a PostgreSQL database connection."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


def get_cursor(conn):
    """Return a dictionary cursor (access columns by name)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    """Create all required tables if they don't exist."""
    conn = get_db_connection()
    cur = get_cursor(conn)

    # ---------- USERS TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)

    # ---------- TEAMS TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            budget REAL NOT NULL DEFAULT 120,
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
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            rating INTEGER NOT NULL,
            batting INTEGER NOT NULL,
            bowling INTEGER NOT NULL,
            fielding INTEGER NOT NULL,
            base_price REAL NOT NULL DEFAULT 2,
            sold_price REAL DEFAULT 0,
            image TEXT,
            team_id INTEGER,
            is_sold INTEGER DEFAULT 0,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    """)

    # ---------- MATCHES TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            team1_id INTEGER NOT NULL,
            team2_id INTEGER NOT NULL,
            team1_score INTEGER,
            team2_score INTEGER,
            winner_id INTEGER,
            stage TEXT DEFAULT 'league',
            played INTEGER DEFAULT 0,
            FOREIGN KEY (team1_id) REFERENCES teams(id),
            FOREIGN KEY (team2_id) REFERENCES teams(id),
            FOREIGN KEY (winner_id) REFERENCES teams(id)
        )
    """)

    # ---------- BALL BY BALL TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ball_by_ball (
            id SERIAL PRIMARY KEY,
            match_id INTEGER NOT NULL,
            innings INTEGER NOT NULL,
            over_number INTEGER NOT NULL,
            ball_number INTEGER NOT NULL,
            runs INTEGER NOT NULL DEFAULT 0,
            is_wicket INTEGER DEFAULT 0,
            extra TEXT DEFAULT '',
            FOREIGN KEY (match_id) REFERENCES matches(id)
        )
    """)

    # ---------- AUCTION ROOM TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auction_room (
            id SERIAL PRIMARY KEY,
            current_player_id INTEGER,
            current_bid REAL DEFAULT 0,
            current_bid_team_id INTEGER,
            timer_end REAL DEFAULT 0,
            status TEXT DEFAULT 'waiting',
            FOREIGN KEY (current_player_id) REFERENCES players(id),
            FOREIGN KEY (current_bid_team_id) REFERENCES teams(id)
        )
    """)

    # ---------- AUCTION SEATS TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auction_seats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            team_id INTEGER UNIQUE NOT NULL,
            username TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    """)

    conn.commit()

    # ---------- INSERT DEFAULT TEAMS ----------
    team_names = [
        "Troopers A", "Troopers B", "Warriors A", "Warriors B",
        "Crusaders A", "Crusaders B", "Sentinels A", "Sentinels B"
    ]
    for name in team_names:
        cur.execute("SELECT id FROM teams WHERE name = %s", (name,))
        if not cur.fetchone():
            cur.execute("INSERT INTO teams (name, budget) VALUES (%s, %s)", (name, 120))

    # ---------- INSERT DEFAULT ADMIN ----------
    from werkzeug.security import generate_password_hash
    cur.execute("SELECT id FROM users WHERE username = %s", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

    # ---------- ENSURE ONE AUCTION ROOM ROW ----------
    cur.execute("SELECT id FROM auction_room")
    if not cur.fetchone():
        cur.execute("INSERT INTO auction_room (status) VALUES ('waiting')")

    conn.commit()
    cur.close()
    conn.close()