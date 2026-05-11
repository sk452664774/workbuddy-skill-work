---
name: work
description: "WorkBuddy 日常工作辅助 Skill，整合 api-doc-server（接口文档管理服务）和 P50 MCP Server（账号/周报/项目/需求管理服务）两大系统的完整操作指南。适用于日常开发工作中查询接口文档、管理项目账号、处理周报、管理需求等场景。"
agent_created: true
---

# Work Skill — 全平台独立工作指令

> **便携设计**：本 skill 可在任何电脑上运行，**不依赖 api-doc-server、不依赖 P50 MCP Server**。
> 仅需要网络能访问目标后端API。

---

## Python 环境说明

> 本 skill 内置了 `scripts/run.sh` 自动检测包装器，会在多台电脑上自动寻找可用的 Python 解释器。
> 所有命令统一使用 `bash <SKILL_DIR>/scripts/run.sh xxx.py` 即可。

## 路径无关说明

**所有脚本路径使用 `SKILL_DIR` 变量**，WorkBuddy 加载 skill 时会自动获取技能目录路径：

```
SKILL_DIR = <WorkBuddy 自动识别的 skill 目录>
   ├── SKILL.md
   └── scripts/
       ├── projects.json         ← 项目→上游OpenAPI地址映射
       ├── query_api.py          ← 接口文档查询（--direct 模式无需 api-doc-server）
       ├── p50_api.py            ← P50 业务API直调（无需 MCP Server）
       ├── run.sh                ← Python 自动检测包装器（跨电脑兼容）
       └── check-services.sh     ← 服务健康检查
```

对 WorkBuddy 的要求：使用 `SKILL_DIR` 变量定位脚本目录，不要硬编码用户路径。

---

## 核心原则

1. **`--direct` 优先** — 默认使用 `--direct` 模式（直连上游/后端，无缓存依赖）
2. **不依赖本地服务** — 接口查询直连 OpenAPI 文档源，业务操作直连后端 API
3. **用具体功能名，不用模块标签** — 查询接口时用"批量下载二维码"而非"人员二维码发放管理"
4. **项目编号模糊匹配** — 用户指定的项目编号可能不完整（如"P48"实际为"P048-B01"），先 `projects list` 全量匹配。匹配 0 个时提示不存在；匹配 1 个时自动选用；**匹配 2 个及以上时询问用户选择**。**禁止直接创建新项目。**
5. **完成即报告** — 每完成一个操作，向用户简要报告结果

---

## 场景 1：查询接口文档

使用 `scripts/query_api.py`，**默认 `--direct` 模式**（无需 api-doc-server）。

### 获取项目列表
```bash
bash <SKILL_DIR>/scripts/run.sh query_api.py --direct projects
```

### 列出项目所有接口
```bash
bash <SKILL_DIR>/scripts/run.sh query_api.py --direct list <项目编号>
```

### 查询接口详情
```bash
# 默认 direct 模式（直连上游 OpenAPI，无缓存）
bash <SKILL_DIR>/scripts/run.sh query_api.py --direct <项目编号> <功能名称>

# 指定模块过滤（同名接口多模块时）
bash <SKILL_DIR>/scripts/run.sh query_api.py --direct <项目编号> <功能名称> --tag "<模块名>"

```

### 下载指定模块接口为 .md 文件
```bash
# 下载到当前工作目录（自动创建以模块名命名的文件夹）
bash <SKILL_DIR>/scripts/run.sh query_api.py --direct download <项目编号> --tag "<模块名>"

# 指定输出目录
bash <SKILL_DIR>/scripts/run.sh query_api.py --direct download <项目编号> --tag "<模块名>" --output "./my_docs"
```

每个接口保存为一个 `.md` 文件，文件名 = 接口 summary，包含方法、路径、参数、请求体、响应结构。

**注意**：download 仅支持 `--direct` 模式（需要上游 API 可达）。

---

**处理不同返回**：
- ✅ 查到 → 输出方法、路径、参数、响应结构
- ⚠️ 多模块 → 提示用 `--tag <模块名>` 指定
- ❌ 没找到 → 换关键词或确认项目编号

**响应格式**：
```
[项目编号] [功能名称] — [方法] [路径]
—— 参数列表：（如果有）
—— 请求体：（如果有）
—— 响应结构：（如果有）
```

---

## 场景 2：管理账号

使用 `scripts/p50_api.py`，**不依赖 MCP Server**。

```bash
# 查询账号列表
bash <SKILL_DIR>/scripts/run.sh p50_api.py accounts list
bash <SKILL_DIR>/scripts/run.sh p50_api.py accounts list --keyword <关键词>

# 创建账号
bash <SKILL_DIR>/scripts/run.sh p50_api.py accounts create <工号> <姓名>
```

---

## 场景 3：管理周报

```bash
# 查询周报
bash <SKILL_DIR>/scripts/run.sh p50_api.py reports list
bash <SKILL_DIR>/scripts/run.sh p50_api.py reports list --employee h2339
bash <SKILL_DIR>/scripts/run.sh p50_api.py reports list --start 2026-04-01 --end 2026-04-30

# 创建周报（参数：工号 开始日期 结束日期 内容）
bash <SKILL_DIR>/scripts/run.sh p50_api.py reports create h2339 2026-04-21 2026-04-27 "本周工作内容..."

# 更新周报
bash <SKILL_DIR>/scripts/run.sh p50_api.py reports update <id> 2026-04-21 2026-04-27 "更新内容"

# 删除周报
bash <SKILL_DIR>/scripts/run.sh p50_api.py reports delete <id>
```

---

## 场景 4：管理项目

```bash
# 查询项目列表
bash <SKILL_DIR>/scripts/run.sh p50_api.py projects list

# 新建项目
bash <SKILL_DIR>/scripts/run.sh p50_api.py projects create P99 "新项目" "项目描述"

# 编辑项目
bash <SKILL_DIR>/scripts/run.sh p50_api.py projects update <id> "新名称" "新描述"

# 删除项目
bash <SKILL_DIR>/scripts/run.sh p50_api.py projects delete <id>
```

---

## 场景 5：管理需求

```bash
# 查所有需求（不指定项目）
bash <SKILL_DIR>/scripts/run.sh p50_api.py requirements list

# 按项目查
bash <SKILL_DIR>/scripts/run.sh p50_api.py requirements list --project P51

# 按提交人查（查我的需求）
bash <SKILL_DIR>/scripts/run.sh p50_api.py requirements list --submitter h2339

# 按状态筛选
bash <SKILL_DIR>/scripts/run.sh p50_api.py requirements list --status "进行中"

# 新建需求
bash <SKILL_DIR>/scripts/run.sh p50_api.py requirements create P51 h2339 --name "需求名称" --desc "需求描述"

# 编辑需求状态
bash <SKILL_DIR>/scripts/run.sh p50_api.py requirements update <id> --status "已完成"

# 删除需求
bash <SKILL_DIR>/scripts/run.sh p50_api.py requirements delete <id>
```

---

## 响应格式标准

```
## [操作类型] 结果

**项目/模块**：[项目编号] / [模块名]

**执行结果**：[成功/失败]

**关键信息**：
- [字段1]：[值1]
- [字段2]：[值2]

**备注**：[需要注意的事项]
```

**简明优先**，日常操作用 3-5 行概括。

---

## 错误处理

```
执行操作
  ├─ 成功 → 报告结果
  └─ 失败
       ├─ 接口文档查不到
       │    ├─ 换关键词（用功能名而非模块名）
       │    └─ 检查项目编号
       ├─ P50 API 连接失败
       │    ├─ 检查网络是否能访问 http://10.88.109.205（P50 后端 API）
       │    └─ 报告用户后端服务不可达
       ├─ 需求空数据
       │    └─ 不传 projectCode，仅按人查
       └─ 项目不存在（API 返回"所选项目不存在"）
            ├─ 先 projects list 全量模糊匹配
            │    ├─ 匹配 0 个 → 报告用户：系统中无此项目
            │    ├─ 匹配 1 个 → 自动使用该项目的完整编号
            │    └─ 匹配 ≥2 个 → 列出候选项，询问用户选择
            └─ 禁止直接创建新项目
```

---

## 项目配置

| 项目 | 上游 OpenAPI 地址数 | 说明 |
|------|-------------------|------|
| P51 | 3（busi + system + file） | 会议管理、人员二维码 |

### 已知功能名称（防用错）
- ✅ `批量下载二维码`（功能名）
- ✅ `分页查询发放台账`（功能名）
- ❌ `人员二维码发放管理`（模块标签，非功能名）

### 已知模块标签（P51）
会议信息管理、会议场地管理、会议文件管理、会议消息管理、人员二维码发放管理
sys-config / dept / dict / logininfor / menu / notice / operlog / post / profile / role / user

---

## 其他电脑使用说明

在其他电脑上使用此 skill 只需：

1. **复制 skill 目录**到目标电脑的 `~/.workbuddy/skills/work/`
2. **确保网络可达**：
   - OpenAPI 文档源：`http://10.80.251.92:8080/...`（接口文档查询用）
   - 后端 API：`http://10.88.109.205`（账号/周报/项目/需求用，具体端口见 `.env` 中 `P50_API_BASE_URL`）
3. **不需要**安装 api-doc-server、P50 MCP Server、Flask 等任何额外服务
4. **不需要**配置 MCP Server
5. Python 3 是唯一依赖（系统自带即可）

脚本中的 `projects.json` 可自行修改项目对应的上游 OpenAPI 地址。
