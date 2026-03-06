"""Base agent with LLM integration, tool-scope enforcement, and audit trail."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from config import settings
from persistence.audit_log import AuditLogger
from schemas.audit import AuditAction


class BaseAgent:
    """Abstract agent with strict tool-scope enforcement.

    Subclasses must define:
      - AGENT_NAME: str
      - ALLOWED_TOOLS: set[str]  (MCP server names this agent may call)
      - SYSTEM_PROMPT: str
    """

    AGENT_NAME: str = "base"
    ALLOWED_TOOLS: set[str] = set()
    SYSTEM_PROMPT: str = ""

    def __init__(self) -> None:
        self.audit = AuditLogger()
        self._tools: dict[str, Any] = {}
        self._conversation: list[dict] = []

    def register_tool(self, name: str, tool: Any) -> None:
        if name not in self.ALLOWED_TOOLS:
            raise PermissionError(
                f"Agent '{self.AGENT_NAME}' is not allowed tool '{name}'. "
                f"Allowed: {self.ALLOWED_TOOLS}"
            )
        self._tools[name] = tool

    def _get_tool(self, name: str) -> Any:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered on agent '{self.AGENT_NAME}'")
        return self._tools[name]

    def _call_llm(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int = 16_384,
    ) -> str:
        """Call Azure OpenAI or standard OpenAI. Falls back to stub if unavailable."""
        try:
            if settings.use_azure:
                from openai import AzureOpenAI
                client = AzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                )
                kwargs: dict = {
                    "model": settings.AZURE_OPENAI_DEPLOYMENT,
                    "messages": messages,
                }
                is_o_series = settings.AZURE_OPENAI_DEPLOYMENT.startswith("o")
                if is_o_series:
                    kwargs["max_completion_tokens"] = max_tokens
                else:
                    kwargs["temperature"] = temperature or settings.LLM_TEMPERATURE
                    kwargs["max_tokens"] = max_tokens
                resp = client.chat.completions.create(**kwargs)
            else:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=temperature or settings.LLM_TEMPERATURE,
                    max_tokens=max_tokens,
                )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            return self._stub_response(messages)

    def _stub_response(self, messages: list[dict]) -> str:
        """Deterministic fallback when LLM is unavailable."""
        last = messages[-1]["content"] if messages else ""
        return json.dumps({
            "agent": self.AGENT_NAME,
            "note": "LLM unavailable — stub response",
            "input_preview": last[:200],
            "timestamp": datetime.utcnow().isoformat(),
        })

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def _log_output(self, output: dict, ticker: str = "") -> None:
        self.audit.log(
            action=AuditAction.AGENT_OUTPUT,
            agent_name=self.AGENT_NAME,
            ticker=ticker,
            details=output,
        )
