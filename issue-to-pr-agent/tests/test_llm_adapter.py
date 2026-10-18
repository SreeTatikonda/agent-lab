from types import SimpleNamespace as NS

from codeagent.llm import AnthropicLLM
from codeagent.tools import TOOL_SPECS


class FakeMessages:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return NS(
            content=[NS(type="text", text="Reading the file."),
                     NS(type="tool_use", id="toolu_1", name="view_file", input={"path": "a.py"})],
            usage=NS(input_tokens=500, cache_read_input_tokens=9000, cache_creation_input_tokens=0,
                     output_tokens=40),
        )


def test_adapter_parses_tool_calls_and_usage():
    fake = FakeMessages()
    llm = AnthropicLLM(model="m", client=NS(messages=fake))
    reply = llm.complete("sys", [{"role": "user", "content": "task"}], TOOL_SPECS)
    assert reply.text == "Reading the file."
    assert reply.tool_calls[0].name == "view_file" and reply.tool_calls[0].input == {"path": "a.py"}
    assert reply.usage.input_tokens == 9500 and reply.usage.cached_input_tokens == 9000


def test_adapter_places_cache_breakpoints_without_mutating_inputs():
    fake = FakeMessages()
    tools = [dict(t) for t in TOOL_SPECS]
    messages = [{"role": "user", "content": "task"}]
    AnthropicLLM(model="m", client=NS(messages=fake)).complete("sys", messages, tools)
    sent = fake.kwargs
    assert sent["tools"][-1]["cache_control"] == {"type": "ephemeral"}
    assert sent["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert sent["messages"][-1]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in tools[-1] and messages[0]["content"] == "task"
