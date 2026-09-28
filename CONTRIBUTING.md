# Contributing

Use the [issue forms](https://github.com/Buktal/ReAct-M/issues/new/choose) for bug reports, feature requests and usage questions. For a substantial change, describe the use case in an issue before opening a pull request.

Fork the repository, create a branch, and open a pull request against `main`. Include the problem, the resulting behavior and how you verified it.

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

Follow the [code of conduct](CODE_OF_CONDUCT.md). Security vulnerabilities should be reported privately as described in [SECURITY.md](SECURITY.md).
