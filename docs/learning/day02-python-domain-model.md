---
title: Day 2｜Python 工程基础与领域模型
date: 2026-07-22
project: Personal AI Workspace
module: AI Interview Learning Agent
stage: Phase 1 - Building AI Applications
status: completed
tags:
  - Python
  - venv
  - dataclass
  - Enum
  - type-hints
  - exception-handling
  - domain-model
  - Git
---

# Day 2｜Python 工程基础与领域模型

## 1. 今日目标

今天没有直接进入 FastAPI、LLM 或 Agent，而是先使用 Python 标准库实现一个内存版知识笔记管理器。

这样安排的目的，是先建立一个不依赖 HTTP、数据库和大模型的业务核心：

```text
终端入口
→ NoteManager 业务逻辑
→ Note 领域对象
→ 内存字典存储
```

明天接入 FastAPI 时，可以把入口替换为 HTTP API，而不需要重写笔记管理逻辑。

---

## 2. 今日完成情况

- [x] 确认 Python 版本：Python 3.13.14
- [x] 创建并激活项目虚拟环境 `.venv`
- [x] 确认当前解释器来自项目虚拟环境
- [x] 创建 `app/domain` 领域模块
- [x] 定义 `Note` 数据模型
- [x] 定义 `MasteryLevel` 掌握程度枚举
- [x] 定义领域异常
- [x] 实现内存版 `NoteManager`
- [x] 实现 CLI 演示入口
- [x] 验证创建、查询、筛选、更新和删除
- [x] 验证三个异常场景
- [x] 恢复正常程序并再次运行
- [x] 完成 Git 提交并推送 GitHub

---

# 3. Python 虚拟环境

## 3.1 创建虚拟环境

```powershell
python -m venv .venv
```

项目目录下会生成一个独立 Python 环境：

```text
.venv/
├── Scripts/
├── Lib/
└── pyvenv.cfg
```

激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

激活后，PowerShell 前缀显示：

```text
(.venv)
```

检查当前解释器：

```powershell
python -c "import sys; print(sys.executable)"
```

实际输出指向：

```text
...i-interview-agent-day1\.venv\Scripts\python.exe
```

这说明后续安装的 FastAPI、pytest、Pydantic 等依赖只属于当前项目，不会污染全局 Python 环境。

## 3.2 为什么需要虚拟环境

不同项目可能需要不同版本的依赖：

```text
项目 A → FastAPI 0.x
项目 B → FastAPI 1.x
```

如果全部安装到全局环境，容易产生版本冲突。虚拟环境通过“每个项目一套依赖”解决这个问题。

## 3.3 Git 中不提交 `.venv`

`.venv`：

- 文件数量多；
- 与操作系统和本机路径相关；
- 可以根据依赖清单重新创建；
- 不应该进入版本管理。

因此 `.gitignore` 中包含：

```gitignore
.venv/
```

---

# 4. 当前项目结构

```text
app/
├── __init__.py
├── cli.py
└── domain/
    ├── __init__.py
    ├── models.py
    ├── exceptions.py
    └── note_manager.py
```

各模块职责：

| 模块 | 职责 |
|---|---|
| `app/__init__.py` | 将 `app` 标记为 Python 包 |
| `app/cli.py` | 命令行入口、调用业务逻辑并显示结果 |
| `domain/models.py` | 定义系统中的领域数据对象 |
| `domain/exceptions.py` | 定义有明确业务语义的异常 |
| `domain/note_manager.py` | 实现笔记创建、查询、筛选、更新和删除 |
| `tests/` | 后续存放自动化测试 |

当前整体数据流：

```text
cli.py
  ↓
NoteManager
  ↓
Note / MasteryLevel
  ↓
dict[int, Note]
```

---

# 5. Python 包、模块与运行方式

## 5.1 模块

一个 `.py` 文件就是一个 Python 模块，例如：

```text
models.py
note_manager.py
cli.py
```

## 5.2 包

包含 Python 模块的目录可以组织为包，例如：

```text
app
app.domain
```

`__init__.py` 用于明确包结构。

因此可以使用绝对导入：

```python
from app.domain.models import Note
from app.domain.note_manager import NoteManager
```

## 5.3 为什么使用 `python -m app.cli`

执行：

```powershell
python -m app.cli
```

表示：

> 从项目根目录，以模块方式运行 `app.cli`。

相比：

```powershell
python app/cli.py
```

模块方式能保持稳定的包导入路径，减少 `ModuleNotFoundError`。

---

# 6. 领域模型 `Note`

`Note` 表示一条面试学习笔记。

```python
@dataclass(slots=True)
class Note:
    id: int
    title: str
    category: str
    content: str
    mastery_level: MasteryLevel = MasteryLevel.NEW
```

字段含义：

| 字段 | 含义 |
|---|---|
| `id` | 笔记唯一标识，未来对应数据库主键 |
| `title` | 知识点标题 |
| `category` | 算法、计网、MySQL 等分类 |
| `content` | 知识点正文 |
| `mastery_level` | 当前掌握程度 |

示例：

```python
Note(
    id=1,
    title="TCP three-way handshake",
    category="computer-network",
    content="The handshake synchronizes sequence numbers...",
)
```

---

# 7. `dataclass` 的作用

如果不使用 `dataclass`，需要手动编写初始化方法：

```python
class Note:
    def __init__(
        self,
        id: int,
        title: str,
        category: str,
        content: str,
    ) -> None:
        self.id = id
        self.title = title
        self.category = category
        self.content = content
```

使用：

```python
@dataclass
```

Python 可以自动生成：

- `__init__`
- `__repr__`
- `__eq__`

因此，`dataclass` 适合“主要职责是承载结构化数据”的对象。

`Note` 不只是一个松散字典，而是一个字段和类型明确的领域对象。

---

# 8. `slots=True`

```python
@dataclass(slots=True)
```

`slots=True` 限制对象只能拥有已经声明的属性。

例如下面的拼写错误会更容易被发现：

```python
note.master_level = MasteryLevel.MASTERED
```

真正字段是：

```python
note.mastery_level
```

没有 `slots=True` 时，Python 可能悄悄创建一个新属性 `master_level`，而原来的 `mastery_level` 完全没有被更新。

因此本项目使用 `slots=True` 的主要意图是：

> 让领域对象结构更严格，及时发现字段拼写错误。

---

# 9. `__post_init__` 与对象不变量

`dataclass` 自动完成初始化后会调用：

```python
def __post_init__(self) -> None:
    ...
```

当前实现负责两类工作。

## 9.1 标准化数据

```python
self.title = self.title.strip()
self.category = self.category.strip()
self.content = self.content.strip()
```

将：

```text
"  TCP handshake  "
```

转为：

```text
"TCP handshake"
```

## 9.2 拒绝非法对象

```python
if not self.title:
    raise ValueError("title cannot be empty")
```

类似规则还包括：

- 分类不能为空；
- 内容不能为空。

设计目的：

> 一个 `Note` 对象一旦创建成功，就应始终满足最基本的合法性规则。

这类始终成立的规则称为对象不变量。

---

# 10. 掌握程度枚举

```python
class MasteryLevel(str, Enum):
    NEW = "new"
    LEARNING = "learning"
    FAMILIAR = "familiar"
    MASTERED = "mastered"
```

## 10.1 为什么不用任意字符串

普通字符串允许出现大量不一致状态：

```python
"Learning"
"learn"
"almost mastered"
"差不多会了"
"masterd"
```

枚举将合法值限定为：

```text
new
learning
familiar
mastered
```

这能为后续功能提供统一协议：

- FastAPI 参数校验；
- JSON 序列化；
- 数据库存储；
- Tool Calling Schema；
- 前端下拉选项；
- 学习数据统计。

## 10.2 `name` 和 `value`

```python
MasteryLevel.NEW.name
# "NEW"

MasteryLevel.NEW.value
# "new"
```

左侧名称主要给代码使用，右侧值主要给 API、JSON 和数据库使用。

## 10.3 为什么继承 `str`

继承 `str` 后，枚举成员同时具有：

- 有限状态的枚举身份；
- 适合 API 和 JSON 的字符串性质。

内部代码可以使用：

```python
MasteryLevel.NEW
```

对外可以表现为：

```json
"new"
```

---

# 11. Python 类型注解

示例：

```python
def get_note(note_id: int) -> Note:
    ...
```

以及：

```python
self._notes: dict[int, Note] = {}
```

类型注解的作用包括：

- 帮助人阅读代码；
- 提供 IDE 自动补全；
- 支持静态类型检查；
- 明确函数输入和输出；
- 为后续 FastAPI/Pydantic Schema 奠定基础。

但 Python 类型注解通常不会自动在运行时阻止错误类型。

例如：

```python
def add(a: int, b: int) -> int:
    return a + b
```

在没有额外校验时，Python 仍可能接受字符串。

因此要区分：

```text
类型注解 → 开发阶段的表达与检查
Pydantic → API 请求到达时的运行时验证
```

---

# 12. 领域异常

当前异常层次：

```python
class NoteError(Exception):
    pass


class NoteNotFoundError(NoteError):
    pass


class DuplicateNoteError(NoteError):
    pass
```

## 12.1 为什么定义 `NoteError`

`NoteError` 是所有笔记业务异常的共同基类。

调用方可以统一处理：

```python
except NoteError as error:
    ...
```

同时仍可以按具体异常区分：

```python
except NoteNotFoundError:
    ...

except DuplicateNoteError:
    ...
```

## 12.2 领域异常与底层异常

字典查找不存在的 key 会产生：

```text
KeyError
```

但对项目用户而言，更清晰的表达是：

```text
指定笔记不存在
```

因此 `get_note` 将底层异常转换为：

```python
NoteNotFoundError
```

未来 FastAPI 可以继续将其转换为：

```text
HTTP 404 Not Found
```

完整转换链：

```text
dict KeyError
→ NoteNotFoundError
→ HTTP 404
```

每一层使用自己能够理解的语言。

## 12.3 `raise ... from error`

```python
raise NoteNotFoundError(...) from error
```

它保留原始异常链：

```text
底层原因：KeyError
业务结果：NoteNotFoundError
```

这样既能向上层提供清晰语义，又不会丢失调试信息。

---

# 13. `NoteManager` 的职责

`NoteManager` 是当前项目的业务逻辑核心。

它负责：

- 创建笔记；
- 查询全部笔记；
- 按分类筛选；
- 按掌握程度筛选；
- 按 ID 查询；
- 更新掌握程度；
- 删除笔记；
- 检查重复标题。

它当前使用：

```python
self._notes: dict[int, Note] = {}
```

模拟数据库。

## 13.1 `_notes`

字典结构：

```text
ID → Note
```

示例：

```python
{
    1: Note(...),
    2: Note(...),
}
```

## 13.2 `_next_id`

```python
self._next_id = 1
```

模拟数据库中的自增主键。

每创建一条笔记：

```python
self._next_id += 1
```

---

# 14. `create_note`

主要流程：

```text
标准化并检查标题
→ 判断是否重复
→ 创建 Note
→ Note 自身验证字段
→ 保存到字典
→ ID 自增
→ 返回创建结果
```

参数中的 `*`：

```python
def create_note(self, *, title: str, category: str, ...)
```

表示调用时必须明确写参数名：

```python
manager.create_note(
    title="TCP",
    category="network",
    content="...",
)
```

这样可以减少多个字符串参数顺序写错的问题。

---

# 15. `list_notes`

支持：

```python
manager.list_notes()
```

返回全部笔记。

也支持：

```python
manager.list_notes(category="computer-network")
```

以及：

```python
manager.list_notes(
    mastery_level=MasteryLevel.LEARNING,
)
```

参数类型：

```python
category: str | None = None
```

表示它可以是字符串，也可以是 `None`。

分类筛选前会执行：

```python
category.strip().lower()
```

因此：

```text
"MySQL"
"mysql"
" mysql "
```

可以被统一处理。

当前实现需要遍历全部内存数据。以后使用数据库时，会转为带条件的 SQL 查询。

---

# 16. `get_note`

```python
def get_note(self, note_id: int) -> Note:
    try:
        return self._notes[note_id]
    except KeyError as error:
        raise NoteNotFoundError(...) from error
```

它承担两个职责：

1. 按 ID 返回笔记；
2. 将底层 `KeyError` 转换为领域异常。

其他操作可以复用它，例如：

```python
note = self.get_note(note_id)
```

这样“检查笔记是否存在”的逻辑不需要重复编写。

---

# 17. `update_mastery`

```python
note = self.get_note(note_id)
note.mastery_level = mastery_level
return note
```

先复用 `get_note` 检查笔记是否存在，再更新掌握程度。

返回更新后的对象，方便 API 或 CLI 立即展示更新结果。

---

# 18. `delete_note`

```python
self.get_note(note_id)
del self._notes[note_id]
```

先检查存在，再执行删除。

如果直接执行：

```python
del self._notes[note_id]
```

不存在时会抛出底层 `KeyError`。

复用 `get_note` 后，可以统一产生：

```text
NoteNotFoundError
```

---

# 19. `_title_exists`

该私有辅助方法负责判断标题是否已经存在。

```python
normalized_title = title.strip().lower()
```

然后通过：

```python
any(...)
```

判断是否至少有一条标题相同的笔记。

因此：

```text
TCP Handshake
tcp handshake
```

会被视为重复。

方法名前的 `_` 表示：

> 这是类内部实现细节，外部代码不应直接依赖它。

---

# 20. CLI 层

`app/cli.py` 是当前的界面层。

它负责：

- 创建 `NoteManager`；
- 准备演示数据；
- 调用业务方法；
- 打印结果；
- 捕获并展示异常。

它不负责：

- 定义笔记是什么；
- 判断标题是否重复；
- 决定删除逻辑；
- 实现存储。

这体现了界面和业务的分离。

## 为什么 `NoteManager` 中不写 `print`

同一个业务核心未来可能服务于：

```text
CLI
FastAPI
网页
自动化测试
Agent Tool
MCP Server
```

如果 `NoteManager` 直接打印，它就会与命令行绑定。

正确方式：

```text
NoteManager 返回对象
→ 不同入口自行决定如何展示
```

CLI 使用文本输出，FastAPI 会使用 JSON。

---

# 21. 三个异常实验

今天主动验证了三个失败场景。

## 21.1 空标题

测试结果：

```text
Operation failed: title cannot be empty
```

验证了：

- `__post_init__` 被正确调用；
- 空白字符串经过 `strip()` 后被识别为空；
- 非法 `Note` 无法进入系统。

## 21.2 重复标题

测试结果：

```text
Operation failed: a note with title 'TCP three-way handshake' already exists
```

验证了：

- `_title_exists` 正常；
- `DuplicateNoteError` 正常；
- 重复数据在创建阶段被阻止。

## 21.3 删除不存在的 ID

测试结果：

```text
Operation failed: note with id 999 was not found
```

验证了：

- 底层 `KeyError` 被转换；
- `NoteNotFoundError` 能被 CLI 捕获；
- 用户不会直接看到字典实现细节。

## 21.4 恢复正常代码

异常实验完成后，恢复正常程序并再次运行。

正常路径成功完成：

```text
创建
→ 列出全部
→ 更新掌握程度
→ 按分类筛选
→ 删除
→ 显示剩余笔记
```

---

# 22. 当前架构的核心分离

## 22.1 数据与展示分离

```text
Note
≠
print(Note)
```

`Note` 描述数据，CLI 决定显示形式。

## 22.2 业务与入口分离

```text
CLI → NoteManager
```

明天可以替换为：

```text
HTTP API → NoteManager
```

而业务逻辑基本不变。

## 22.3 业务异常与技术异常分离

```text
KeyError
→ NoteNotFoundError
→ CLI 错误信息 / HTTP 404
```

## 22.4 业务与存储分离的准备

当前：

```text
NoteManager → dict
```

未来：

```text
API → Service → Repository → SQLite
```

当前代码还没有完成真正的存储分层，但已经为迁移做好准备。

---

# 23. Git 工作流记录

今天的主要提交流程：

```powershell
git status
git add app .gitignore
git commit -m "feat: add in-memory note domain model and CLI"
git push
```

提交结果：

```text
feat: add in-memory note domain model and CLI
```

Git 的意义不只是同步 GitHub，还包括：

- 查看 AI 修改了哪些内容；
- 将每个功能限定在小范围提交；
- 出错后可以回滚；
- 形成可展示的开发历史；
- 支持后续 Pull Request 和 Code Review。

## 新文件查看 diff 的注意点

未跟踪的新文件不会显示在普通：

```powershell
git diff
```

中。

应先暂存：

```powershell
git add app
git diff --cached
```

这样可以在提交前查看新文件的完整差异。

---

# 24. 当前实现的限制

当前版本只是教学型内存原型，存在以下限制：

1. 程序退出后数据丢失；
2. 只有单进程内存数据；
3. `NoteManager` 同时承担业务和暂时存储；
4. 没有完整更新标题、分类和正文的方法；
5. 没有创建时间和更新时间；
6. 没有分页；
7. 没有并发控制；
8. 没有自动化测试；
9. CLI 是固定演示，不是真正的交互式界面；
10. 标题唯一规则仍然较简单。

这些限制不是今天的失败，而是后续学习入口。

---

# 25. 明天接入 FastAPI 后的变化

当前：

```text
CLI
→ NoteManager
→ Note
→ dict
```

下一阶段：

```text
HTTP 请求
→ FastAPI 路由
→ Pydantic 请求模型
→ NoteManager
→ Note
→ JSON 响应
```

可以基本保留：

- `models.py`
- `exceptions.py`
- `note_manager.py`

新增：

```text
app/main.py
app/api/
app/schemas/
```

这说明今天建立的业务核心不是一次性练习，而是后续 API 的基础。

---

# 26. 今日面试表达

## 为什么先做 CLI，而不是直接上 FastAPI？

> 我先使用标准库完成不依赖框架的领域模型和业务逻辑，使笔记创建、查询、更新和删除能够独立运行。这样接入 FastAPI 时，只需要增加 HTTP 和 Schema 层，不需要把业务逻辑写进路由函数，也便于后续替换存储和编写测试。

## 为什么使用领域异常？

> 字典只会抛出 KeyError，但上层真正关心的是笔记不存在。通过将底层异常转换为 NoteNotFoundError，CLI 可以显示用户可理解的错误，FastAPI 以后也可以映射为 HTTP 404，同时仍保留底层异常链用于调试。

## 为什么使用枚举？

> 掌握程度属于有限状态，不应由任意字符串表示。枚举能统一 API、数据库和业务逻辑中的状态取值，并减少拼写错误。

## 类型注解是否会自动检查运行时类型？

> 通常不会。类型注解主要服务于可读性、IDE 和静态类型检查。后续 FastAPI 会借助 Pydantic 对外部输入进行运行时验证。

---

# 27. 今日总结

今天真正学习的不是几段 Python 语法，而是一个最小业务系统如何被拆分：

```text
models.py
→ 系统中的对象是什么

exceptions.py
→ 业务可能如何失败

note_manager.py
→ 系统允许对对象做什么

cli.py
→ 用户如何调用和观察结果
```

核心工程思想：

> 先建立不依赖 FastAPI、数据库和 LLM 的业务内核，再逐层增加外部能力。

这种结构能够让系统从 CLI 自然演化到：

```text
FastAPI
→ SQLite
→ LLM
→ Tool Calling
→ Agent
→ Personal AI Workspace
```

而不是每增加一个技术就重写整个项目。

---

# 28. 下一步

下一阶段进入：

> FastAPI、REST API、Pydantic 与 HTTP 状态码

重点问题：

- HTTP 请求如何映射到 Python 函数？
- Pydantic 如何验证输入？
- 领域异常如何映射为 404 和 409？
- `Note` 领域对象与 API Schema 有什么区别？
- 为什么不应该把全部业务逻辑写进路由函数？
