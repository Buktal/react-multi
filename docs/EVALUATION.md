# Evaluation

Two different questions must stay separate: does the execution mechanism work, and does a real model solve tasks better with it?

## Included mechanics experiment

~~~sh
python -m react_m compare --repeats 5 --output results/local/mechanics.json
~~~

Plans are hand-authored, documents are fictional, and tool/decision delays are configurable simulated waits. All actual outputs, failures and timings are retained. Task/mode order is shuffled with a fixed seed. The committed sample is in [results](../results/README.md).

| Scenario | Check |
| --- | --- |
| independent | Two known document IDs can be read independently; parallel and multi should both benefit |
| dependency | Read the unique search result; only multi can bind its ID within the batch |
| ambiguous | Multiple candidates require clarification, not arbitrary selection |
| failure | Missing evidence requires handling, not an invented answer |

The first two cases are scored against independently written exact answers. The latter two check that the workflow requests user input; they do not assess the quality of the question. Success means expected fixture behavior, not a general benchmark accuracy score.

## Real-model fixture evaluation

~~~sh
python -m react_m evaluate --model YOUR_MODEL --repeats 3 --output results/local/live.json
~~~

All modes use the same model, fixture data, tool descriptions and execution implementation. The mode restriction is explicit in the prompt and enforced by the Agent. Expected answers are held by the evaluator and not passed to the reasoner.

The four included fixtures are too small to establish real-world quality or statistical significance. The command is a smoke-test harness for collecting genuine model traces; it is not a reproduction of the original ReAct experiments.

## Baselines

- **Single**: one action per decision.
- **Parallel**: multiple independent actions, no references to results in the same batch.
- **Multi**: independent actions plus deterministic result bindings and explicit dependencies.

Ordinary parallelism is a strong baseline for independent tasks. A reduction against Single alone does not prove an advantage over existing parallel tool calling.

Keep tools and environments fixed. A stateless document-ID interface must not be given only to Multi while another mode is forced to use shared current-page state. Compare the same tasks and enough common budget for every mode to finish.

## Recorded evidence

Run traces include mode, backend, task identifier, outcomes, decisions, observations, tool attempts, elapsed time, model request count and provider token usage where available. Rejected model outputs and exhausted runs count; failures are retained. Summary tables include all runs, success rate, median wall time and mean request/attempt counts.

The initial implementation does not estimate dollar cost, confidence intervals or P95 from five tiny repetitions. Future substantial experiments should add paired task comparisons, randomized live run order, provider/model revision metadata, dataset versions, uncertainty intervals and representative sample sizes. Inspect successful-task latency separately while retaining all failures in the primary report.

## What has and has not been established

The included tests and sample validate dependency execution, checks, failure isolation and expected scripted decision counts. They do not demonstrate that a model can reliably produce those batches, or that fewer rounds outweigh longer prompts and speculative actions.

No live-model result has been established in the initial development environment because no model credentials are configured. If a real-model evaluation is later run, publish the exact configuration, raw traces where appropriate, and observed limitations before making performance claims.
