"""Model adapters. The agent only depends on the LLM protocol below.

AnthropicLLM talks to the real API with prompt caching on the stable prefix.
ScriptedLLM replays a fixed policy so the whole loop can be tested offline and for free.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Sequence

from .models import ToolCall, Usage


@dataclass
class AssistantTurn:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)


class LLM(Protocol):
    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> AssistantTurn: ...


# ---------------------------------------------------------------- real model
class AnthropicLLM:
    def __init__(self, model: str = "claude-sonnet-5-5", max_tokens: int = 2048, client: Any = None):
        if client is None:
            import anthropic  # optional dependency
            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        cached_tools = [dict(t) for t in tools]
        if cached_tools:
            # one cache breakpoint after tools + system, the part that never changes mid-run
            cached_tools[-1]["cache_control"] = {"type": "ephemeral"}
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            tools=cached_tools,
            messages=_with_rolling_cache(messages),
        )
        text_parts, calls = [], []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(block.id, block.name, dict(block.input)))
        u = response.usage
        cached = (getattr(u, "cache_read_input_tokens", 0) or 0)
        written = (getattr(u, "cache_creation_input_tokens", 0) or 0)
        usage = Usage(input_tokens=u.input_tokens + cached + written,
                      cached_input_tokens=cached, output_tokens=u.output_tokens)
        return AssistantTurn("\n".join(text_parts).strip(), calls, usage)


def _with_rolling_cache(messages: list[dict]) -> list[dict]:
    """Mark the last user message as a cache breakpoint so the next call reuses the whole prefix."""
    if not messages:
        return messages
    out = [dict(m) for m in messages]
    last = out[-1]
    content = last["content"]
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    content = [dict(b) for b in content]
    content[-1]["cache_control"] = {"type": "ephemeral"}
    last["content"] = content
    return out


# ---------------------------------------------------------------- test double
Policy = Callable[[list[dict]], AssistantTurn]


def call(name: str, **args: Any) -> ToolCall:
    return ToolCall("toolu_" + uuid.uuid4().hex[:10], name, args)


def turn(text: str, *calls: ToolCall, input_tokens: int = 2000, output_tokens: int = 150) -> AssistantTurn:
    return AssistantTurn(text, list(calls), Usage(input_tokens, int(input_tokens * 0.8), output_tokens))


class ScriptedLLM:
    """Plays back turns in order. A turn may be an AssistantTurn or a function of the transcript,
    so scripts can react to what the tools actually returned."""

    def __init__(self, script: Sequence[AssistantTurn | Policy], repeat_last: bool = False):
        self.script = list(script)
        self.repeat_last = repeat_last
        self.calls = 0
        self.seen_messages: list[list[dict]] = []

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> AssistantTurn:
        self.seen_messages.append([dict(m) for m in messages])
        if self.calls >= len(self.script):
            if not self.repeat_last:
                raise RuntimeError("scripted model ran out of turns")
            item = self.script[-1]
        else:
            item = self.script[self.calls]
        self.calls += 1
        result = item(messages) if callable(item) else item
        # fresh ids every time so repeated turns still look like distinct calls
        result = AssistantTurn(result.text,
                               [ToolCall("toolu_" + uuid.uuid4().hex[:10], c.name, dict(c.input))
                                for c in result.tool_calls],
                               result.usage)
        return result


def last_tool_result(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m["role"] == "user" and isinstance(m["content"], list):
            for block in reversed(m["content"]):
                if block.get("type") == "tool_result":
                    return str(block.get("content", ""))
    return ""
