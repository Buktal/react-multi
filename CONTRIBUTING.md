# Contributing

Use Python 3.11 or newer. Install the package with `python -m pip install -e ".[dev]"`.

Before a pull request, run:

```sh
python -m pytest
python -m ruff check .
python -m mypy src/react_m
python -m build
```

Tests cross public interfaces: `Engine.execute`, `Agent.run`, the HTTP model adapter, and experiment/CLI entry points. Use controlled async tools and HTTP transports; tests must not require API keys, external websites, datasets or paid calls. Test outcomes and observable behavior rather than private scheduling methods.

Keep this a small research implementation. Prefer explicit data flow and a few public interfaces over a plugin framework. Public code is typed; explain semantic changes in `docs/PROTOCOL.md`. Add regression tests for correctness changes, especially dependency validation, cancellation, resource ordering and tool side effects.

Benchmark changes must preserve comparable tasks, tool interfaces and budgets across modes. Label scripted runs, retain failures, and never claim a performance or novelty result that has not been measured. See `docs/RELATED_WORK.md` and `docs/EVALUATION.md`.

Use GitHub issues for bugs and proposals. Do not attach credentials, private prompts or sensitive tool outputs. The MIT license covers original contributions; preserve upstream notices for any code introduced from other projects.
