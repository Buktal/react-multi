import asyncio

import pytest

from react_m import Engine, Tool


@pytest.mark.asyncio
async def test_independent_actions_can_make_progress_together():
    both_started = asyncio.Event()
    started = []

    async def lookup(name):
        started.append(name)
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), 1)
        return {"name": name}

    tool = Tool(
        "lookup",
        "Look up a record",
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
        lookup,
    )
    report = await Engine([tool]).execute(
        {
            "actions": [
                {"id": "a", "tool": "lookup", "args": {"name": "Ada"}},
                {"id": "b", "tool": "lookup", "args": {"name": "Grace"}},
            ]
        }
    )
    assert report["status"] == "complete"
    assert {r["id"]: r["output"] for r in report["results"]} == {
        "a": {"name": "Ada"},
        "b": {"name": "Grace"},
    }


@pytest.mark.parametrize(
    "users, expected_status",
    [
        ([{"id": "u-7"}], "succeeded"),
        ([], "needs_reasoning"),
        ([{"id": "u-7"}, {"id": "u-8"}], "needs_reasoning"),
    ],
)
async def test_orders_require_a_unique_user_without_an_extra_model_call(users, expected_status):
    async def find():
        return {"users": users}

    async def orders(user_id):
        return {"user": user_id, "total": 42}

    tools = [
        Tool("find", "Find users", {"type": "object"}, find),
        Tool(
            "orders",
            "Get orders",
            {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
            },
            orders,
        ),
    ]
    report = await Engine(tools).execute(
        {
            "actions": [
                {"id": "find", "tool": "find"},
                {
                    "id": "orders",
                    "tool": "orders",
                    "bindings": {
                        "user_id": {
                            "action": "find",
                            "pointer": "/users",
                            "select": "only",
                            "project": "/id",
                        }
                    },
                },
            ]
        }
    )
    result = report["results"][1]
    assert result["status"] == expected_status
    if expected_status == "succeeded":
        assert result["output"] == {"user": "u-7", "total": 42}
    else:
        assert result["attempts"] == 0


@pytest.mark.parametrize(
    "actions",
    [
        [{"id": "a", "tool": "echo"}, {"id": "a", "tool": "echo"}],
        [{"id": "a", "tool": "missing"}],
        [{"id": "a", "tool": "echo", "depends_on": ["missing"]}],
        [
            {"id": "a", "tool": "echo", "depends_on": ["b"]},
            {"id": "b", "tool": "echo", "depends_on": ["a"]},
        ],
        [{"id": "a", "tool": "echo", "args": {"unexpected": True}}],
    ],
)
async def test_invalid_batch_is_rejected_before_any_tool_runs(actions):
    called = []

    async def echo():
        called.append(True)
        return "ok"

    tool = Tool("echo", "Echo", {"type": "object", "additionalProperties": False}, echo)
    report = await Engine([tool]).execute({"actions": actions})
    assert report["status"] == "rejected"
    assert called == []


async def test_failed_branch_does_not_discard_unrelated_evidence():
    async def unavailable():
        raise ConnectionError("offline")

    async def evidence():
        return {"finding": "service healthy"}

    tools = [Tool("bad", "Unavailable", {}, unavailable), Tool("ok", "Evidence", {}, evidence)]
    report = await Engine(tools).execute(
        {
            "actions": [
                {"id": "failure", "tool": "bad"},
                {"id": "child", "tool": "ok", "depends_on": ["failure"]},
                {"id": "independent", "tool": "ok"},
            ]
        }
    )
    assert [r["status"] for r in report["results"]] == ["failed", "blocked", "succeeded"]
    assert report["results"][2]["output"] == {"finding": "service healthy"}


async def test_resource_lock_prevents_lost_updates():
    counter = 0

    async def increment():
        nonlocal counter
        value = counter
        await asyncio.sleep(0)
        counter = value + 1
        return counter

    tool = Tool("increment", "Update local state", {}, increment, resource="counter")
    report = await Engine([tool]).execute(
        {
            "actions": [
                {"id": "a", "tool": "increment"},
                {"id": "b", "tool": "increment"},
            ]
        }
    )
    assert sorted(r["output"] for r in report["results"]) == [1, 2]


async def test_order_sensitive_session_requires_explicit_dependencies():
    async def search():
        return "page"

    engine = Engine(
        [Tool("search", "Stateful search", {}, search, resource="wiki-session", ordered=True)]
    )
    report = await engine.execute(
        {
            "actions": [
                {"id": "a", "tool": "search"},
                {"id": "b", "tool": "search"},
            ]
        }
    )
    assert report["status"] == "rejected"
    report = await engine.execute(
        {
            "actions": [
                {"id": "a", "tool": "search"},
                {"id": "b", "tool": "search", "depends_on": ["a"]},
            ]
        }
    )
    assert report["status"] == "complete"


async def test_safe_transient_failure_can_be_retried():
    from react_m import RetryableToolError

    attempts = 0

    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RetryableToolError("temporarily unavailable")
        return "recovered"

    tool = Tool("flaky", "Read", {}, flaky, retry_safe=True, retries=1)
    report = await Engine([tool]).execute({"actions": [{"id": "a", "tool": "flaky"}]})
    assert report["results"][0]["output"] == "recovered"
    assert report["tool_attempts"] == 2


async def test_unknown_write_outcome_cannot_be_resubmitted_with_a_new_id():
    async def write():
        await asyncio.sleep(10)

    engine = Engine([Tool("write", "External write", {}, write, read_only=False, timeout=0.01)])
    first = await engine.execute({"actions": [{"id": "a", "tool": "write"}]})
    assert first["results"][0]["status"] == "outcome_unknown"
    second = await engine.execute({"actions": [{"id": "new_id", "tool": "write"}]})
    assert second["status"] == "rejected"
    assert second["tool_attempts"] == 0


async def test_batch_deadline_cancels_reads_and_accounts_for_started_attempts():
    async def slow():
        await asyncio.sleep(10)

    engine = Engine([Tool("slow", "Slow read", {}, slow, retry_safe=True)], timeout=0.02)
    report = await engine.execute(
        {
            "actions": [
                {"id": "a", "tool": "slow"},
                {"id": "b", "tool": "slow", "depends_on": ["a"]},
            ]
        }
    )
    assert report["status"] == "interrupted"
    assert report["tool_attempts"] == 1
    assert all(r["status"] in {"cancelled", "blocked"} for r in report["results"])
