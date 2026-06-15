from flask import Flask, redirect, url_for, session
import os
from models import init_db

# Import blueprints
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.team_routes import team_bp
from routes.auction_routes import auction_bp
from routes.simulation_routes import sim_bp
from routes.live_auction_routes import live_bp

# Configure Flask with frontend templates & static folders
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "static")
)

app.secret_key = os.environ.get("SECRET_KEY", "cricket_auction_secret_key_2026")

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(team_bp)
app.register_blueprint(auction_bp)
app.register_blueprint(sim_bp)
app.register_blueprint(live_bp)


# ---------------- HOME ROUTE ----------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("auth.login"))


# ---------------- INITIALIZE DATABASE ON STARTUP ----------------
with app.app_context():
    init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)