# weave-note

> 中文版（默认） · [English](README.en.md)

**一个非常简单的笔记应用**：记录、组织与检索个人知识，支持多格式导出。

## 项目特点

- **零配置起步**：默认 SQLite（首次启动自动建库建表），切换 PostgreSQL 只需改一行 `[database] type`
- **轻量可嵌入**：FastAPI + async SQLAlchemy 2.0 单进程即可运行；前端为 Vue3 + Vite 单页应用
- **知识组织**：笔记本 → 笔记两级结构，支持默认笔记本、快速笔记、批量操作
- **全文搜索**：标题/正文关键词搜索（SQLAlchemy 跨库 ILIKE 匹配），支持笔记本内过滤
- **多格式导出**：单笔记 Markdown、笔记本 CSV（ZIP 打包）、PDF（WeasyPrint）
- **异步导出管道**：导出任务经 `export_worker` 后台队列（并发 2、超时 600s），大导出不阻塞接口
- **文件解析**：上传 docx / pptx / xlsx / PDF / 图片自动解析为正文（懒加载，缺依赖时优雅降级）
- **多用户**：注册/登录/JWT，每用户独立 `user_workspaces/` 文件区

## 核心功能

| 功能       | 说明                                            |
| ---------- | ----------------------------------------------- |
| 笔记本管理 | 新建 / 重命名 / 设默认 / 删除（默认笔记本保护） |
| 笔记 CRUD  | 新建 / 编辑 / 移动 / 批量删除                   |
| 快速笔记   | 一键记录，自动落入默认笔记本                    |
| 全文搜索   | 关键词命中笔记，返回上下文片段                  |
| 导出       | 单笔记 Markdown / 笔记本 CSV（ZIP）/ PDF |
| 文件上传   | docx/pptx/xlsx/PDF/图片 解析入库                |

## 目录结构

```
weave-note/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口、健康检查、静态文件、导出轮询代理
│   │   ├── api/             # 路由：auth / notes / export_tasks / file_upload / image_upload
│   │   ├── core/            # config（sqlite/postgres 双模）/ deps
│   │   ├── db/              # database（方言自适应引擎）/ migrations
│   │   ├── schemas/         # pydantic 模型
│   │   ├── services/        # auth_service / export_worker / file_parser / workspace_service 等
│   │   └── vendor_js/       # 前端引用的第三方 JS
│   ├── static/              # 前端构建产物
│   ├── config.toml          # 服务配置（[database] type 切换 sqlite/postgres）
│   └── requirements.txt
├── frontend/                # Vue3 + Vite 前端源码
└── scripts/                 # install_venv / init_db / build / start / stop / restart
```

## 部署前提

| 依赖     | 版本要求              | 说明                                                                                                                                                                                                                |
| -------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 操作系统 | -                     | macOS / Ubuntu 22.04+ / Windows（推荐 WSL2；原生 Windows 用 Git Bash 跑 bash 脚本）                                                                                                                                 |
| Python   | 3.11+（建议 3.13）    | Ubuntu 24.04 自带 3.12；22.04 需`add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.12`；macOS: `brew install python@3.13`；Windows: python.org 安装器（勾选 Add to PATH）                       |
| Node.js  | 18+（仅重建前端需要） | 仓库已含构建产物（`backend/static/`），不改前端可不装；需要时：macOS: `brew install node`；Ubuntu: `sudo apt install nodejs npm`（24.04 自带 18）或 NodeSource；Windows: `winget install OpenJS.NodeJS.LTS` |
| curl     | -                     | 验证接口                                                                                                                                                                                                            |

> 数据库默认使用 **SQLite**（零外部依赖，首次启动自动建库建表，无需安装 PostgreSQL）。
> 如需切换回 PostgreSQL 14+（不需 pgvector），先安装 PostgreSQL：
> macOS: `brew install postgresql@16 && brew services start postgresql@16`；
> Ubuntu: `sudo apt install postgresql && sudo systemctl start postgresql`；
> Windows: 推荐 WSL2 后按 Ubuntu 步骤。
> 然后改 `backend/config.toml` 的 `[database] type = "postgres"` 并创建同名数据库：
>
> ```bash
> createdb -U postgres -h 127.0.0.1 weave_note
> ```
>
> 认证说明：macOS/Homebrew 默认本地免密（trust），直接可用；Ubuntu 默认本地 TCP 为 scram
> 认证，需先 `sudo -u postgres psql -c "ALTER USER postgres PASSWORD '<强密码>'"`，脚本运行时
> `export PGPASSWORD='<强密码>'`（init_db.sh 透传该变量），并把同一密码写入
> `backend/config.toml` 的 `[database] password`（服务连接只读 config，不走环境变量）。

### 可选功能的系统依赖（PDF 导出 / 图表公式渲染）

| 功能                   | 系统依赖              | 安装方式                                                                                                                                                                       |
| ---------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PDF 导出（WeasyPrint） | Pango 等系统库        | macOS:`brew install pango`；<br />Ubuntu: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 fonts-noto-cjk`                             |
| 图表/公式渲染（Playwright） | Chromium 浏览器二进制 | 创建 venv 后执行`.venv/bin/python -m playwright install chromium`（Windows 环境为 `.venv\Scripts\python.exe`；Ubuntu 再加 `python -m playwright install-deps chromium`）。缺失时 mermaid/ECharts/LaTeX 图表导出降级为占位/文本 |

> **Windows**：WeasyPrint 无官方免依赖的 Windows 构建（需要 Pango 动态库），
> 原生 Windows 下 PDF 导出不可用——weave-note 建议整体部署在 WSL2 内；
> 笔记浏览/编辑等其余功能在原生 Windows（Git Bash 环境）可正常使用。

## 独立部署（自包含三步）

本项目不依赖外层目录结构，独立部署只需：

```bash
bash scripts/install_venv.sh   # 本项目 .venv + 依赖（幂等；PYTHON_BIN 可指定解释器）
bash scripts/init_db.sh        # 按 [database] type 初始化：sqlite 免 PG；postgres 幂等建库+预建表
bash scripts/start.sh          # 启动（自动选用 .venv）
curl http://127.0.0.1:8201/healthz
```

## 部署步骤（详细）

### 1. 数据库

**推荐（自包含）**：直接运行项目级脚本，它按 `[database] type` 自动处理
SQLite 预建 / PostgreSQL 幂等建库 + 预建表（幂等可重复）：

```bash
bash scripts/init_db.sh
```

**SQLite（默认）**：实际无需任何操作，首次启动自动创建 `backend/weave_note.db`。

**PostgreSQL（可选）**：前置需本机 PostgreSQL 14+。脚本会幂等 `createdb weave_note`；
也可以手工：

```bash
createdb -U postgres -h 127.0.0.1 weave_note
```

如果数据库已存在会报错，可忽略，或先执行：

```bash
psql -U postgres -h 127.0.0.1 -d postgres \
  -c "SELECT 1 FROM pg_database WHERE datname='weave_note'"
```

在 family 多项目目录下也可用家族级入口（等价于依次调用各项目的
`scripts/init_db.sh`，weave_mem 恒 PG+pgvector）：

```bash
bash <family根>/scripts/init_databases.sh
```

### 2. 创建虚拟环境并安装依赖

**推荐（自包含）**：

```bash
bash scripts/install_venv.sh
```

等价的手工步骤：

```bash
python3.11 -m venv .venv     # 或 python3.13
./.venv/bin/pip install -r backend/requirements.txt
```

> 若已有可用的共享虚拟环境（如 family 仓库根目录的 `.venv` 或 `/tmp/weave-family-venv`），
> 本步骤可跳过；`scripts/start.sh` 会自动按顺序探测选用。

### 3. 修改配置

编辑 `backend/config.toml`：

```toml
[server]
host = "127.0.0.1"   # 仅本机访问；对外部署改 0.0.0.0
port = 8201

[security]
jwt_secret_key = "请改成足够长的随机字符串"

[database]
# type = "sqlite"（默认）| "postgres"
type = "sqlite"
path = "weave_note.db"
# postgres 模式使用以下字段：
# host = "127.0.0.1"
# port = 5432
# username = "postgres"
# password = ""
# name = "weave_note"
```

支持的环境变量：

| 环境变量                    | 说明                                                     |
| --------------------------- | -------------------------------------------------------- |
| `PYTHON`                  | 指定启动解释器（`start.sh` 优先使用）                  |
| `HOST` / `PORT`         | 覆盖监听地址/端口（`start.sh`）                        |
| `LOG_FILE` / `PID_FILE` | 日志/PID 文件路径（`start.sh`）                        |
| `JWT_SECRET_KEY`          | JWT 密钥（config.toml 未配置时生效）                     |
| `CONFIG_MODEL_PATH`       | 模型 config_model.toml 路径（默认取 config.toml 同目录） |

### 4. 启动

```bash
# 在项目根目录执行
chmod +x scripts/*.sh
bash scripts/start.sh
```

脚本默认写入：

- PID 文件：`weave-note/weave-note.pid`
- 日志文件：`weave-note/weave-note.log`

可使用 `LOG_FILE`、`PID_FILE`、`HOST`、`PORT`、`PYTHON` 环境变量覆盖这些路径与参数。

### 5. 验证

```bash
# 健康检查
curl http://127.0.0.1:8201/healthz
# 期望：{"status":"ok","service":"weave-note","database":"ok"}

# 登录（首次启动已自动创建 test / 123456）
curl -sS -X POST http://127.0.0.1:8201/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"test","password":"123456"}'

# 前端
open http://127.0.0.1:8201/
```

浏览器打开后使用 `test / 123456` 登录，可新建笔记本、新建/编辑/删除笔记、搜索笔记。

### 5.1 端到端工作流验收

按以下顺序操作即为完整笔记工作流：

1. 浏览器打开 `http://127.0.0.1:8201/`，用 `test / 123456` 登录
2. 点击「＋」新建笔记本，输入名称并确定
3. 点击「＋ 新建」，输入标题与正文，点击「保存」
4. 在左侧搜索框输入正文中的关键词，按回车，确认能命中该笔记
5. 重新点击笔记本列表中的笔记本，点击该笔记，修改正文并再次保存
6. 确认修改后内容仍在，且重启服务后依然存在

### 6. 停止

```bash
bash scripts/stop.sh
```

## 核心 API

| 方法     | 路径                                           | 说明                                    |
| -------- | ---------------------------------------------- | --------------------------------------- |
| POST     | `/api/auth/register`                         | 注册（body：username/password）         |
| POST     | `/api/auth/login`                            | 登录，返回 JWT                          |
| POST     | `/api/auth/logout`                           | 登出                                    |
| GET      | `/api/auth/me`                               | 当前用户信息                            |
| GET      | `/api/notes/notebooks`                       | 笔记本列表                              |
| POST     | `/api/notes/notebooks`                       | 新建笔记本                              |
| PUT      | `/api/notes/notebooks/{id}`                  | 重命名笔记本                            |
| PUT      | `/api/notes/notebooks/{id}/default`          | 设为默认笔记本                          |
| GET      | `/api/notes/default-notebook`                | 获取默认笔记本                          |
| DELETE   | `/api/notes/notebooks/{id}`                  | 删除笔记本（默认笔记本不可删）          |
| POST     | `/api/notes/notebooks/bulk-delete`           | 批量删除笔记本                          |
| POST     | `/api/notes/notebooks/bulk-export`           | 批量导出笔记本（zip）                   |
| GET      | `/api/notes/notebooks/{id}/export`           | 导出笔记本 CSV                          |
| GET      | `/api/notes/notebooks/{id}/notes`            | 笔记列表                                |
| POST     | `/api/notes/notebooks/{id}/notes`            | 新建笔记                                |
| GET      | `/api/notes/notes/{id}`                      | 笔记详情                                |
| PUT      | `/api/notes/notes/{id}`                      | 保存笔记                                |
| DELETE   | `/api/notes/notes/{id}`                      | 删除笔记                                |
| PUT      | `/api/notes/notes/{id}/move`                 | 移动笔记                                |
| POST     | `/api/notes/notes/bulk-delete`               | 批量删除笔记                            |
| POST     | `/api/notes/notes/bulk-move`                 | 批量移动笔记                            |
| POST     | `/api/notes/notes/bulk-export`               | 批量导出笔记（zip）                     |
| POST     | `/api/notes/quick`                           | 快速笔记                                |
| GET      | `/api/notes/search?q=关键词`                 | 全文搜索                                |
| GET      | `/api/notes/notes/{id}/export?format=md`     | 导出笔记                                |
| GET/POST | `/api/export-tasks[/{task_id}]`              | 异步导出任务：创建/查询/下载/取消/删除  |
| POST     | `/api/files/upload`                    | 文件上传解析（docx/pptx/xlsx/pdf/图片） |
| POST     | `/api/images/upload` `/upload-media` | 图片上传                                |
| GET      | `/api/images/serve`                    | 图片访问                                |

除注册/登录/健康检查外，其余接口均需请求头：

```http
Authorization: Bearer <access_token>
```

## 常见问题

### 启动失败：数据库连接错误

SQLite 模式（默认）：确认 `backend/` 目录可写（首次启动创建 `weave_note.db`），
启动日志出现 `Weave Note 启动完成` 即正常。

PostgreSQL 模式：确认 PostgreSQL 已启动且数据库存在：

```bash
pg_isready -h 127.0.0.1 -p 5432
psql -U postgres -h 127.0.0.1 -d weave_note -c 'SELECT 1'
```

### 端口被占用

修改 `backend/config.toml` 的 `port`，或启动时覆盖：

```bash
PORT=8204 bash scripts/start.sh
```

### 忘记测试账号密码

删除 `weave_note.db`（SQLite，默认）或 `weave_note` 库（PostgreSQL）中的测试用户后重启会自动重建；更推荐直接使用注册接口创建新账号。

### 日志在哪里

默认 `weave-note/weave-note.log`。如果设置了 `LOG_FILE` 环境变量，则为该路径。
