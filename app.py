from flask import Flask
from vim_database.database import db
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / "..env", override=True)

app=None

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(16)
    app.debug = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vim_database.sqlite"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        import vim_database.models  # noqa: F401 — register all ORM tables
        from vim.vim_controller import register_routes
        register_routes(app)
        try:
            db.create_all()
        except Exception as e:
            print("create_all() FAILED:", e)

        from vim.extraction import config as extraction_config
        llama, groq = extraction_config.load_keys_into_app(app)
        if llama and groq:
            print("API keys loaded from", extraction_config.ENV_PATH)
        else:
            print("WARNING: API keys missing. Check", extraction_config.ENV_PATH)

    return app

app = create_app()

if __name__ == "__main__":
    # Disable reloader (watchdog restarts on site-packages changes).
    # Use port 5001 to avoid stale zombie processes stuck on 5000.
    app.run(debug=True, use_reloader=False, threaded=True, host="127.0.0.1", port=5002)