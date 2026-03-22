"""
Phase 4B — Fee Explainer Engine

Generates a neutral, fact-only explanation for a given fee scenario
using the LLM MCP Router.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

FEE_EXPLAINER_SYSTEM = """
You are a senior Financial Compliance Officer at INDMoney. Your task is to provide a neutral, facts-only explanation for a specific fee or charge scenario.

Rules:
1. Provide exactly 6 bullet points (no more than 6).
2. Maintain a neutral, professional, and objective tone.
3. strictly NO recommendations, NO comparisons with other apps, and NO financial advice.
4. Include exactly 2 official source links. Prioritize these domains: indmoney.com/pricing, indmoney.com/mutual-funds/pricing, indmoney.com/us-stocks/pricing, sebi.gov.in, rbi.org.in.
5. Ensure the information is accurate based on current knowledge.
6. Respond in strict JSON format.

Output Format:
{{
  "scenario": "Original Scenario Name",
  "bullets": [
    "Fact 1...",
    "Fact 2..."
  ],
  "source_links": [
    "https://...",
    "https://..."
  ],
  "last_checked": "{today_date}"
}}
"""

def generate_fee_explanation(router, scenario: str) -> Optional[Dict]:
    """
    Generates a structured explanation for a fee scenario.
    
    Args:
        router: LLMMCPRouter (or any object with chat_completion method)
        scenario: Fee scenario to explain
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"    🔍 Explaining fee scenario: {scenario}...")
    
    system_prompt = FEE_EXPLAINER_SYSTEM.format(today_date=today)
    user_prompt = f"Explain this fee scenario for INDMoney: {scenario}"
    
    resp = router.chat_completion(system_prompt, user_prompt)
    
    try:
        data = json.loads(resp)
        return data
    except json.JSONDecodeError:
        logger.error(f"Failed to parse fee explanation JSON: {resp}")
        return None
