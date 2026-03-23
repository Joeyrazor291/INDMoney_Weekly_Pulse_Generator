"""
Phase 6 — Flask Approval UI

Renders the pulse note preview, provides a fee-explainer input box,
and offers three approval actions: Send to Notes, Create Email Draft, Skip.

The Flask server runs on localhost:5050 and blocks the pipeline until
the user makes a decision.
"""

import sys
import os
import threading
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from flask import Flask, render_template, request, redirect, url_for, jsonify

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phase4_theme_engine.fee_explainer import generate_fee_explanation
from phase6_approval.mcp_actions import append_to_notes, create_email_draft
from phase8_analytics.history_manager import get_analytics_history
import traceback

# For production debugging
LAST_EXCEPTION = None

logger = logging.getLogger(__name__)

# ── Flask App ────────────────────────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

# ── Error Handler ────────────────────────────────────────────────────────────

@app.errorhandler(Exception)
def handle_exception(e):
    """Log the error and return a friendly-ish error page with traceback."""
    logger.error(f"Unhandled Exception: {e}")
    tb = traceback.format_exc()
    return f"<h1>500 Internal Server Error</h1><pre>{tb}</pre>", 500

# Initialization of app state
app.config["PULSE_STATE"] = {
    "pulse_note": "",
    "themes": [],
    "review_count": 0,
    "config": None,
    "router": None,         # LLMMCPRouter for fee explainer
    "fee_explanation": None,
    "decision": None,       # Set by approval actions
    "actions_taken": [],    # Track all actions performed
    "action_ideas": [],     # Global action ideas
}

_shutdown_event = threading.Event()


def _get_theme_metadata(theme_name: str) -> dict:
    """Map theme names to UI metadata (icons, colors)."""
    if not theme_name:
        theme_name = ""
    name_low = theme_name.lower()
    
    # Defaults
    meta = {
        "icon": "layers",  # Default icon
        "color": "#6366f1", # Indigo
        "bg_light": "rgba(99, 102, 241, 0.1)"
    }
    
    if any(word in name_low for word in ["perform", "speed", "slow", "crash", "bug", "error"]):
        meta["icon"] = "warning"
        meta["color"] = "#ef4444" # Red
        meta["bg_light"] = "rgba(239, 68, 68, 0.1)"
    elif any(word in name_low for word in ["feature", "missing", "request", "add", "option"]):
        meta["icon"] = "features"
        meta["color"] = "#f59e0b" # Yellow/Orange
        meta["bg_light"] = "rgba(245, 158, 11, 0.1)"
    elif any(word in name_low for word in ["fee", "charge", "cost", "price", "brokerage", "transparent"]):
        meta["icon"] = "currency-circle-dollar"
        meta["color"] = "#10b981" # Teal/Green
        meta["bg_light"] = "rgba(16, 185, 129, 0.1)"
    elif any(word in name_low for word in ["ui", "layout", "ux", "design", "interface"]):
        meta["icon"] = "paint-brush"
        meta["color"] = "#3b82f6" # Blue
        meta["bg_light"] = "rgba(59, 130, 246, 0.1)"
        
    return meta


def _render_approval_page(success_message: str = None, done: bool = False):
    """Unified rendering helper to ensure data consistency."""
    state = app.config["PULSE_STATE"]
    # Enhance themes with UI metadata
    enhanced_themes = []
    for theme in state["themes"]:
        # Handle both dataclass objects and dictionaries
        if hasattr(theme, "__dict__"):
            t_dict = asdict(theme)
        else:
            t_dict = dict(theme)

        theme_data = {
            "theme_name": t_dict.get("theme", ""),
            "summary": t_dict.get("summary", ""),
            "best_quote": t_dict.get("quote", "") or "",
            "meta": _get_theme_metadata(t_dict.get("theme", ""))
        }
        enhanced_themes.append(theme_data)

    return render_template(
        "approval.html",
        pulse_note=state["pulse_note"],
        pulse_themes=list(enhanced_themes),
        action_ideas=state["action_ideas"],
        review_count=state["review_count"],
        fee_explanation=state["fee_explanation"],
        success_message=success_message or "\n".join(state["actions_taken"]),
        done=done,
        now=datetime.now().strftime("%Y-%m-%d %H:%M")
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@app.before_request
def _ensure_state_initialized():
    """Ensure the latest pulse and config are loaded (crucial for HF Spaces)."""
    state = app.config["PULSE_STATE"]
    
    # ALWAYS check for fresh data from outputs/latest_pulse.json (Git-Sync architecture)
    json_path = PROJECT_ROOT / "outputs" / "latest_pulse.json"
    if json_path.exists():
        try:
            import json
            with open(json_path, "r") as f:
                data = json.load(f)
            state["pulse_note"] = data.get("pulse_note", "")
            state["themes"] = data.get("themes", [])
            state["action_ideas"] = data.get("action_ideas", [])
            state["review_count"] = data.get("review_count", 0)
        except Exception as e:
            logger.error(f"Failed to load latest_pulse.json: {e}")

    # Re-initialize config/router for production if missing
    if state["router"] is None:
        try:
            from phase1_scaffold.config import load_config
            from phase1_scaffold.main import create_llm_router
            
            # Note: load_config() calls load_dotenv() from the current env
            state["config"] = load_config()
            state["router"] = create_llm_router(state["config"])
            
            # Log for debugging (redacted)
            if state["config"].openrouter_api_key:
                logger.info("✅ Router successfully initialized in before_request.")
            else:
                logger.warning("⚠️  Config loaded but OPENROUTER_API_KEY is missing.")
        except Exception as e:
            logger.error(f"Failed to auto-initialize Config/Router: {e}")

@app.route("/")
def index():
    """Render pulse note preview + fee explainer input."""
    return _render_approval_page()


@app.route("/analytics")
def analytics():
    """Render the longitudinal analytics dashboard using Chart.js"""
    history_data = get_analytics_history()
    return render_template(
        "analytics.html",
        history_data=history_data,
        now=datetime.now().strftime("%Y-%m-%d %H:%M")
    )


@app.route("/generate_fee", methods=["POST"])
def generate_fee():
    """Generate a fee explanation for a user-provided scenario."""
    state = app.config["PULSE_STATE"]
    scenario = request.form.get("scenario", "").strip()
    if not scenario:
        return redirect(url_for("index"))

    config = state["config"]
    router = state["router"]
    
    if router is None:
        logger.error("Fee explanation failed: LLM router is not initialized.")
        state["fee_explanation"] = {
            "scenario": scenario,
            "bullets": [
                "Error: AI generation is currently disabled.",
                "Missing API Keys: Hugging Face Spaces does not have access to your local .env file. Please copy your OPENROUTER_API_KEY from your .env and add it to the 'Settings > Variables and secrets' section of your Hugging Face Space."
            ],
            "source_links": [],
            "last_checked": "",
        }
        return redirect(url_for("index"))

    try:
        explanation = generate_fee_explanation(router, scenario)
        state["fee_explanation"] = explanation
    except Exception as e:
        global LAST_EXCEPTION
        LAST_EXCEPTION = traceback.format_exc()
        logger.error(f"Fee explanation failed: {e}")
        state["fee_explanation"] = {
            "scenario": scenario,
            "bullets": [f"Error generating explanation: {e}"],
            "source_links": [],
            "last_checked": "",
        }

    return redirect(url_for("index"))


@app.route("/debug/config")
def debug_config():
    """Return non-sensitive config for debugging production mismatches."""
    from .mcp_actions import LAST_MCP_ERROR
    state = app.config.get("PULSE_STATE")
    if state is None:
        return jsonify({"status": "uninitialized", "error": "PULSE_STATE not found in app config"}), 200
        
    config = state.get("config")
    if not config:
        return jsonify({"status": "no_config", "error": "Config object not in state"}), 200
        
    fee_expl = state.get("fee_explanation") or {}
    fee_bullets = fee_expl.get("bullets", [])
    fee_err = fee_bullets[0] if (fee_bullets and isinstance(fee_bullets[0], str) and "Error" in fee_bullets[0]) else None
    
    # Secret Health Checks
    def check_creds(val):
        if not val: return "❌ MISSING"
        if val.strip().startswith("{"): return "✅ VALID JSON"
        if "/" in val or "." in val: return f"⚠️ PATH? ({val[:15]}...)"
        if len(val) > 20 and val.isalnum(): return "❌ ERROR (Looks like a Doc ID or Key, not JSON)"
        return f"❓ UNKNOWN ({val[:10]}...)"

    return jsonify({
        "google_doc_id": config.google_doc_id,
        "mcp_command": config.mcp_command,
        "mcp_args": config.mcp_args,
        "gmail_user": config.gmail_user,
        "health_checks": {
            "OPENROUTER_API_KEY": "✅ SET" if config.openrouter_api_key else "❌ MISSING",
            "GOOGLE_DOCS_CREDENTIALS": check_creds(config.google_docs_credentials),
            "GMAIL_REFRESH_TOKEN": "✅ SET" if os.getenv("GMAIL_REFRESH_TOKEN") else "❌ MISSING"
        },
        "last_mcp_error": LAST_MCP_ERROR,
        "last_app_exception": LAST_EXCEPTION,
        "fee_explanation_error": fee_err,
        "status": "active"
    })

@app.route("/approve/notes", methods=["POST"])
def approve_notes():
    """Append pulse + fee data to live Google Doc."""
    state = app.config["PULSE_STATE"]
    config = state["config"]
    
    # Update state with potentially edited content from the form
    if "pulse_note" in request.form:
        state["pulse_note"] = request.form.get("pulse_note")

    path = append_to_notes(
        google_doc_id=config.google_doc_id,
        pulse_note=state["pulse_note"],
        themes=state["themes"],
        review_count=state["review_count"],
        mcp_command=config.mcp_command,
        mcp_args=config.mcp_args,
        fee_explanation=state["fee_explanation"],
    )
    state["actions_taken"].append(f"✅ Appended to notes: {path}")
    return _render_approval_page()


@app.route("/approve/email", methods=["POST"])
def approve_email():
    """Create email draft in Gmail."""
    state = app.config["PULSE_STATE"]
    config = state["config"]

    # Update state with potentially edited content from the form
    if "pulse_note" in request.form:
        state["pulse_note"] = request.form.get("pulse_note")

    draft_id = create_email_draft(
        pulse_note=state["pulse_note"],
        email_to=config.email_to,
        gmail_user=config.gmail_user,
        gmail_app_password=config.gmail_app_password,
        gmail_client_id=config.gmail_client_id,
        gmail_client_secret=config.gmail_client_secret,
        gmail_refresh_token=config.gmail_refresh_token,
        fee_explanation=state["fee_explanation"],
    )
    state["actions_taken"].append(f"✅ Gmail draft created: {draft_id}")
    return _render_approval_page()


@app.route("/approve/both", methods=["POST"])
def approve_both():
    """Append to notes AND create Gmail draft."""
    state = app.config["PULSE_STATE"]
    config = state["config"]

    # Update state with potentially edited content from the form
    if "pulse_note" in request.form:
        state["pulse_note"] = request.form.get("pulse_note")

    notes_path = append_to_notes(
        google_doc_id=config.google_doc_id,
        pulse_note=state["pulse_note"],
        themes=state["themes"],
        review_count=state["review_count"],
        mcp_command=config.mcp_command,
        mcp_args=config.mcp_args,
        fee_explanation=state["fee_explanation"],
    )
    draft_id = create_email_draft(
        pulse_note=state["pulse_note"],
        email_to=config.email_to,
        gmail_user=config.gmail_user,
        gmail_app_password=config.gmail_app_password,
        gmail_client_id=config.gmail_client_id,
        gmail_client_secret=config.gmail_client_secret,
        gmail_refresh_token=config.gmail_refresh_token,
        fee_explanation=state["fee_explanation"],
    )
    state["actions_taken"].append(f"✅ Notes: {notes_path}")
    state["actions_taken"].append(f"✅ Gmail draft: {draft_id}")
    return _render_approval_page()


@app.route("/approve/skip", methods=["POST"])
def approve_skip():
    """Done — end the pipeline."""
    state = app.config["PULSE_STATE"]
    state["decision"] = "done"
    _shutdown_event.set()
    return _render_approval_page(
        success_message="\n".join(state["actions_taken"]) + "\n✅ Pipeline complete — you can close this tab.",
        done=True
    )


# ── Public API ───────────────────────────────────────────────────────────────

def launch_approval_ui(config, router, pulse_note: str, themes: list,
                       action_ideas: list, review_count: int, port: int = 5050) -> str:
    """Launch the Flask approval UI and block until user makes a decision."""
    state = app.config["PULSE_STATE"]
    state["pulse_note"] = pulse_note
    state["themes"] = themes
    state["action_ideas"] = action_ideas
    state["review_count"] = review_count
    state["config"] = config
    state["router"] = router
    state["fee_explanation"] = None
    state["decision"] = None
    state["actions_taken"] = []
    _shutdown_event.clear()

    print(f"    DEBUG: launch_approval_ui called. themes set to {len(themes)} items.")

    # Suppress Flask's default logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    print(f"  🌐 Approval UI → http://localhost:{port}")
    print("  👉 Open this URL in your browser to review and approve.\n")

    server_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()

    # Block until a decision is made
    _shutdown_event.wait()

    return state["decision"] or "skip"
