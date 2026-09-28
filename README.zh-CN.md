# ReAct-M

[![Tests](https://github.com/Buktal/ReAct-M/actions/workflows/tests.yml/badge.svg)](https://github.com/Buktal/ReAct-M/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/Buktal/ReAct-M)](https://github.com/Buktal/ReAct-M/releases)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**每轮推理，执行多个动作。**

[English](README.md) · [Notebook](ReAct-M.ipynb)

ReAct-M 是一个支持多动作批次的 Python ReAct 实现。每轮推理可以生成多个工具调用：独立动作并发执行，有依赖的动作直接引用上游结果。执行结果作为观察，进入下一轮推理。

~~~text
                   ┌─ 搜索 A → 读取 A ─┐
任务 → 推理 ───────┤                  ├─ 观察 → 推理 → 回答
                   └─ 搜索 B → 读取 B ─┘
~~~

## 功能

- **动作批次**：支持显式依赖和 JSON 结果引用。
- **并发执行**：支持并发上限、共享资源互斥和操作顺序约束。
- **迭代推理**：需要根据新信息做判断时，进入下一轮推理。
- **异常处理**：保留部分结果，阻止失败分支的后续动作，支持超时和安全重试。
- **模型接入**：兼容可配置的 Chat Completions 接口。
- **示例与实验**：提供 Wikipedia 工具、离线示例和三种执行模式。

## 快速开始

需要 Python 3.11 或更新版本。

从 [GitHub Releases](https://github.com/Buktal/ReAct-M/releases) 安装已发布版本：

~~~sh
python -m pip install https://github.com/Buktal/ReAct-M/releases/download/v0.1.0/react_m-0.1.0-py3-none-any.whl
python -m react_m demo --scenario dependency
~~~

如需使用 Notebook 或查看源码：

~~~sh
git clone https://github.com/Buktal/ReAct-M.git
cd ReAct-M
python -m venv .venv
~~~

在 PowerShell 中运行 `.venv\Scripts\Activate.ps1` 激活环境；macOS/Linux 使用 `source .venv/bin/activate`。随后执行：

~~~sh
python -m pip install -e .
python -m react_m demo --scenario dependency
~~~

离线示例使用预设决策和内置合成文档，无需 API 密钥。可用 `--scenario independent|dependency|ambiguous|failure` 选择场景，也可以打开 [Notebook](ReAct-M.ipynb)。

安装后的 `react-m` 命令与 `python -m react_m` 等价。

## 接入模型

设置 API 密钥和模型名称。例如，在 PowerShell 中运行：

~~~powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "your-model-id"
python -m react_m ask "Nicholas Ray 和 Elia Kazan 有哪些共同的职业？"
~~~

`ask` 命令搜索并读取 Wikipedia，在执行轨迹中保留来源链接，结果默认保存到 `results/local/question.json`。

| 配置 | 用途 |
| --- | --- |
| `OPENAI_MODEL` 或 `--model` | 模型名称 |
| `OPENAI_API_KEY` | API 密钥 |
| `OPENAI_BASE_URL` 或 `--base-url` | API 基础地址，默认为 `https://api.openai.com/v1` |
| `REACT_M_API_KEY` | 可选，覆盖 `OPENAI_API_KEY` |
| `--no-json-mode` | 为不支持 JSON-object 模式的接口关闭该模式 |

接口需支持 Chat Completions 和 `max_completion_tokens` 参数。Wikipedia 查询需要联网。

## 动作批次

后续动作可以直接从上游结果中获取参数：

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

这里的 `read` 会接收唯一搜索结果的 ID。如果搜索返回零个或多个匹配，`select: only` 会产生 `needs_reasoning`，由下一轮推理处理歧义。

| 动作字段 | 含义 |
| --- | --- |
| `id`、`tool` | 唯一动作 ID 与已注册的工具名称 |
| `args` | 直接给定的参数 |
| `bindings` | 从同一批次中其他动作的结果获取参数 |
| `depends_on` | 必须先成功执行的动作，不传递数据 |

结果引用使用 RFC 6901 JSON Pointer，并自动建立依赖。Engine 在执行前校验依赖图，在调用工具前校验绑定后的参数。失败或存在歧义的动作会阻止其后续依赖动作，无关分支仍可继续。

模型每轮返回一个决策对象：`{"type": "execute", "actions": [...]}`、`{"type": "finish", "answer": "..."}` 或 `{"type": "ask_user", "question": "..."}`。对应 Schema 可从 `react_m.agent.DECISION_SCHEMA` 和 `react_m.protocol.BATCH_SCHEMA` 获取。

## Python API

为异步工具注册参数 Schema，然后执行动作批次：

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

`Agent(engine, reasoner).run(task)` 提供推理循环。`react_m.providers` 中的 `ChatCompletionsReasoner` 用于接入模型；`ScriptedReasoner` 为示例提供预设决策。

工具须返回可序列化为 JSON 的值，并配合异步取消。工具配置包括 `timeout`、`retries`、`retry_safe`、`read_only` 和共享 `resource`；需要明确操作顺序的资源使用 `ordered=True`。只有明确可重复执行的只读操作才能自动重试，外部写操作不支持自动重试。执行结果无法确认时会返回 `outcome_unknown` 并停止派发后续动作；调用方须先核实外部状态，再创建新的 Engine。

默认每批最多 32 个动作、四个工具并发、批次超时 30 秒、最多八轮推理。执行限制可通过 `Engine`、`Tool` 和 `Agent` 参数配置；每批动作数量上限由 Schema 固定。

## 比较执行模式

| 模式 | 每轮动作 | 批次内引用结果 |
| --- | --- | --- |
| `single` | 一个动作 | 不支持 |
| `parallel` | 多个独立动作 | 不支持 |
| `multi` | 多个独立或有依赖的动作 | 支持 |

运行离线对照，或使用已配置的模型评估同一组案例：

~~~sh
python -m react_m compare --repeats 5 --output results/local/mechanics.json
python -m react_m evaluate --output results/local/live.json
~~~

`compare` 使用预设决策与可配置延迟测量执行机制；`evaluate` 在相同的四组案例上记录模型响应、工具调用、可获取的 token 用量和任务结果。独立读取验证并发，搜索后读取验证参数传递，歧义与缺失证据验证澄清流程。

[示例结果](results/README.md) 展示执行机制，其成功率表示预设案例是否得到期望结果；真实模型的速度和回答质量需要模型实验验证。批次执行可以减少机械传参产生的推理往返，但更大的批次也可能增加无效调用或延迟反馈。

## 参与贡献

开发环境与检查命令见 [CONTRIBUTING.md](CONTRIBUTING.md)。Bug、功能建议和使用问题可提交到 [GitHub Issues](https://github.com/Buktal/ReAct-M/issues/new/choose)。参与者须遵守[行为准则](CODE_OF_CONDUCT.md)。

安全漏洞请通过 [SECURITY.md](SECURITY.md) 中的私密渠道报告。版本变化见[更新日志](CHANGELOG.md)。

## 致谢

参考 Yao 等人的 [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)，ICLR 2023。原始实现见 [ReAct 仓库](https://github.com/ysymyth/ReAct)。

相关工作还包括将规划与依赖观察的执行分开的 [ReWOO](https://arxiv.org/abs/2305.18323)，以及通过并行执行器协调有依赖工具调用的 [LLMCompiler](https://arxiv.org/abs/2312.04511)。

## 许可证

[MIT](LICENSE)。
