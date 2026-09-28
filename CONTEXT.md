# ReAct-M

ReAct-M is an open-source research implementation of iterative reasoning with action batches.

## Language

**ReAct-M**:
The project and overall approach: one reasoning round can arrange multiple actions, followed by observations and further reasoning.
_Avoid_: MultiAct, ReActs, ReAct+

**Action Batch**:
A finite group of actions chosen from current information, with any required success and data dependencies.
_Avoid_: complete task plan, guaranteed parallel actions

**ReAct-M Engine**:
The module responsible for executing an action batch and collecting its observations.
_Avoid_: using DAG Executor to name the whole project

**Decision Dependency**:
A choice of subsequent action that requires interpreting new information.
_Avoid_: treating every dependency as parameter transfer

**Data Dependency**:
A known action's need for a value returned by another action.
_Avoid_: a new reasoning step when deterministic transfer is sufficient

**Jev**:
An optional future tool-routing implementation; the initial release does not include a trained Jev model.
_Avoid_: required reasoning model, LLM replacement
