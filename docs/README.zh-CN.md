# ReAct-M

目标是一个参考原版 [ReAct](https://github.com/ysymyth/ReAct) 风格的开源研究仓库：实现小而清楚、示例能运行、实验可复现。

ReAct-M 将每轮的单个动作扩展为动作批次。独立动作可并行；动作已确定、仅需要上游参数时，由运行时直接传递；需要理解新观察才能选择下一步时，再进入下一轮推理。

## 运行

需要 Python 3.11 或更新版本。在项目目录创建并激活虚拟环境后运行：

```sh
python -m pip install -e ".[dev]"
python -m react_m demo --scenario dependency
python -m react_m compare --repeats 5 --output results/local/mechanics.json
```

演示包括 independent、dependency、ambiguous、failure 四种场景，以及 single、parallel、multi 三种模式。[Notebook](../ReAct-M.ipynb) 使用同一组实验函数。

**离线演示使用手写计划与虚构文档，不调用大模型。它验证运行机制，不证明真实模型的效果。**

## 接入真实模型

在本地设置 OPENAI_API_KEY 和 OPENAI_MODEL，再运行：

```sh
python -m react_m evaluate --output results/local/live.json
python -m react_m ask "Nicholas Ray 和 Elia Kazan 有哪些共同的职业？"
```

支持通过 OPENAI_BASE_URL 配置兼容 Chat Completions 的接口，通过 REACT_M_API_KEY 覆盖密钥。模型名称需要自行指定；不支持 JSON-object 模式的接口可使用 --no-json-mode。接口需支持 max_completion_tokens。此命令可能产生 API 费用，请勿提交密钥或私有输出。

ask 命令使用只读 Wikipedia 搜索与页面读取工具处理自定义问题，并在轨迹中保留来源链接；它需要联网。页面采用明确的 ID，较长正文会标注截断，接口不同于原版的共享当前页面。完整问答效果仍需实际模型接入后验证。

## 如何看待这个思路

这个方向有工程价值，但多工具规划、减少推理往返和并发执行已有 ReWOO、LLMCompiler 等相关研究。本仓库提供一个可阅读、可实验的实现，不宣称首创或领先这些系统。

已跑通的[机制实验](../results/README.md)符合预期：独立查询的收益大部分来自普通并行；依赖传参可减少一次中间决策；歧义与失败仍要处理。真实模型是否也能降低成本、保持准确率，还需要真实模型与更大任务集验证。当前没有已验证的真实模型基准结果。

## 范围

包含批次协议、参数引用、依赖检查、有限并发、资源顺序、失败隔离、Agent 循环、模型接入、测试和实验入口。Jev 留作可选扩展，当前没有训练或接入专门路由模型。

这是初版研究实现。工具必须是可信且配合取消的异步函数；它不提供分布式锁、事务回滚、真实退款保证或任意代码沙箱。

详细信息见[主 README](../README.md)、[协议](PROTOCOL.md)、[设计](DESIGN.md)、[评估方法](EVALUATION.md)和[相关工作](RELATED_WORK.md)。项目采用 MIT 许可证。
