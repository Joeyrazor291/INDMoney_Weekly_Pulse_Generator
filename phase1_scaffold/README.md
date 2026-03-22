# 🏦 INDMoney Weekly App Review Pulse Generator

> Automated pipeline that turns recent Google Play Store reviews into a scannable weekly pulse note with themes, user quotes, and action ideas.

---

## 🎯 What This Does

1. **Scrapes** the latest 8–12 weeks of INDMoney reviews from Google Play Store
2. **Cleans** data and removes all PII (emails, phones, usernames)
3. **Analyses** reviews using Groq LLM to identify 3–5 themes
4. **Generates** a ≤250-word weekly pulse note with:
   - Top 3 themes with summaries
   - 3 representative user quotes
   - 3 actionable product improvement ideas
5. **Delivers** via approval-gated email draft (no auto-send)

---

## 👥 Who This Helps

| Team | Benefit |
|---|---|
| **Product / Growth** | Understand what to fix or build next |
| **Support** | Know what users are reporting |
| **Leadership** | Quick weekly health pulse |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd "INDMoney_Pulse_Generator"
python -m venv venv
source venv/bin/activate          # macOS/Linux
pip install -r phase1_scaffold/requirements.txt
```

### 2. Configure Environment

```bash
cp phase1_scaffold/.env.example .env
# Edit .env with your actual values (GROQ_API_KEY, email settings, etc.)
```

### 3. Run the Pipeline

```bash
python phase1_scaffold/main.py
```

---

## 📁 Project Structure

```
INDMoney_Pulse_Generator/
├── data/
│   ├── raw/                    # Scraped reviews (auto-generated)
│   └── sample/                 # Sample data for offline testing
├── outputs/
│   ├── drafts/                 # Saved .eml email drafts
│   └── notes_log.json          # Append-only notes log
├── phase1_scaffold/            # ← You are here
│   ├── config.py               # Central config loader
│   ├── main.py                 # Pipeline orchestrator
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment template
│   └── README.md               # This file
├── phase2/                     # Play Store scraper
├── phase3_ingestion/           # Data ingestor + PII scrubber
├── phase4_theme_engine/        # Groq LLM theme engine
├── phase5_builder/             # Pulse note builder (Jinja2)
├── phase6_approval/            # Flask approval UI + MCP actions
├── tests/                      # Unit & integration tests
├── .env                        # Secrets (git-ignored)
└── architecture.md             # Full architecture document
```

---

## ⚙️ Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq Cloud API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model name |
| `APP_ID` | `com.indmoney.indstocks` | Google Play app ID |
| `REVIEW_COUNT` | `1000` | Max reviews to fetch per run |
| `WEEKS_BACK` | `8` | Date window: last N weeks |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | *(required)* | Sender email |
| `SMTP_PASS` | *(required)* | App password |
| `EMAIL_TO` | *(required)* | Recipient email |

---

## 🔒 Privacy & Constraints

- ✅ **No PII** — emails, phones, usernames are auto-redacted
- ✅ **Public data only** — no login or proprietary API required
- ✅ **No auto-send** — email drafts saved as `.eml` files
- ✅ **Approval gate** — human review before any delivery action
- ✅ **≤250 words** — pulse notes are concise and scannable
- ✅ **Max 5 themes** — focused and actionable

---

## 🏗️ Pipeline Phases

| Phase | Module | Status |
|---|---|---|
| 1. Scaffold & Config | `phase1_scaffold/` | ✅ Complete |
| 2. Play Store Scraper | `phase2/` | ⏳ Pending |
| 3. Data Ingestion + PII | `phase3_ingestion/` | ⏳ Pending |
| 4. LLM Theme Engine | `phase4_theme_engine/` | ⏳ Pending |
| 5. Pulse Note Builder | `phase5_builder/` | ⏳ Pending |
| 6. Approval + MCP Actions | `phase6_approval/` | ⏳ Pending |
| 7. Verification & Tests | `tests/` | ⏳ Pending |

---

*Built with ❤️ for INDMoney product teams*
