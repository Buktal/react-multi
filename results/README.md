# Scripted mechanics sample

This is a measured execution demonstration using hand-authored plans and fictional documents. It is **not a live-model benchmark**. All real model-call counts are zero.

Reproduce with:

```sh
python -m react_m compare --repeats 5 --output results/local/mechanics.json
```

Recorded environment: Python 3.13.15 on Windows. Five repetitions per scenario/mode, 20 ms configured tool delay and 10 ms configured decision delay. OS scheduling and runtime overhead affect measured times.

| Scenario | Mode | Expected behavior | Mean decisions | Median seconds |
| --- | --- | --- | --- | --- |
| independent | single | 100% | 3.0 | 0.1077 |
| independent | parallel | 100% | 2.0 | 0.0602 |
| independent | multi | 100% | 2.0 | 0.0610 |
| dependency | single | 100% | 3.0 | 0.1076 |
| dependency | parallel | 100% | 3.0 | 0.1075 |
| dependency | multi | 100% | 2.0 | 0.0916 |
| ambiguous | single | 100% | 2.0 | 0.0607 |
| ambiguous | parallel | 100% | 2.0 | 0.0601 |
| ambiguous | multi | 100% | 2.0 | 0.0605 |
| failure | single | 100% | 2.0 | 0.0597 |
| failure | parallel | 100% | 2.0 | 0.0597 |
| failure | multi | 100% | 2.0 | 0.0592 |

The independent case shows why ordinary parallel calling is an essential baseline. The dependency case removes one scripted decision in Multi. Ambiguity and failure still require handling; there is no claimed benefit on those cases.

The success column means the fixture produced its expected answer or clarification state. It is not a language-model accuracy score. No significance or generalization claim can be made from this small controlled sample.

Full configuration and all 60 traces: [mechanics.json](mechanics.json). Use `python -m react_m evaluate` for model-based runs; its output defaults to `results/local/live.json`.
