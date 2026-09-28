# Contributing

Use Python 3.11 or newer. Install the package with `python -m pip install -e ".[dev]"`.

Before a pull request, run:

```sh
python -m pytest
python -m ruff check .
python -m mypy src/react_m
python -m build
```

Tests cover the Engine, Agent, model adapter and CLI using local fixtures and mock HTTP transports. They run without API keys or network access. CI runs these checks on Windows and Linux with Python 3.11 and 3.13.

For a bug fix, include a regression test that exercises the affected public behavior. Update the English and Chinese READMEs when changing the API or CLI.

When contributing experiments, include the configuration and outcomes, identify scripted or model-based runs, and use comparable tasks, tools and budgets across modes.

Use GitHub issues for bugs and proposals. Do not attach credentials, private prompts or sensitive tool outputs. The MIT license covers original contributions; preserve upstream notices for any code introduced from other projects.
