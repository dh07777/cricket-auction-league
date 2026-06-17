import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "auction.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_cursor(conn):
    return conn.cursor()


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL DEFAULT 'user'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT UNIQUE NOT NULL,
            budget         REAL    NOT NULL DEFAULT 120,
            matches_played INTEGER DEFAULT 0,
            wins           INTEGER DEFAULT 0,
            losses         INTEGER DEFAULT 0,
            points         INTEGER DEFAULT 0,
            nrr            REAL    DEFAULT 0.0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            role       TEXT NOT NULL,
            rating     INTEGER NOT NULL,
            batting    INTEGER NOT NULL,
            bowling    INTEGER NOT NULL,
            fielding   INTEGER NOT NULL,
            base_price REAL NOT NULL DEFAULT 2,
            sold_price REAL DEFAULT 0,
            image      TEXT,
            team_id    INTEGER REFERENCES teams(id),
            is_sold    INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            team1_id    INTEGER NOT NULL REFERENCES teams(id),
            team2_id    INTEGER NOT NULL REFERENCES teams(id),
            team1_score INTEGER,
            team2_score INTEGER,
            winner_id   INTEGER REFERENCES teams(id),
            stage       TEXT    DEFAULT 'league',
            played      INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ball_by_ball (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id    INTEGER NOT NULL REFERENCES matches(id),
            innings     INTEGER NOT NULL,
            over_number INTEGER NOT NULL,
            ball_number INTEGER NOT NULL,
            runs        INTEGER NOT NULL DEFAULT 0,
            is_wicket   INTEGER DEFAULT 0,
            extra       TEXT    DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS auction_room (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            current_player_id   INTEGER REFERENCES players(id),
            current_bid         REAL    DEFAULT 0,
            current_bid_team_id INTEGER REFERENCES teams(id),
            timer_end           REAL    DEFAULT 0,
            status              TEXT    DEFAULT 'waiting'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS auction_seats (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER UNIQUE NOT NULL REFERENCES users(id),
            team_id  INTEGER UNIQUE NOT NULL REFERENCES teams(id),
            username TEXT NOT NULL
        )
    """)

    conn.commit()

    # Default teams
    team_names = [
        "Troopers A", "Troopers B", "Warriors A", "Warriors B",
        "Crusaders A", "Crusaders B", "Sentinels A", "Sentinels B"
    ]
    for name in team_names:
        cur.execute("SELECT id FROM teams WHERE name = ?", (name,))
        if not cur.fetchone():
            cur.execute("INSERT INTO teams (name, budget) VALUES (?, ?)", (name, 120))

    # Default admin
    from werkzeug.security import generate_password_hash
    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

    # Auction room sentinel row
    cur.execute("SELECT id FROM auction_room")
    if not cur.fetchone():
        cur.execute("INSERT INTO auction_room (status) VALUES ('waiting')")

    conn.commit()
    cur.close()
    conn.close()