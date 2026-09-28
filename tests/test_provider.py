import json

import httpx

from react_m import Agent, Engine
from react_m.providers import ChatCompletionsReasoner


async def test_chat_adapter_sends_protocol_and_counts_usage():
    def respond(request):
        body = json.loads(request.content)
        assert request.url.path == "/v1/chat/completions"
        assert body["model"] == "configured-model"
        assert body["response_format"] == {"type": "json_object"}
        assert "execute" in body["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"type":"finish","answer":"1843"}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        reasoner = ChatCompletionsReasoner("configured-model", api_key="test-only", client=client)
        result = await Agent(Engine([]), reasoner).run("What year?")
    assert result["answer"] == "1843"
    assert (result["model_calls"], result["input_tokens"], result["output_tokens"]) == (1, 12, 8)


async def test_provider_failure_does_not_print_credentials_or_retry_silently():
    def respond(request):
        return httpx.Response(401, json={"error": "test-only-secret must not be logged"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        reasoner = ChatCompletionsReasoner(
            "configured-model", api_key="test-only-secret", client=client
        )
        result = await Agent(Engine([]), reasoner).run("test")
    assert result["status"] == "provider_error"
    assert result["model_calls"] == 1
    assert "test-only-secret" not in json.dumps(result)
