# Seele 项目 Skills 清单

本文档记录当前项目适用的技能入口。原始版本已备份为 `SKILLS.md.bak-20260607-184747`。

## 当前优先使用

| Skill | 位置 | 作用 | 触发场景 |
|-------|------|------|----------|
| `seele-project` | `C:\Users\Ouhz\.codex\skills\seele-project` | Seele 项目专用协作技能，覆盖进程清理、前后端规范、异步任务、数据写入和验证流程 | 任何涉及本仓库的查看、修改、运行、调试、审查任务 |
| `browser:control-in-app-browser` | Codex Browser 插件 | 在 Codex 内置浏览器中验证本地前端页面 | 前端改动后验证 `localhost:8000` 页面、交互或截图 |
| `skill-creator` | Codex 系统技能 | 创建或更新 Codex skill | 需要新增/调整项目技能时 |
| `openai-docs` | Codex 系统技能 | 查询 OpenAI 官方文档 | OpenAI API、Codex、模型选择等问题 |
| `imagegen` | Codex 系统技能 | 生成或编辑位图图片 | 需要生成图片素材、视觉 mockup、插画等 |

## 项目规则入口

优先读取并遵守：

1. `AGENTS.md`
2. `CLAUDE.md`
3. `SKILLS.md`
4. `seele-backend/README.md`
5. `seele-frontend/README.md`

## 前端约定

- 技术栈：Vue 3、Vue Router、ECharts、Vue CLI
- 目录：`seele-frontend`
- 端口：`8000`
- API 代理：`/api` 转发到 `http://localhost:9000`
- 风格：Composition API、`<script setup>` 优先、2 空格、单引号、无分号、LF
- 前端视觉任务应保持现有设计系统，不做通用模板化 UI

## 后端约定

- 技术栈：FastAPI、SQLAlchemy 2.0、Pydantic v2、MySQL
- 目录：`seele-backend`
- 端口：`9000`
- 启动入口：`seele-backend/start.py`
- 响应格式：`{ code, message, data }`
- 配置入口：`seele-backend/app/config.py`
- dev/prod 差异只通过 `DEPLOY_ENV=dev|prod` 和配置文件推导

## 已注释归档：当前 Codex 环境不直接使用

<!--
以下是原 Claude Code / 外部 skills 清单。当前 Codex 会话未直接加载这些 skill 实体，保留为历史索引，不作为自动触发依据。

| Skill | 原来源 | 原作用 |
|-------|--------|--------|
| `update-config` | Claude Code 内置 | 配置 harness 的自动化行为 |
| `simplify` | Claude Code 内置 | 审查变更代码的质量、复用和效率 |
| `loop` | Claude Code 内置 | 定时循环执行命令 |
| `vue-best-practices` | Claude Code 内置 | Vue 3 + Composition API + `<script setup>` 规范 |
| `frontend-design` | Claude Code / 外部仓库 | 创建高质量前端界面 |
| `claude-api` | Claude Code / 外部仓库 | 使用 Claude API / Anthropic SDK 开发 AI 应用 |
| `webapp-testing` | anthropics/skills | Web 应用自动化测试 |
| `mcp-builder` | anthropics/skills | 构建 Model Context Protocol 服务 |
| `xlsx` | anthropics/skills | Excel 文件读写 |
| `pdf` | anthropics/skills | PDF 文件解析与生成 |
| `docx` | anthropics/skills | Word 文档协作编辑 |
| `web-artifacts-builder` | anthropics/skills | 构建交互式 Web 内容 |

如后续安装这些技能，可再移出注释区并注明实际路径。
-->
