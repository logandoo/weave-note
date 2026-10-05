# 变更记录（weave-note）

本项目在 v0.x 阶段不启用版本号，按日期归档；格式参考 Keep a Changelog。

## 2026-10-05

### 变更
- 脚本入口统一到 `script/linux/`（start/stop/restart/project_build/install_venv/init_db），取消 `scripts/` 目录。

## 2026-08-18

### 修复
- 安全与工程化加固：登出即失效、JWT 密钥环境变量/持久化、CORS 修正、登录限流、时间戳 UTC 化；补齐 CI（ruff + 类型检查 + 前端构建）。
- 修复登录/搜索等复验问题。

### 变更
- 默认数据库 SQLite（保留 PostgreSQL 双支持）；三平台部署适配（macOS / Ubuntu / Windows-WSL2）。

## 2026-08-17

### 新增
- 首个版本：从 chatbot 拆分；笔记本 / 笔记管理、全文搜索；图片上传与文件转笔记；多格式导出（PDF / CSV / Markdown / 截图）；侧边栏二级菜单（重命名 / 删除 / 移动）。
