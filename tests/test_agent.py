from react_m import Agent, Engine, ScriptedReasoner, Tool


async def test_observations_feed_the_next_decision_and_all_rounds_are_counted():
    async def fact():
        return {"year": 1843}

    def finish(task, history, tools, mode):
        year = history[-1]["observation"]["results"][0]["output"]["year"]
        return {"type": "finish", "answer": str(year)}

    reasoner = ScriptedReasoner(
        [
            {"type": "execute", "actions": [{"id": "fact", "tool": "fact"}]},
            finish,
        ]
    )
    agent = Agent(Engine([Tool("fact", "Read fact", {}, fact)]), reasoner)
    result = await agent.run("What year?")
    assert result["answer"] == "1843"
    assert result["decision_calls"] == 2
    assert result["model_calls"] == 0
    assert result["tool_attempts"] == 1


async def test_invalid_decisions_use_the_existing_round_budget():
    reasoner = ScriptedReasoner([{"type": "nonsense"}] * 2)
    result = await Agent(Engine([]), reasoner, max_rounds=2).run("test")
    assert result["status"] == "budget_exhausted"
    assert result["decision_calls"] == 2
    assert len(result["history"]) == 2


async def test_single_and_parallel_modes_enforce_their_baseline_restrictions():
    async def echo():
        return "ok"

    batch = {
        "type": "execute",
        "actions": [
            {"id": "a", "tool": "echo"},
            {"id": "b", "tool": "echo", "depends_on": ["a"]},
        ],
    }
    for mode in ("single", "parallel"):
        result = await Agent(
            Engine([Tool("echo", "Echo", {}, echo)]),
            ScriptedReasoner([batch]),
            mode=mode,
            max_rounds=1,
        ).run("test")
        assert result["tool_attempts"] == 0
        assert result["history"][0]["observation"]["status"] == "rejected"
