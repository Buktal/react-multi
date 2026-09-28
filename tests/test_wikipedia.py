import httpx

from react_m import Engine
from react_m.wikipedia import wikipedia_tools


async def test_wikipedia_search_result_can_feed_a_read_with_source_provenance():
    def respond(request):
        params = request.url.params
        if params.get("list") == "search":
            return httpx.Response(
                200,
                json={
                    "query": {
                        "search": [
                            {"pageid": 42, "title": "Example", "snippet": "A <b>source</b>"},
                        ]
                    }
                },
            )
        assert params["pageids"] == "42"
        return httpx.Response(
            200,
            json={
                "query": {
                    "pages": {
                        "42": {
                            "pageid": 42,
                            "title": "Example",
                            "extract": "A documented fact.",
                        }
                    }
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        report = await Engine(wikipedia_tools(client=client)).execute(
            {
                "actions": [
                    {"id": "find", "tool": "search", "args": {"query": "Example"}},
                    {
                        "id": "read",
                        "tool": "read",
                        "bindings": {
                            "doc_id": {
                                "action": "find",
                                "pointer": "/matches",
                                "select": "only",
                                "project": "/id",
                            }
                        },
                    },
                ]
            }
        )
    assert report["status"] == "complete"
    assert report["results"][1]["output"] == {
        "title": "Example",
        "text": "A documented fact.",
        "source_url": "https://en.wikipedia.org/?curid=42",
        "truncated": False,
    }
