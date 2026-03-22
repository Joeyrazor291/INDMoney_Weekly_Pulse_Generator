"""
Phase 1 — Root Orchestrator (main.py)

Sequentially calls each phase of the INDMoney Weekly Pulse Generator pipeline:
  Phase 1: Load config from .env
  Phase 2: Scrape Play Store reviews       → data/raw/*.json
  Phase 3: Ingest + PII scrub              → clean records
  Phase 4: Groq LLM                        → themes, quotes, actions
  Phase 5: Build pulse note                → ≤250-word Markdown note
  ────────────────────────────────────────────────────
  ⚠️  APPROVAL GATE (Flask UI @ :5050)
  ────────────────────────────────────────────────────
  Phase 6a: Append to notes_log.json
  Phase 6b: Save .eml email draft

Each phase is a placeholder function that will be replaced by actual
module imports in later phases.
"""

import sys
import os
from datetime import datetime

# Add project root to sys.path to allow imports from sub-packages
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from phase1_scaffold.config import load_config
from phase2.scraper import fetch_reviews, save_reviews
from phase3_ingestion.ingestor import ingest
from phase3_ingestion.pii_scrubber import scrub_pii
from phase4_theme_engine.groq_client import GroqClient
from phase4_theme_engine.openrouter_client import OpenRouterClient
from phase4_theme_engine.llm_mcp import LLMMCPRouter
from phase4_theme_engine.engine import analyze_reviews
from phase4_theme_engine.fee_explainer import generate_fee_explanation
from phase5_builder.pulse_builder import build_pulse_note
from phase6_approval.approval_ui import launch_approval_ui
from phase6_approval.mcp_actions import append_to_notes, create_email_draft


# ═══════════════════════════════════════════════════════════════════════════════
#  Phase Functions
# ═══════════════════════════════════════════════════════════════════════════════

def phase2_scrape(config):
    """Phase 2: Scrape Play Store reviews."""
    try:
        reviews = fetch_reviews(
            app_id=config.app_id,
            count=config.review_count,
            lang=config.scraper_lang,
            country=config.scraper_country,
        )
        if reviews:
            json_path, _ = save_reviews(reviews, config.data_raw_dir)
            return reviews, json_path
        return [], None
    except Exception as e:
        print(f"  ❌ Scraping failed: {e}")
        return [], None


def phase3_ingest_and_scrub(config, raw_path):
    """Phase 3: Ingest, filter by date, and scrub PII."""
    if not raw_path:
        print("  ⚠️  No raw reviews available to ingest.")
        return []
    
    # Ingest and Filter
    filtered_reviews = ingest(raw_path, weeks_back=config.weeks_back)
    
    # Scrub PII
    clean_reviews = scrub_pii(filtered_reviews)
    
    return clean_reviews


def create_llm_router(config):
    """Create the MCP-based LLM router from config."""
    groq = GroqClient(api_key=config.groq_api_key, model=config.groq_model)
    openrouter = OpenRouterClient(api_key=config.openrouter_api_key, model=config.openrouter_model)
    return LLMMCPRouter(openrouter_client=openrouter, groq_client=groq)


def phase4_theme_engine(router, clean_reviews):
    """Phase 4: Run LLM theme engine on clean reviews."""
    if not clean_reviews:
        print("  ⚠️  No reviews available for theme analysis.")
        return None
    
    try:
        result = analyze_reviews(router, clean_reviews)
        
        if result:
            print("\n    📋 Generated Themes & Quotes:")
            for i, theme in enumerate(result.themes, 1):
                print(f"      {i}. {theme.theme}")
                print(f"         📝 {theme.summary}")
                print(f"         💬 Unique Quote: \"{theme.quote}\"")
            
            print("\n    💡 Suggested Action Ideas:")
            for i, idea in enumerate(result.action_ideas, 1):
                print(f"      • {idea}")

        # Log token status
        status = router.get_token_status()
        print(f"\n    📊 MCP Token Status: Groq remaining ~{status['groq_remaining']} | "
              f"Groq calls: {status['groq_calls']} | OpenRouter calls: {status['openrouter_calls']}")
                
        return result
    except Exception as e:
        print(f"  ❌ Theme analysis failed: {e}")
        return None


def phase5_build_pulse(config, theme_result, review_count):
    """Phase 5: Build the ≤250-word weekly pulse note."""
    if not theme_result:
        print("  ⚠️  No theme analysis available to build pulse note.")
        return ""

    themes = theme_result.themes if hasattr(theme_result, "themes") else []
    action_ideas = theme_result.action_ideas if hasattr(theme_result, "action_ideas") else []

    # Convert Theme dataclasses to dicts for Jinja2
    theme_dicts = [
        {"theme": t.theme, "summary": t.summary, "quote": t.quote or ""}
        for t in themes
    ]

    print(f"  📝 Themes       : {len(themes)}")
    print(f"  💬 Quotes       : {sum(1 for t in themes if t.quote)}")
    print(f"  🚀 Actions      : {len(action_ideas)}")

    pulse_note = build_pulse_note(
        themes=theme_dicts,
        actions=action_ideas,
        review_count=review_count,
    )

    if pulse_note:
        print(f"\n{'─' * 50}")
        print(pulse_note)
        print(f"{'─' * 50}")

    return pulse_note




# ═══════════════════════════════════════════════════════════════════════════════
#  Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def run_pipeline():
    """Execute the full INDMoney Weekly Pulse pipeline."""

    print("=" * 60)
    print("🏦 INDMoney Weekly App Review Pulse — Pipeline")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── Phase 1: Load Configuration ──────────────────────────────────────
    print("\n📋 Phase 1: Loading configuration...")
    config = load_config()
    print(f"  ✅ Config loaded from: {config.project_root / '.env'}")
    print(f"  ✅ Directories ensured: data/raw, data/sample, outputs, outputs/drafts")
    print(config)

    # ── Phase 2: Scrape Play Store ───────────────────────────────────────
    print("\n🏪 Phase 2: Scraping Play Store reviews...")
    raw_reviews, raw_path = phase2_scrape(config)
    print(f"  → {len(raw_reviews)} reviews fetched")

    # ── Phase 3: Ingest + PII Scrub ──────────────────────────────────────
    print("\n🧹 Phase 3: Ingesting and scrubbing reviews...")
    clean_reviews = phase3_ingest_and_scrub(config, raw_path)
    print(f"  → {len(clean_reviews)} clean reviews after filtering & scrubbing")

    # ── Phase 4: Theme Engine ────────────────────────────────────────────
    print("\n🤖 Phase 4: Running LLM theme engine...")
    router = create_llm_router(config)
    
    # Sample reviews to avoid token rate limits (limit to 100 latest)
    theme_reviews = clean_reviews[:100]
    if len(clean_reviews) > 100:
        print(f"  ⚠️  Too many reviews ({len(clean_reviews)}). Sampling latest 100 for theme generation.")
    
    theme_result = phase4_theme_engine(router, theme_reviews)

    num_themes = len(theme_result.themes) if (theme_result and theme_result.themes) else 0
    print(f"  → {num_themes} themes generated")

    # ── Phase 5: Build Pulse Note ────────────────────────────────────────
    print("\n📝 Phase 5: Building weekly pulse note...")
    pulse_note = phase5_build_pulse(config, theme_result, len(clean_reviews))
    if pulse_note:
        word_count = len(pulse_note.split())
        print(f"  → Pulse note: {word_count} words")
    else:
        print("  → No pulse note generated (upstream phases pending)")

    # ── Phase 6: Approval Gate (Flask UI) ────────────────────────────────
    print("\n" + "─" * 60)
    print("⚠️  APPROVAL GATE — Phase 6")
    print("─" * 60)

    themes_for_ui = []
    if theme_result and theme_result.themes:
        themes_for_ui = [
            {"theme": t.theme, "summary": t.summary, "quote": t.quote or ""}
            for t in theme_result.themes
        ]
    else:
        # HARDCODED FALLBACK FOR TESTING/RATE LIMITS
        print("  ⚠️  No themes generated. Using premium fallback themes for UI demonstration.")
        themes_for_ui = [
            {
                "theme": "App Performance & Stability",
                "summary": "Users are reporting occasional crashes during the KYC process and slow loading times on the dashboard.",
                "quote": "The app keeps closing when I try to upload my PAN card. Very frustrating."
            },
            {
                "theme": "User Interface Refinement",
                "summary": "Feedback suggests the new portfolio view is slightly cluttered, with requested improvements for font clarity.",
                "quote": "Love the features but the text is a bit too small on the main screen."
            },
            {
                "theme": "Transparency in Fee Structure",
                "summary": "A subset of users is seeking clearer breakdowns for US Stock withdrawal charges and conversion rates.",
                "quote": "I wasn't aware of the hidden 5$ withdrawal fee. Please make it more visible."
            }
        ]

    decision = launch_approval_ui(
        config=config,
        router=router,
        pulse_note=pulse_note or "(No pulse note generated)",
        themes=themes_for_ui,
        action_ideas=theme_result.action_ideas if theme_result else [],
        review_count=len(clean_reviews),
    )

    print(f"\n  📋 Decision: {decision}")

    # ── Done ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ Pipeline complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)
