---
title: INDMoney Pulse UI
emoji: 🏦
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# 🏦 INDMoney Weekly App Review Pulse

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-blueviolet)
![Flask](https://img.shields.io/badge/UI-Flask-lightgrey)

An automated AI pipeline that scrapes Google Play Store reviews, scrubs PII, and uses OpenRouter's HTTP APIs (with dynamic fallbacks) to analyze user sentiment. It generates a concise, actionable weekly pulse note for Product Managers to track recurring themes, user quotes, and concrete improvement ideas.

## 🌟 Why This Exists?

Product, support, and leadership teams need a recurring view of what users are saying about the app. Manually reading hundreds of Play Store reviews every week is unsustainable and error-prone. This pipeline acts as an AI PM Assistant to:
- Quickly identify the highest-impact issues (bugs, UX friction).
- Surface representative user quotes without exposing Personally Identifiable Information (PII).
- Suggest 3 - 5 concrete action items for the engineering and design teams based *strictly* on real user feedback.

## 🚀 Key Features

- **Automated Scraping**: Fetches up to 1000 of the latest Play Store reviews.
- **Zero PII Leakage**: Aggressive Regex scrubbing strips emails, phone numbers (Indian & Intl), and sensitive URLs before data ever touches an LLM.
- **Smart Theme Engine**: Routes LLM requests dynamically by using **OpenRouter** as the primary inference engine, with an automatic fallback mechanism to alternative free-tier models if any rate limits or errors occur. This ensures zero downtime when extracting the top 3-5 distinct themes.
- **Approval-Gated Actions**: Runs a local Flask UI on `localhost:5050` where a human can review the AI's output before committing it.
- **MCP Integration (Google Docs)**: Once approved, the Markdown pulse note is appended magically to a persistent Google Document.
- **Bonus! Fee Explainer**: A built-in LLM tool for the support team to quickly generate unbiased fee explanations structured in < 6 bullet points.

## 🛠 Tech Stack

- **Core**: Python 3.10+
- **Scraper**: `google-play-scraper`
- **Data Prep**: `pandas`
- **AI/LLM**: `openrouter`
- **UI Approval Gate**: `flask`
- **Tool Calling (Google Docs)**: Model Context Protocol (`mcp`)
- **CI/CD Automation**: GitHub Actions (Weekly Cron)

## 🏗 Architecture

The pipeline processes data through 6 phases:
1. **Scaffold & Config**: Ingests secrets from `.env`.
2. **Scraper**: Grabs native Play Store reviews and maps to an internal JSON schema.
3. **Ingestor & Scrubber**: Filters by a 56-day sliding window and scrubs PII.
4. **Theme Engine**: A robust 3-stage LLM call that extracts themes, groups quotes deterministically, and brainstorms action ideas.
5. **Builder**: Renders the final output into Markdown (`≤250 words`) using Jinja2 templates.
6. **Approval UI**: Pauses the system. Starts a Flask server. Waits for a human to hit *[Send to Notes]* or *[Create Email Draft]*.

*View the full technical architecture in [architecture.md](architecture.md).*

## 💻 Local Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/indmoney-pulse-generator.git
   cd indmoney-pulse-generator
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r phase1_scaffold/requirements.txt
   ```

3. **Environment Setup**  
   Copy the example config and add your API keys:
   ```bash
   cp .env.example .env
   ```
   *Required Keys inside `.env`:*
   - `OPENROUTER_API_KEY`: Your OpenRouter API key
   - `APP_ID`: `com.indmoney.indstocks`

## 🏃‍♂️ Running the Pipeline

Simply run the main orchestrator script:
```bash
python phase1_scaffold/main.py
```

**What happens?**
1. It downloads the reviews to `data/raw`.
2. Cleaned data is sent to OpenRouter.
3. A browser window will automatically launch at `http://localhost:5050` for the Approval UI.
4. Review the generated pulse, and click exactly how you want it delivered!

## ☁️ Deployment (Free Forever)

This project uses a dual-platform "Git-Sync" pipeline to run completely for free:
1. **GitHub Actions**: A `.github/workflows/pulse_cron.yml` runs the heavy scraping pipeline automatically every Friday at 9:00 AM IST and commits the new Pulse drafts back to the repository.
2. **Hugging Face Spaces**: A connected Docker Space actively serves the local Flask App (Approval UI) for PMs. Whenever GitHub Actions commits a new pulse, Hugging Face automatically syncs and populates the web UI with the fresh data!
