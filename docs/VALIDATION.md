# Initial validation record

This records what was actually checked for v0.1.0. It does not certify real-model answer quality.

## Executed checks

- Python 3.13 on Windows: the test suite exercises public Engine, Agent, model-transport, experiment and Wikipedia-tool interfaces.
- Ruff lint and mypy type checking passed.
- Source distribution and wheel builds succeeded. A wheel installed into a separate environment ran all four offline scenarios in all three modes, without importing the working checkout.
- All three executable notebook cells ran locally; their outputs are included in the notebook.
- Five repetitions of four scenarios and three modes produced 60 stored mechanics traces, all matching the fixture's expected behavior. These are scripted runs with simulated delays and zero model requests.
- Actual network calls to Wikipedia searched for Ada Lovelace and read page ID 974 successfully. The read returned a source URL and correctly marked a 12000-character truncated extract.
- Local Markdown links and bundled fixture files were checked.

CI runs the tests, lint, types, build and an offline comparison on Windows/Linux with Python 3.11/3.13. Its current status is shown in the repository's Actions tab; local checks alone are not evidence that remote CI passed.

## Standards review

Automated standards checks passed. A separate Standards reviewer could not complete because its service was rate-limited; no independent Standards pass is claimed. The implementation was manually checked for unnecessary indirection, interface consistency, secret handling and consistency between documentation and code. Remaining experimental limits are documented rather than hidden.

## Spec review

An independent read-only reviewer compared the core implementation to docs/SPEC.md from the initial empty commit. It reported no actionable missing requirement, scope-creep issue or incorrect implementation. It additionally checked timeout branch isolation, safe Engine reuse and fixture inclusion in the wheel.

The later Wikipedia adapter and custom-question CLI were checked separately through an HTTP fixture, an actual Wikipedia request, type/lint checks and packaging validation. The core independent review predates that small addition.

## Not established

- No actual language-model endpoint was called: model credentials were not configured. Provider transport tests use controlled HTTP responses.
- No verified task-quality, token-cost or latency advantage for a real language model.
- No reproduction of original ReAct benchmark scores, large-dataset evaluation or statistical significance result.
- No trained Jev router, production write recovery, distributed locking or sandboxing guarantee.

The supported conclusion is that the implemented batching mechanism works on the tested cases and is worth evaluating further. Related approaches already exist; see RELATED_WORK.md before making novelty claims.
