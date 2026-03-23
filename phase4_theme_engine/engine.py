"""
Phase 4 — Theme Engine

Orchestrates the LLM pipeline to:
1. Generate high-level themes from a batch of reviews.
2. Extract representative verbatim quotes for each theme.
3. Suggest actionable product improvement ideas.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict

logger = logging.getLogger(__name__)


@dataclass
class Theme:
    theme: str
    summary: str
    quote: str | None = None  # Will be populated in Stage 2

@dataclass
class ThemeResult:
    themes: List[Theme]
    action_ideas: List[str]
    metadata: Dict

# ═══════════════════════════════════════════════════════════════════════════════
#  Prompts
# ═══════════════════════════════════════════════════════════════════════════════

THEME_GENERATION_SYSTEM = """
You are a senior Product Manager at INDMoney. Your task is to analyze customer reviews for the mobile app.
Identify 3-5 distinct, meaningful themes from the provided list of reviews.
Focus on user pain points, feature requests, or areas of delight.

Rules:
1. Return exactly 3 to 5 themes.
2. For each theme, provide a concise summary (1-2 sentences).
3. Be specific. Instead of "UI issues", say "Difficulty navigating portfolio view".
4. Respond in strict JSON format.

Output Format:
{
  "themes": [
    {"theme": "Theme Title", "summary": "Summary description"}
  ]
}
"""

QUOTE_EXTRACTION_SYSTEM_V2 = """
You are a Product Analyst. Your task is to identify and select the single best verbatim user quote from the provided list of reviews that most strongly supports and illustrates the given theme.

Theme: {theme}
Summary: {summary}

Rules:
1. Select exactly ONE quote that exists verbatim in the input data.
2. IF NO PERFECT QUOTE EXISTS, pick the most relevant sentence or phrase from a review.
3. Do not include user names, dates, or PII.
4. Keep the quote concise.
5. Respond in strict JSON format.

Output Format:
{{
  "quote": "verbatim user quote here"
}}
"""

ACTION_IDEAS_SYSTEM = """
You are a Product Strategy lead. Based on the following aggregated themes from app reviews, suggest 3 highly actionable product or process improvement ideas.

Themes:
{themes_context}

Rules:
1. Provide exactly 3 action ideas.
2. Each idea should be specific, feasible, and directly address the themes.
3. Respond in strict JSON format.

Output Format:
{{
  "action_ideas": ["Action 1", "Action 2", "Action 3"]
}}
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  Engine Functions
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_reviews(router, reviews: List[Dict]) -> ThemeResult:
    """
    Runs the 3-stage LLM pipeline.

    Args:
        router:   LLMMCPRouter that handles provider selection for all calls.
        reviews:  List of review dicts with 'text' field.
    """
    if not reviews:
        return ThemeResult(themes=[], action_ideas=[], metadata={"status": "no_reviews"})

    review_texts = "\n".join([f"- {r['text']}" for r in reviews])

    # --- Step 1: Generate Themes (via MCP Router) ---
    print("    🎨 Stage 1: Generating high-level themes...")
    theme_resp = router.chat_completion(THEME_GENERATION_SYSTEM, f"Reviews:\n{review_texts}")
    try:
        themes_data = json.loads(theme_resp).get("themes", [])
    except json.JSONDecodeError:
        logger.error(f"Failed to parse themes JSON: {theme_resp}")
        themes_data = []

    themes = [Theme(theme=t["theme"], summary=t["summary"], quote=None) for t in themes_data]

    # --- Step 2: Extract Quotes (via MCP Router with Fallback) ---
    for theme in themes:
        print(f"    💬 Stage 2: Extracting best quote for theme: {theme.theme}")
        quote_prompt = f"Available Reviews:\n{review_texts}"
        
        # Primary Attempt
        quote_resp = router.chat_completion(
            QUOTE_EXTRACTION_SYSTEM_V2.format(theme=theme.theme, summary=theme.summary),
            quote_prompt
        )
        
        try:
            theme.quote = json.loads(quote_resp).get("quote", "")
        except (json.JSONDecodeError, AttributeError):
            theme.quote = ""

        # Fallback Attempt: If primary failed, try specifically via a more robust model (Gemini 2.0 Flash)
        if not theme.quote or theme.quote.strip() == "":
            print(f"      🔂 Quote empty for '{theme.theme}' — Retrying via Robust Fallback (Gemini 2.0)...")
            try:
                # Use OpenRouter but with a more powerful model than Haiku
                fallback_resp = router.chat_completion(
                    QUOTE_EXTRACTION_SYSTEM_V2.format(theme=theme.theme, summary=theme.summary),
                    quote_prompt,
                    retries=2,
                    model_override="liquid/lfm-2.5-1.2b-thinking:free"
                )
                
                # Note: openrouter.chat_completion might still use the default model from .env 
                # unless I pass a model override. Let's modify OpenRouterClient to allow model override.
                
                theme.quote = json.loads(fallback_resp).get("quote", "")
                if theme.quote:
                    print(f"      ✅ Fallback success for '{theme.theme}'")
            except Exception as e:
                print(f"      ❌ Fallback failed for '{theme.theme}': {e}")
                theme.quote = ""

    # --- Step 3: Generate Action Ideas (via MCP Router) ---
    print("    💡 Stage 3: Generating actionable product ideas...")
    themes_context = "\n".join([f"- {t.theme}: {t.summary}" for t in themes])
    action_resp = router.chat_completion(
        ACTION_IDEAS_SYSTEM.format(themes_context=themes_context),
        "Generate 3 action ideas based on these themes."
    )
    try:
        action_ideas = json.loads(action_resp).get("action_ideas", [])
    except json.JSONDecodeError:
        logger.error(f"Failed to parse action ideas JSON: {action_resp}")
        action_ideas = []

    return ThemeResult(
        themes=themes,
        action_ideas=action_ideas,
        metadata={
            "review_count": len(reviews),
            "model": "mcp_router"
        }
    )
