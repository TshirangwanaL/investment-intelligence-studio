"""News Sentiment Analyst — LLM-powered structured sentiment scoring.

Fills the gap: GDELT provides raw articles but no structured sentiment analysis.
This agent scores and categorises a batch of articles.
"""

from __future__ import annotations

import json
from typing import Any

from agents.base import BaseAgent


class NewsSentimentAgent(BaseAgent):
    AGENT_NAME = "news_sentiment"
    ALLOWED_TOOLS = {"mcp_news_gdelt"}
    SYSTEM_PROMPT = """You are a financial news analyst at an institutional fund.
Given a batch of news headlines and metadata, produce structured sentiment analysis.

For EACH article:
- sentiment: bullish / bearish / neutral
- magnitude: 0.0–1.0 (how strong the signal is)
- category: one of [macro, earnings, regulatory, geopolitical, sector, company_specific, legal, other]
- relevance: 0.0–1.0 (how relevant to the query)

Also produce an AGGREGATE summary:
- overall_sentiment: bullish / bearish / neutral
- confidence: 0.0–1.0
- dominant_themes: top 3 themes from the batch
- risk_flags: any high-risk signals (litigation, fraud, bankruptcy, regulatory)

Return valid JSON with NO commentary outside the JSON object."""

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        query = context.get("query", "")
        max_records = context.get("max_records", 20)
        timespan = context.get("timespan", "7d")

        articles_raw: list[dict] = []
        if "mcp_news_gdelt" in self._tools:
            gdelt = self._get_tool("mcp_news_gdelt")
            result = gdelt.search_news(
                query=query, max_records=max_records, timespan=timespan
            )
            if result.success and result.data:
                articles_raw = result.data.get("articles", [])

        if not articles_raw:
            return {
                "query": query,
                "articles": [],
                "aggregate": {
                    "overall_sentiment": "neutral",
                    "confidence": 0.0,
                    "dominant_themes": [],
                    "risk_flags": [],
                },
                "note": "No articles found",
            }

        headlines = []
        for i, a in enumerate(articles_raw[:30]):
            headlines.append({
                "idx": i,
                "title": a.get("title", "")[:120],
                "domain": a.get("domain", ""),
                "tone": a.get("tone", 0),
                "date": a.get("seendate", ""),
            })

        prompt = f"""Analyze the sentiment of these {len(headlines)} news articles about "{query}".

ARTICLES:
{json.dumps(headlines, indent=1, default=str)[:6000]}

Return valid JSON:
{{
  "article_scores": [
    {{"idx": 0, "sentiment": "bullish|bearish|neutral", "magnitude": 0.0, "category": "...", "relevance": 0.0}},
    ...
  ],
  "aggregate": {{
    "overall_sentiment": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "dominant_themes": ["theme1", "theme2", "theme3"],
    "risk_flags": ["flag1"] or []
  }}
}}"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw = self._call_llm(messages)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "article_scores": [],
                "aggregate": {
                    "overall_sentiment": "neutral",
                    "confidence": 0.3,
                    "dominant_themes": [],
                    "risk_flags": [],
                },
            }

        scores = {s["idx"]: s for s in parsed.get("article_scores", []) if "idx" in s}
        enriched_articles = []
        for i, a in enumerate(articles_raw[:30]):
            score = scores.get(i, {})
            enriched_articles.append({
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "domain": a.get("domain", ""),
                "date": a.get("seendate", ""),
                "gdelt_tone": a.get("tone", 0),
                "llm_sentiment": score.get("sentiment", "neutral"),
                "llm_magnitude": score.get("magnitude", 0.0),
                "llm_category": score.get("category", "other"),
                "llm_relevance": score.get("relevance", 0.0),
            })

        output = {
            "query": query,
            "articles": enriched_articles,
            "aggregate": parsed.get("aggregate", {}),
            "article_count": len(enriched_articles),
        }

        self._log_output(output)
        return output
