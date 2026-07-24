# AI Interview Learning Agent

面向算法与计算机基础复习的 AI 面试学习系统。

## 当前阶段

Day 1：项目立项与范围冻结。

## 两周目标

- 使用 FastAPI 提供知识笔记与复习任务 API
- 接入兼容 OpenAI 协议的 LLM
- 支持普通响应与 SSE 流式输出
- 实现受控的 Tool Calling
- 实现简化 ReAct Agent Runner
- 实现短期窗口、摘要压缩和最小 RAG
- 使用 pytest 验证核心接口和错误路径
- 部署到 Ubuntu VPS
- 形成可用于简历和面试的工程记录

## 开发原则

1. 每次只实现一个明确功能。
2. AI 修改代码前必须先给出计划。
3. 修改后检查 Git diff。
4. 核心功能必须有测试。
5. 不写入无法解释的简历内容。

## 当前阶段
## 当前阶段

Day 9：受控 Agent Runner。

已完成：

- Native Tool Calling
- Tool Registry 与参数验证
- 多轮工具调用循环
- 工具结果回传模型
- 最大执行步数
- 重复工具调用保护
- Agent 执行步骤记录
- FastAPI REST API
- Pydantic 输入输出校验
- SQLite 持久化
- SQLAlchemy Repository
- 兼容 OpenAI 协议的 LLM Client
- 结构化面试问题生成
- SSE 流式输出
- 首 Token 延迟与总耗时记录
- API、Service、数据库和 SSE 自动化测试
