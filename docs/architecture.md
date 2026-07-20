# 初步架构

## 组件

1. API 层：接收 HTTP 请求并校验输入。
2. Service 层：承载业务逻辑。
3. Data 层：SQLite 数据持久化。
4. LLM Client：统一封装模型调用。
5. Agent Runner：负责工具选择、执行循环和停止条件。
6. Memory：管理最近消息、摘要和检索结果。
7. Tool Registry：保存允许调用的工具及其 Schema。
8. Tests：验证正常路径和异常路径。

## 初步数据流

用户请求 → FastAPI 路由 → Pydantic 校验 → Service → LLM / Agent Runner → Tool Registry 或 Memory → 结构化结果 → API 响应

## 核心约束

- 模型只生成工具调用意图，不直接访问数据库。
- 后端负责参数校验和真实执行。
- Agent 必须有最大轮数。
- 工具必须采用白名单。
- 不记录或展示模型隐藏推理过程，只记录工具调用与结果。
