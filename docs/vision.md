---
title: Personal AI Workspace 长期愿景
document_type: repository-vision
status: active
version: 0.1
created_at: 2026-07-20
review_cycle: monthly
---

# Personal AI Workspace 长期愿景

## 1. 文档目的

本文档定义本仓库的长期方向、系统边界、演化原则和阶段路线。

它不是当前迭代的需求清单，也不要求一次性实现完整架构。它用于：

- 说明仓库最终希望解决什么问题；
- 统一后续模块的设计语言；
- 判断新功能是否值得加入；
- 避免项目退化为一次性 Demo；
- 避免为了长期愿景而过度设计；
- 为长期维护、简历和面试提供一致叙事。

当前两周仍以 **AI Interview Learning Agent** 为交付目标。它是 Personal AI Workspace 的第一个正式模块，而不是整个系统的最终形态。

## 2. 项目愿景

### 一句话定义

> Personal AI Workspace 是一个面向个人长期学习、研究、决策和自动化任务的模块化 AI 工作空间。

它将知识库、记忆、Prompt、工具、Agent Runtime、任务调度、评估、可观测性和用户界面组织成一个可持续演化的系统。

### 长期目标

系统最终应支持：

- 保存和检索个人知识；
- 管理跨会话的长期上下文；
- 运行不同领域的 AI Agent；
- 让 Agent 安全调用本地或远程工具；
- 编排可重复执行的工作流；
- 记录任务过程、工具调用、错误和结果；
- 对 Agent 输出进行评估和审计；
- 通过 API、CLI 和 Dashboard 访问系统；
- 允许新模块复用公共基础设施；
- 在本地设备、VPS 或云端持续运行。

### 希望形成的个人能力

> 擅长构建可运行、可解释、可扩展和可审查的 AI Agent 系统。

重点不是只掌握某个框架，而是理解 AI 系统中不同层次的职责、边界和协作方式。

## 3. 核心定位

Personal AI Workspace 同时具备三种属性。

### AI Application

面向真实用户任务提供功能，例如：

- 面试学习；
- 技术学习；
- 英语学习；
- 市场研究；
- 旅行规划；
- 个人知识问答。

### AI Infrastructure

提供所有模块共享的基础能力，例如：

- 模型调用；
- 上下文管理；
- 长期记忆；
- Tool Registry；
- Agent Runtime；
- 任务调度；
- 评估与日志；
- 权限与安全控制。

### AI Product

最终需要具备可使用的产品形态：

- 清晰的用户流程；
- 可理解的结果；
- 失败提示与恢复路径；
- 可配置模块；
- API、CLI 或 Dashboard；
- 可以长期使用，而不只是用于演示。

## 4. 设计原则

### 4.1 先完成垂直切片，再抽象公共能力

错误方式：

> 先设计完整 AI OS，再寻找使用场景。

推荐方式：

> 先完成 Interview Module，再从实际重复中提取 LLM Client、Memory、Tool Registry 和 Agent Runtime。

### 4.2 系统优先于框架

学习任何框架时，必须回答：

- 它位于系统哪一层？
- 它解决什么问题？
- 不使用它时，最小实现是什么？
- 它隐藏了哪些关键机制？
- 替换它的成本是什么？

LangChain、LlamaIndex、Dify、Coze 等工具可以使用，但不能替代底层理解。

### 4.3 模型负责建议，系统负责执行

模型可以：

- 生成回答；
- 选择工具；
- 生成结构化参数；
- 提议执行计划。

后端必须负责：

- 参数验证；
- 权限检查；
- 工具白名单；
- 超时控制；
- 重试策略；
- 幂等性；
- 执行日志；
- 最终状态确认。

### 4.4 默认可观察、可测试、可回滚

新增能力应优先具备：

- 明确输入和输出；
- 结构化日志；
- 错误分类；
- 自动化测试；
- Git 历史；
- 配置与密钥隔离；
- 回滚或恢复方式。

### 4.5 小步演化

每次迭代尽量满足：

- 一个明确目标；
- 一个有限修改范围；
- 一组验收标准；
- 一次测试和审查；
- 一个可回滚提交。

### 4.6 真实完成优于功能清单

README、简历和演示只描述实际实现并能够解释的内容。

## 5. 概念架构

```text
┌──────────────────────────────────────────────┐
│ Presentation Layer                           │
│ Dashboard / Web / CLI / API Clients          │
├──────────────────────────────────────────────┤
│ Domain Modules                               │
│ Interview / Learning / Markets / Travel ...  │
├──────────────────────────────────────────────┤
│ Workflow & Agent Layer                       │
│ Agent Runtime / Planner / Executor / Jobs    │
├──────────────────────────────────────────────┤
│ Context & Knowledge Layer                    │
│ Memory / RAG / Knowledge Base / Summaries    │
├──────────────────────────────────────────────┤
│ Tool & Integration Layer                     │
│ Tool Registry / MCP / Connectors / Actions   │
├──────────────────────────────────────────────┤
│ Model Layer                                  │
│ LLM Client / Routing / Streaming / Retry     │
├──────────────────────────────────────────────┤
│ Platform Layer                               │
│ Storage / Queue / Logging / Auth / Config    │
├──────────────────────────────────────────────┤
│ Infrastructure Layer                         │
│ Local Machine / VPS / Cloud / Containers     │
└──────────────────────────────────────────────┘
```

## 6. 各层职责

### Presentation Layer

负责用户与系统交互，包括 Web Dashboard、REST API、CLI、通知和 Markdown 导出。该层不直接实现 Agent 或数据库业务逻辑。

### Domain Modules

每个模块对应一个真实领域任务。候选模块：

- Interview Learning；
- Technology Learning；
- English Growth；
- Global Markets；
- Poker Decision；
- Travel Planning；
- Personal Notes；
- Research Assistant；
- Coding Assistant；
- Quant Research。

模块应复用公共能力，而不是分别复制 LLM、Memory 和 Tool 代码。

### Workflow & Agent Layer

负责将用户目标转化为可执行步骤：

- ReAct Runner；
- Plan-and-Execute；
- Workflow State Machine；
- Scheduler；
- Background Jobs；
- Human Approval；
- Retry and Recovery；
- Agent Evaluation。

### Context & Knowledge Layer

负责决定模型在当前请求中应该看到什么：

- 最近消息窗口；
- 会话摘要；
- 用户偏好；
- 长期记忆；
- Markdown 知识库；
- 向量检索；
- 来源引用；
- Context Budget。

### Tool & Integration Layer

负责将模型连接到外部能力：

- Tool Schema；
- Tool Registry；
- 本地函数；
- 数据库查询；
- Web API；
- 文件系统；
- Connector；
- MCP Client / Server；
- 权限控制；
- 幂等执行。

### Model Layer

负责统一模型访问：

- OpenAI-compatible API；
- 模型配置；
- 流式输出；
- 结构化输出；
- Token 统计；
- 超时；
- 重试；
- 限流；
- Fallback；
- 模型路由；
- 成本记录。

### Platform Layer

负责非 AI 的工程基础：

- SQLite / PostgreSQL；
- 文件存储；
- Redis；
- Task Queue；
- 配置管理；
- Secret Management；
- 日志；
- 指标；
- 身份认证；
- 审计记录。

### Infrastructure Layer

负责实际运行环境：

- Windows 开发环境；
- WSL2；
- Ubuntu VPS；
- Docker；
- CI/CD；
- 备份；
- 监控；
- 多节点部署。

## 7. 第一正式模块：AI Interview Learning Agent

### 模块目标

帮助用户系统学习算法和计算机基础，并通过 AI 完成：

- 知识整理；
- 面试问题生成；
- 回答评价；
- 递进式追问；
- 薄弱项识别；
- 复习任务生成；
- 笔记检索；
- 学习记录沉淀。

### 该模块验证的公共能力

| 业务功能 | 验证的系统能力 |
|---|---|
| 生成面试问题 | LLM Client、Prompt、结构化输出 |
| 流式回答 | Streaming |
| 搜索笔记 | Tool Calling、Knowledge Retrieval |
| 更新掌握程度 | Tool Schema、参数验证、数据库写入 |
| 创建复习任务 | Agent Loop、幂等性 |
| 多轮追问 | Context Window |
| 历史压缩 | Summary Memory |
| 基于笔记回答 | RAG |
| 接入外部客户端 | MCP |

### 当前阶段边界

当前两周只实现最小垂直切片：

- FastAPI；
- SQLite；
- 笔记 CRUD；
- LLM 调用；
- SSE；
- 三个工具；
- 简化 ReAct；
- 最近消息与摘要；
- 最小 Markdown RAG；
- pytest；
- VPS 部署。

暂不包括：

- 复杂前端；
- 多用户；
- 多 Agent；
- 统一 Dashboard；
- 通用工作流编辑器；
- 生产级权限系统；
- 分布式部署。

## 8. 候选长期公共模块

### Knowledge Base

统一管理 Markdown、网页摘录、PDF 笔记、代码片段、项目文档、标签、来源和更新记录。

### Memory

统一管理用户长期偏好、会话摘要、项目决策、Agent 状态、事件记录以及可更新和可遗忘的记忆。

### Prompt Library

统一管理 Prompt 模板、版本、输入变量、输出 Schema、测试用例和评估结果。

### Tool Registry

统一管理工具名称、Schema、权限、超时、重试、幂等性、审计和版本。

### Agent Runtime

统一提供 ReAct、Planner / Executor、状态、最大轮数、中断、恢复、人工审批、执行轨迹和结果评估。

### Scheduler

支持定时任务、条件监控、日报、周报、自动复习、数据采集和通知。

### Observability

支持请求日志、模型耗时、首 Token 延迟、Token 用量、成本、工具成功率、Agent 轮数、错误分类、任务状态和评估得分。

### Dashboard

提供模块入口、任务状态、Agent 运行记录、知识库、复习计划、系统健康状态、配置和审计。

## 9. 阶段路线

### Phase 1：Building AI Applications

目标：掌握一个 AI 应用的完整垂直链路。

内容：

- FastAPI；
- LLM API；
- Structured Output；
- Streaming；
- Tool Calling；
- Memory；
- RAG；
- MCP 基础；
- Testing；
- Deployment。

主要成果：

- AI Interview Learning Agent。

### Phase 2：Building AI Agents

目标：从单次调用升级到可控执行系统。

内容：

- ReAct；
- Plan-and-Execute；
- Workflow；
- State Machine；
- Scheduler；
- Long-term Memory；
- Evaluation；
- Observability；
- Human Approval。

主要成果：

- 可复用 Agent Runtime；
- 第二个领域模块。

### Phase 3：Building AI Systems

目标：形成多模块共享平台。

内容：

- Tool Registry；
- Prompt Library；
- Knowledge Base；
- Task Queue；
- Dashboard；
- Auth；
- Docker；
- CI/CD；
- Monitoring；
- Backup；
- Security。

主要成果：

- Personal AI Workspace MVP。

### Phase 4：Building Autonomous Systems

目标：支持长期运行、条件触发和自动恢复的任务。

候选场景：

- 市场监控；
- 技术简报；
- 学习计划；
- Research Agent；
- Coding Agent；
- Quant Research；
- 系统运维 Agent。

这一阶段必须强化风险边界、权限、审计、幂等、故障恢复和人工干预。

## 10. 仓库演化策略

### 当前阶段：模块化单体

早期采用模块化单体，而不是微服务，因为：

- 开发和调试成本低；
- 容易理解完整数据流；
- 适合个人项目；
- 便于测试和部署；
- 公共能力仍在快速变化。

### 长期目录候选

```text
personal-ai-workspace/
├── app/
│   ├── platform/
│   ├── llm/
│   ├── memory/
│   ├── tools/
│   ├── agents/
│   ├── knowledge/
│   ├── workflows/
│   └── modules/
│       ├── interview/
│       ├── technology/
│       ├── english/
│       └── markets/
├── tests/
├── docs/
├── scripts/
└── deployments/
```

当前不立即重构。只有当第二个真实模块出现并产生明确重复时，才提取公共层。

### 提取公共能力的条件

- 至少两个模块使用；
- 业务语义相同；
- 接口边界稳定；
- 测试能够覆盖；
- 抽象后确实减少重复和耦合。

## 11. 非目标

本项目暂不追求：

- 自研基础模型；
- 模型训练平台；
- 通用 AGI；
- 无限制自治；
- 一开始支持大规模并发；
- 复制所有现有 AI 产品；
- 使用尽可能多的框架；
- 用架构复杂度证明技术能力。

系统价值来自：

> 真实使用、稳定运行、清晰边界、持续演化和能够解释。

## 12. 安全与信任边界

系统未来可能接触私人笔记、邮件、日历、文件、服务器和金融数据，因此必须逐步建立：

- 最小权限；
- 工具白名单；
- 明确确认；
- Secret 隔离；
- 输入验证；
- 输出验证；
- 操作审计；
- 幂等执行；
- 危险操作二次确认；
- 不确定状态不自动重试；
- 数据备份和恢复；
- 用户可删除记忆。

高风险领域不得以“Agent 自主决策”为理由跳过安全控制。

## 13. 工程质量标准

每个正式模块至少应具备：

- README；
- 明确依赖；
- `.env.example`；
- 输入 Schema；
- 错误处理；
- 核心测试；
- 日志；
- Git 历史；
- 架构说明；
- 部署或运行说明；
- 已知限制；
- 后续计划。

关键公共组件还应具备接口文档、故障场景、版本策略、迁移说明以及性能或成本指标。

## 14. 学习组织方式

每学习一个新概念，都记录：

```markdown
## 概念名称

### 它解决什么问题？

### 它属于系统哪一层？

### 最小实现是什么？

### 常见框架如何封装它？

### 失败模式是什么？

### 如何测试？

### 在当前项目中的应用位置是什么？
```

示例：

- FastAPI → Presentation / API Layer
- SQLite → Platform / Storage Layer
- Prompt → Model Layer
- Tool Calling → Tool & Integration Layer
- Memory → Context & Knowledge Layer
- ReAct → Workflow & Agent Layer
- MCP → Tool & Integration / Communication
- Dashboard → Presentation Layer

## 15. 决策记录

重要技术选择应通过 ADR 记录。

```markdown
# ADR-XXX：决策名称

## 背景

## 备选方案

## 最终选择

## 原因

## 代价

## 何时重新评估
```

首批候选 ADR：

- 选择 Python + FastAPI；
- 第一阶段选择 SQLite；
- 采用 OpenAI-compatible LLM Client；
- 初期采用模块化单体；
- 模型不直接执行工具；
- 不记录隐藏推理过程。

## 16. 新功能准入问题

加入新模块或基础设施前，必须回答：

1. 它解决了哪个真实问题？
2. 目前是否存在用户或工作流？
3. 它属于哪一层？
4. 是否已有模块能实现？
5. 是否会重复已有能力？
6. 一个迭代内能否交付垂直切片？
7. 如何测试和观测？
8. 出错后如何恢复？
9. 是否涉及敏感数据或高风险操作？
10. 现在实现是否早于实际需要？

无法清楚回答时，默认不加入。

## 17. 成功标准

### 短期

- Interview Module 可用；
- 能解释完整调用链；
- 能展示测试、日志和 Git 历史；
- 能用于简历和面试；
- 自己愿意继续使用。

### 中期

- 出现第二个真实模块；
- 公共 LLM、Memory 和 Tool 能力被复用；
- 有基础任务调度和可观察性；
- 系统部署稳定；
- 文档可以指导后续开发。

### 长期

- 多个个人 Agent 共享同一基础设施；
- 新模块接入成本明显降低；
- 系统能够长期运行并安全恢复；
- 个人知识和任务形成持续积累；
- 项目体现 AI Application、Infrastructure 和 Product 的统一能力。

## 18. 当前执行原则

长期愿景不能破坏当前迭代。

截至当前阶段：

> 只完成 AI Interview Learning Agent 的最小垂直切片。

只有在以下条件全部满足后，才开始提取 Workspace 公共架构：

- Interview Module 能正常运行；
- 核心接口有测试；
- LLM、Tool Calling、Memory 和 RAG 链路可解释；
- 已有第二个真实模块需求；
- 已观察到明确重复；
- 抽象不会延迟当前交付。

## 19. 当前项目叙事

> 本仓库从 AI Interview Learning Agent 起步，目标是逐步构建一个模块化的 Personal AI Workspace。第一阶段聚焦 FastAPI、LLM 流式调用、Tool Calling、上下文管理、RAG、测试和部署，通过真实学习场景验证完整 AI 应用链路。后续将从实际模块中提取通用的模型访问、记忆、工具注册、Agent Runtime、任务调度与可观测能力，而不是预先构建一个空泛的平台。

## 20. 文档维护

- 每月复查一次愿景与路线；
- 每完成一个阶段更新版本；
- 重大方向变化必须记录原因；
- 已完成能力与候选能力必须区分；
- 不把设想写成已经实现的功能；
- 当前迭代以 `requirements.md` 和 Backlog 为准；
- 本文档只负责长期方向和设计原则。
