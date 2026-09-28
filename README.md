# ReAct-M

**Reasoning and acting with multiple actions.** A small Python research implementation inspired by [ReAct](https://github.com/ysymyth/ReAct).

[中文说明](docs/README.zh-CN.md) · [Notebook](ReAct-M.ipynb) · [Protocol](docs/PROTOCOL.md) · [Related work](docs/RELATED_WORK.md)

ReAct-M extends the action in a ReAct loop into a batch. Independent actions can run concurrently; dependent actions can use explicitly referenced results without another model request. When new observations require a new decision, the next reasoning round handles it.

~~~text
Reason → [search A ─→ read A
          search B ─→ read B] → Observations → Reason
~~~

This repository provides an installable implementation, offline examples, a configurable real-model adapter, tests, and three comparison modes. It is an early research implementation, not a production workflow platform.

## Quick start

Requires Python 3.11 or newer. No API key is needed for the first two commands.

~~~sh
git clone https://github.com/Buktal/ReAct-M.git
cd ReAct-M
python -m venv .venv
~~~

Activate with `.venv\Scripts\Activate.ps1` on PowerShell or `source .venv/bin/activate` on macOS/Linux, then:

~~~sh
python -m pip install -e ".[dev]"
python -m react_m demo --scenario dependency
python -m react_m compare --repeats 5 --output results/local/mechanics.json
~~~

The installed `react-m` command is equivalent to `python -m react_m`. The notebook uses the same public experiment functions.

**Offline demos use hand-authored plans and fictional documents. They are labeled scripted, make zero model requests, and are not evidence of real-model accuracy or speed.**

## What is implemented

- A bounded Reason → Action Batch → Observation loop.
- Explicit result bindings and success dependencies, validated before dispatch.
- Bounded parallelism, shared-resource locks and required ordering for stateful tools.
- Exactly-one candidate selection: ambiguity returns to reasoning instead of silently choosing.
- Partial results, branch failure isolation, finite retries for explicitly safe reads, and conservative unknown-outcome handling.
- Single-action, independent-parallel and dependency-aware multi-action modes.
- A Chat Completions-compatible adapter with configurable model/endpoint and token accounting.

Jev remains an optional future routing adapter. The initial implementation exposes the full small tool catalog; no trained router is included.

## A batch with a data dependency

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

`read` receives the unique search result's ID. Zero or multiple matches produce `needs_reasoning`; the model can ask for clarification in the next round. See [the complete protocol](docs/PROTOCOL.md).

## Run a real model

Configure credentials locally; never commit them. Select a model available at your endpoint explicitly. For example, in PowerShell:

~~~powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "your-model-id"
python -m react_m evaluate --output results/local/live.json
~~~

For another compatible endpoint, set `OPENAI_BASE_URL` to its API base URL (usually ending in `/v1`). `REACT_M_API_KEY` overrides `OPENAI_API_KEY`. Use `--no-json-mode` if the endpoint does not support JSON-object response mode. The adapter sends `max_completion_tokens`; endpoints must support this parameter.

The evaluation runs all three modes on the same four tiny fixtures. It can incur API charges. Raw traces and reported usage are saved, including failures. These fixtures are smoke tests, not HotpotQA/FEVER/ALFWorld/WebShop reproductions.

For a custom question with live Wikipedia evidence:

~~~sh
python -m react_m ask "What professions did Nicholas Ray and Elia Kazan have in common?"
~~~

This uses the same model configuration and read-only Wikipedia search/read tools, returning source URLs in the trace. It requires network access. Pages use explicit IDs and may be truncated to 12000 characters with a flag; this is a new adapter, not the original shared-state WikiEnv. An actual model endpoint is still required to validate end-to-end answers.

## Evidence and positioning

| Mode | Same-round independent calls | Same-batch result bindings |
| --- | --- | --- |
| Single-action | No | No |
| Independent-parallel | Yes | No |
| ReAct-M | Yes | Yes |

The initial [mechanics experiment](results/README.md) shows the expected narrow behavior: ordinary parallel execution already captures independent-query gains; a deterministic dependency can remove an intermediate decision; ambiguity and failures still require handling.

**No live-model benchmark result has been established for this release.** ReWOO and LLMCompiler already cover closely related planning and execution ideas. This project makes no claim to invent parallel tool calling, introduce a new reasoning paradigm, or outperform those systems. Read [related work and claim boundaries](docs/RELATED_WORK.md).

## Development

~~~sh
python -m pytest
python -m ruff check .
python -m mypy src/react_m
python -m build
~~~

See [contributing](CONTRIBUTING.md), [design](docs/DESIGN.md), [evaluation methodology](docs/EVALUATION.md), [validation record](docs/VALIDATION.md), and [v0.1 scope](docs/SPEC.md).

## Acknowledgments and license

Inspired by Yao et al., **ReAct: Synergizing Reasoning and Acting in Language Models**, ICLR 2023 ([paper](https://arxiv.org/abs/2210.03629), [original code](https://github.com/ysymyth/ReAct)). This implementation and its fictional fixtures are independently written; no original dataset or notebook code is bundled. It is not affiliated with the ReAct authors or the React JavaScript framework.

MIT — see [LICENSE](LICENSE).
