"""
Phase 1 — Central Configuration Loader

Reads all project settings from a .env file using python-dotenv.
Provides a single Config dataclass that every downstream phase imports.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# ── Resolve paths relative to the project root ──────────────────────────────
# phase1_scaffold/ is one level below the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Load .env once at module import time
load_dotenv(dotenv_path=ENV_PATH)


@dataclass
class Config:
    """
    Centralised configuration for the INDMoney Pulse Generator pipeline.

    All values are read from environment variables (via .env).
    Sensible defaults are provided where applicable.
    """

    # ── OpenRouter (LLM Engine) ──────────────────────────────────────────────
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    openrouter_model: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_MODEL", "liquid/lfm-2.5-1.2b-thinking:free")
    )

    # ── Play Store Scraper ───────────────────────────────────────────────
    app_id: str = field(
        default_factory=lambda: os.getenv("APP_ID", "com.indmoney.indstocks")
    )
    review_count: int = field(
        default_factory=lambda: int(os.getenv("REVIEW_COUNT", "1000"))
    )
    scraper_lang: str = field(
        default_factory=lambda: os.getenv("SCRAPER_LANG", "en")
    )
    scraper_country: str = field(
        default_factory=lambda: os.getenv("SCRAPER_COUNTRY", "in")
    )

    # ── Data Ingestion ───────────────────────────────────────────────────
    weeks_back: int = field(
        default_factory=lambda: int(os.getenv("WEEKS_BACK", "8"))
    )

    # ── Google Docs ──────────────────────────────────────────────────────
    google_doc_id: str = field(
        default_factory=lambda: os.getenv("GOOGLE_DOC_ID", "")
    )
    google_docs_credentials: str = field(
        default_factory=lambda: os.getenv("GOOGLE_DOCS_CREDENTIALS", "")
    )

    # ── Email / SMTP ─────────────────────────────────────────────────────

    email_to: str = field(
        default_factory=lambda: os.getenv("EMAIL_TO", "")
    )
    gmail_user: str = field(
        default_factory=lambda: os.getenv("GMAIL_USER", "")
    )
    gmail_app_password: str = field(
        default_factory=lambda: os.getenv("GMAIL_APP_PASSWORD", "")
    )

    # ── MCP Server ───────────────────────────────────────────────────────
    mcp_command: str = field(
        default_factory=lambda: os.getenv("MCP_COMMAND", "python")
    )
    mcp_args: list[str] = field(
        default_factory=lambda: os.getenv(
            "MCP_ARGS", "phase6_approval/google_docs_mcp.py"
        ).split(",")
    )

    # ── Directories (derived from PROJECT_ROOT) ──────────────────────────
    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)

    @property
    def data_raw_dir(self) -> Path:
        """Directory for scraped review JSON/CSV files."""
        return self.project_root / "data" / "raw"

    @property
    def data_sample_dir(self) -> Path:
        """Directory for sample/test data."""
        return self.project_root / "data" / "sample"

    @property
    def outputs_dir(self) -> Path:
        """Directory for generated pulse notes and logs."""
        return self.project_root / "outputs"

    @property
    def drafts_dir(self) -> Path:
        """Directory for saved .eml email drafts."""
        return self.project_root / "outputs" / "drafts"

    @property
    def notes_log_path(self) -> Path:
        """Path to the append-only notes log JSON file."""
        return self.project_root / "outputs" / "notes_log.json"

    # ── Helpers ───────────────────────────────────────────────────────────

    def ensure_directories(self) -> None:
        """Create all required output directories if they don't exist."""
        for directory in [
            self.data_raw_dir,
            self.data_sample_dir,
            self.outputs_dir,
            self.drafts_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """
        Validate that critical config values are present.

        Returns:
            List of warning messages (empty if all OK).
        """
        warnings = []
        if not self.openrouter_api_key:
            warnings.append("⚠️  OPENROUTER_API_KEY is not set — LLM calls will fail.")
        if not self.email_to:
            warnings.append("⚠️  EMAIL_TO is not set — email drafts will lack a recipient.")
        if not self.google_doc_id:
            warnings.append("⚠️  GOOGLE_DOC_ID is not set — appending to Google Docs will fail.")
        if not self.google_docs_credentials or "REPLACE_WITH" in self.google_docs_credentials:
            warnings.append("⚠️  GOOGLE_DOCS_CREDENTIALS is not set — live Google Docs integration will fail.")
        if not self.gmail_user or not self.gmail_app_password:
            warnings.append("⚠️  GMAIL_USER/GMAIL_APP_PASSWORD not set in .env — email sending will fail.")
        if self.weeks_back < 1 or self.weeks_back > 12:
            warnings.append(
                f"⚠️  WEEKS_BACK={self.weeks_back} is outside the valid range (1–12)."
            )
        return warnings

    def __repr__(self) -> str:
        """Redact secrets when printing config."""
        return (
            f"Config(\n"
            f"  openrouter_api_key={'***' if self.openrouter_api_key else '(not set)'},\n"
            f"  openrouter_model={self.openrouter_model!r},\n"
            f"  app_id={self.app_id!r},\n"
            f"  review_count={self.review_count},\n"
            f"  weeks_back={self.weeks_back},\n"
            f"  google_doc_id={self.google_doc_id!r},\n"
            f"  google_docs_credentials={'***' if self.google_docs_credentials else '(not set)'},\n"
            f"  email_to={self.email_to or '(not set)'},\n"
            f"  gmail_user={self.gmail_user or '(not set)'},\n"
            f"  gmail_app_password={'***' if self.gmail_app_password else '(not set)'},\n"
            f"  project_root={self.project_root}\n"
            f")"
        )


# ── Module-level convenience ─────────────────────────────────────────────────

def load_config() -> Config:
    """
    Create a Config instance, ensure directories exist, and print warnings.

    Returns:
        Fully initialised Config object.
    """
    cfg = Config()
    cfg.ensure_directories()

    warnings = cfg.validate()
    for w in warnings:
        print(w)

    return cfg


# Allow running standalone to verify config loading
if __name__ == "__main__":
    config = load_config()
    print("\n✅ Configuration loaded successfully:\n")
    print(config)
