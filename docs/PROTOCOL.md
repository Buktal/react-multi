# Protocol v0.1

This document describes the implemented Python interfaces. The machine-readable decision schema is exported as `react_m.agent.DECISION_SCHEMA`; the batch schema is `react_m.protocol.BATCH_SCHEMA`.

## Model decisions

Each reasoning request returns one JSON object:

~~~json
{"type": "execute", "actions": [{"id": "a", "tool": "read", "args": {"doc_id": "alder"}}]}
~~~

~~~json
{"type": "finish", "answer": "1892"}
~~~

~~~json
{"type": "ask_user", "question": "Which observatory do you mean?"}
~~~

Only these three decision types are supported. No free-form generated script is executed and no private reasoning trace is required. Invalid decisions become rejected observations and consume an existing round, not an uncounted repair request.

The Engine accepts `{"actions": [...]}` directly, without the decision's `type`.

## Actions and bindings

| Field | Meaning |
| --- | --- |
| `id` | Unique within the batch; 1–64 letters/digits/underscores/hyphens, beginning with a letter |
| `tool` | Exact registered tool name |
| `args` | Optional object containing literal top-level arguments |
| `bindings` | Optional mapping from argument name to a result reference |
| `depends_on` | Optional list of action IDs that must succeed first |

The same parameter cannot appear in both args and bindings. Unknown fields are rejected. A batch has 1–32 actions.

~~~json
{
  "actions": [
    {"id": "find", "tool": "search", "args": {"query": "Alder Observatory"}},
    {
      "id": "read",
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

Every binding names an action in the **same batch** and an RFC 6901 `pointer` into its JSON output. The empty pointer selects the entire output. Array indexes are explicit; missing paths fail the dependent action.

The optional `select: only` requires the selected value to be an array with exactly one item. Otherwise the action returns `needs_reasoning` with zero tool attempts. Optional `project` selects a field inside that one item and requires `select`. General filtering, arbitrary expressions and cross-batch references are not supported. In a later round, known previous results can be supplied as literal arguments.

Bindings create dependency edges automatically. `depends_on` adds success prerequisites without transferring data. The graph may reference a later-listed action; array order is not an execution order. The whole graph is validated for IDs, tools, references and cycles before any dispatch. Literal-only argument objects are validated at that point; bound argument objects are validated after binding and before calling that tool.

## Tool contract

~~~python
from react_m import Engine, Tool

async def read(doc_id: str):
    return {"id": doc_id, "year": 1892}

tool = Tool(
    "read",
    "Read a document by ID",
    {"type": "object", "properties": {"doc_id": {"type": "string"}},
     "required": ["doc_id"], "additionalProperties": False},
    read,
    timeout=10,
    retry_safe=True,
)
report = await Engine([tool], concurrency=4, timeout=30).execute(
    {"actions": [{"id": "a", "tool": "read", "args": {"doc_id": "alder"}}]}
)
~~~

Handlers must be async functions and return finite JSON-serializable values. The host declares:

- `timeout`: per-attempt deadline in seconds, positive and finite.
- `retries`: 0–3 additional attempts; defaults to 0.
- `retry_safe`: host guarantees repeatability, including local state; defaults to false.
- `read_only`: no external write; defaults to true. External writes cannot automatically retry in v0.1.
- `resource`: optional shared in-process resource name for mutual exclusion.
- `ordered`: requires an explicit dependency order among actions sharing that resource.

A tool raises `RetryableToolError` for a transient failure. Only retry-safe tools retry that exception or a cooperatively cancelled timeout, with bounded backoff. Arbitrary programming/validation errors do not automatically retry. Tools may raise `NeedsReasoning` from `react_m.protocol` when their own structured checks cannot continue.

Unknown outcomes must be reconciled outside the Engine. Setting retry_safe on a stateful cursor operation without an actual repeatability guarantee is incorrect.

## Reports

A batch status is `complete`, `partial`, `rejected`, or `interrupted`. Rejected batches have zero tool attempts. Every action in an accepted batch has a result identified by its ID, with attempts and elapsed seconds.

| Action status | Meaning |
| --- | --- |
| `succeeded` | Tool returned valid JSON; output is available |
| `failed` | Binding, schema validation or a confirmed read/tool failure |
| `needs_reasoning` | An explicit selection/check cannot continue |
| `blocked` | A predecessor failed or further execution is unsafe |
| `cancelled` | Execution was interrupted before a confirmed result |
| `outcome_unknown` | Operation may have taken effect; automatic replay is unsafe |

Unrelated branches retain their results. Failed/ambiguous descendants do not execute. A batch deadline requests cancellation; it does not claim to roll back external effects. Per-action elapsed time includes dependency and resource waiting. Batch time measures the whole execution.

Agent statuses include `finished`, `needs_input`, `budget_exhausted`, `provider_error` and `needs_reconciliation`. `finished` means the model supplied an answer, not that an external evaluator proved it correct.

## Budgets and measurements

Defaults: eight decisions, up to 128 tool attempts reserved conservatively using each tool's retry limit, 32 actions per batch, four concurrent tools, 30 seconds per batch and 10 seconds per tool attempt. These limits do not forcibly stop untrusted or blocking Python code.

`decision_calls` counts all reasoning-adapter calls. `model_calls` counts actual model requests; scripted runs report zero. Token totals use provider-reported usage; `usage_complete=false` identifies missing usage and no monetary cost is inferred. No nested model call occurs inside the Engine.

Single mode rejects multi-action batches; single and parallel modes reject intra-batch dependencies/references. These restrictions are enforced, not merely mentioned in a prompt.
