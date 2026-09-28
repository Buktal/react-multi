# ReAct-M

**Reasoning and acting with multiple actions.**

[中文](README.zh-CN.md) · [Notebook](ReAct-M.ipynb)

ReAct-M is a Python implementation of a multi-action ReAct loop. Each reasoning round can produce a batch of tool calls: independent actions run concurrently, while dependent actions receive values from earlier results. The collected observations feed the next reasoning round.

~~~text
                   ┌─ search A → read A ─┐
Task → Reasoning ──┤                    ├─ Observations → Reasoning → Answer
                   └─ search B → read B ─┘
~~~

## Features

- **Action batches** with explicit dependencies and JSON result references.
- **Concurrent execution** with configurable limits and shared-resource ordering.
- **Iterative reasoning** when new information requires another decision.
- **Failure handling** with partial results, blocked dependents, timeouts and safe retries.
- **Model integration** through a configurable Chat Completions-compatible endpoint.
- **Wikipedia tools**, offline examples and three execution modes for comparison.

## Quick start

Requires Python 3.11 or newer.

~~~sh
git clone https://github.com/Buktal/ReAct-M.git
cd ReAct-M
python -m venv .venv
~~~

Activate the environment with `.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` on macOS/Linux, then run:

~~~sh
python -m pip install -e .
python -m react_m demo --scenario dependency
~~~

Offline examples use scripted decisions and bundled synthetic documents, so they require no API key. Choose a scenario with `--scenario independent|dependency|ambiguous|failure`, or explore them in the [Notebook](ReAct-M.ipynb).

The installed `react-m` command is equivalent to `python -m react_m`.

## Use a model

Set your API key and model name. For example, in PowerShell:

~~~powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "your-model-id"
python -m react_m ask "What professions did Nicholas Ray and Elia Kazan have in common?"
~~~

The `ask` command searches and reads Wikipedia, keeps source URLs in the execution trace, and saves the result to `results/local/question.json`.

| Setting | Purpose |
| --- | --- |
| `OPENAI_MODEL` or `--model` | Model identifier |
| `OPENAI_API_KEY` | API key |
| `OPENAI_BASE_URL` or `--base-url` | API base URL; defaults to `https://api.openai.com/v1` |
| `REACT_M_API_KEY` | Optional override for `OPENAI_API_KEY` |
| `--no-json-mode` | Disable JSON-object response mode for endpoints that do not support it |

The endpoint must support Chat Completions and `max_completion_tokens`. Wikipedia queries require network access.

## Action batches

A dependent action can bind its arguments to another action's result:

~~~json
{
  "actions": [
    {"id": "find", "tool": "search", "args": {"query": "Alder Observatory"}},
    {
      "id": "article",
      "tool": "read",
      "bindings": {
        "doc_id": {
          "action": "find",
          "pointer": "/matches",
          "select": "only",
          "project": "/id"
        }
      }
    }
  ]
}
~~~

Here, `read` receives the unique search result's ID. If the search returns zero or multiple matches, `select: only` produces `needs_reasoning` so the next round can handle the ambiguity.

| Action field | Meaning |
| --- | --- |
| `id`, `tool` | Unique action ID and registered tool name |
| `args` | Literal arguments |
| `bindings` | Arguments taken from another action's result in the same batch |
| `depends_on` | Actions that must succeed first, without transferring data |

Bindings use RFC 6901 JSON Pointers and create dependencies automatically. The Engine validates the graph before dispatch and checks bound arguments before calling the tool. Failed or ambiguous actions block their dependents; unrelated branches can continue.

The model returns one decision object: `{"type": "execute", "actions": [...]}`, `{"type": "finish", "answer": "..."}` or `{"type": "ask_user", "question": "..."}`. Schemas are available as `react_m.agent.DECISION_SCHEMA` and `react_m.protocol.BATCH_SCHEMA`.

## Python API

Register async tools with their argument schemas, then execute a batch:

~~~python
import asyncio
from react_m import Engine, Tool

async def read(doc_id: str):
    return {"id": doc_id, "year": 1892}

async def main():
    tool = Tool(
        "read", "Read a document by ID",
        {"type": "object", "properties": {"doc_id": {"type": "string"}},
         "required": ["doc_id"], "additionalProperties": False},
        read, retry_safe=True,
    )
    report = await Engine([tool]).execute(
        {"actions": [{"id": "a", "tool": "read", "args": {"doc_id": "alder"}}]}
    )
    print(report)

asyncio.run(main())
~~~

`Agent(engine, reasoner).run(task)` adds the reasoning loop. `ChatCompletionsReasoner` from `react_m.providers` connects it to a model; `ScriptedReasoner` supplies fixed decisions for examples.

Tools return JSON-serializable values and must cooperate with async cancellation. Tool settings control `timeout`, `retries`, `retry_safe`, `read_only` and shared `resource` access. Set `ordered=True` for resources requiring explicit dependency order. Retries are limited to explicitly repeatable read operations; external writes cannot automatically retry. An unresolved outcome produces `outcome_unknown` and stops further dispatch. The host must reconcile the external state before creating a new Engine.

Defaults are 32 actions per batch, four concurrent tools, a 30-second batch timeout, and eight reasoning rounds. Parameters passed to `Engine`, `Tool` and `Agent` configure execution limits; the batch schema fixes the action limit.

## Compare execution modes

| Mode | Actions per round | Same-batch result bindings |
| --- | --- | --- |
| `single` | One | No |
| `parallel` | Multiple independent actions | No |
| `multi` | Multiple independent or dependent actions | Yes |

Run the offline comparison or evaluate the same cases with your configured model:

~~~sh
python -m react_m compare --repeats 5 --output results/local/mechanics.json
python -m react_m evaluate --output results/local/live.json
~~~

`compare` measures scripted execution with configurable delays. `evaluate` records model responses, tool calls, token usage when available, and outcomes on the same four fixtures. Independent reads test concurrency; search-then-read tests parameter transfer; ambiguity and missing evidence test clarification.

The [sample results](results/README.md) demonstrate execution mechanics. Their success rates describe expected fixture behavior; real-model speed and answer quality require model-based measurements. Batching can reduce mechanical reasoning rounds, while larger batches may add unnecessary calls or delay feedback.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and checks. Report bugs or propose changes in [GitHub Issues](https://github.com/Buktal/ReAct-M/issues).

## Acknowledgments

Inspired by Yao et al., [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629), ICLR 2023. See the [original ReAct repository](https://github.com/ysymyth/ReAct).

Related approaches include [ReWOO](https://arxiv.org/abs/2305.18323), which separates planning from observation-dependent execution, and [LLMCompiler](https://arxiv.org/abs/2312.04511), which coordinates dependent tool calls with a parallel executor.

## License

[MIT](LICENSE).
