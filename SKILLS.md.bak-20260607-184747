# Seele 项目 Skills 清单

本文档汇总本项目（Vue 3 + FastAPI）适用的所有 skills，按层级分类，方便快速定位。

---

## 一、项目级通用 Skills

| Skill | 来源 | 作用 | 适用场景 |
|-------|------|------|----------|
| `update-config` | Claude Code 内置 | 配置 harness 的自动化行为 | 需要设置 hooks、循环任务、自动行为时 |
| `simplify` | Claude Code 内置 | 审查变更代码的质量、复用和效率 | 每次代码修改后审查重构 |
| `loop` | Claude Code 内置 | 定时循环执行命令 | 轮询部署状态、定时检查等 |

---

## 二、前端 Skills（seele-frontend）

| Skill | 来源 | 作用 | 触发条件 |
|-------|------|------|----------|
| `vue-best-practices` | Claude Code 内置 | Vue 3 + Composition API + `<script setup>` + TypeScript 规范 | 任何 `.vue`、Vue Router、Vuex 相关任务 |
| `frontend-design` | Claude Code 内置 | 创建高质量的前端界面，避免 AI 通用审美 | 构建页面、组件、Web 应用时 |

### 前端规范速查（已落地）

- **语法**：Composition API + `<script setup>`，组件 PascalCase，Props camelCase
- **缩进**：2 空格 / 单引号 / 无分号 / LF
- **代理**：`/api` → `http://localhost:9000`（`vue.config.js` 已配置）
- **SFC 顺序**：`<script>` → `<template>` → `<style>`

---

## 三、后端 Skills（seele-backend）

| Skill | 来源 | 作用 | 触发条件 |
|-------|------|------|----------|
| `claude-api` | Claude Code 内置 | 使用 Claude API / Anthropic SDK 开发 AI 应用 | 代码中导入 `anthropic` 或 `@anthropic-ai/sdk` 时 |

### 后端规范速查（已落地）

- **框架**：FastAPI + SQLAlchemy 2.0 + Pydantic v2
- **端口**：强制 9000（`start.py`）
- **数据源**：baostock 为主，akshare 备用
- **响应格式**：统一 `{ code, message, data }`
- **数据范围**：默认仅沪深主板且非 ST

---

## 四、外部 Skills 仓库

| 仓库 | 描述 | 安装方式 |
|------|------|----------|
| `anthropics/skills` | Anthropic 官方示例仓库，含文档、设计、开发、测试等 17 个 skill | `/plugin marketplace add anthropics/skills` |

### 与本项目相关的 skills

| Skill | 类别 | 作用 | 适用场景 |
|-------|------|------|----------|
| `claude-api` | 开发 | 使用 Claude API / Anthropic SDK 构建 AI 应用 | 后端接入大模型、Agent 开发 |
| `frontend-design` | 设计 | 创建高质量前端界面，避免通用 AI 审美 | 股票数据可视化页面、K 线图 UI |
| `webapp-testing` | 测试 | Web 应用自动化测试 | E2E 测试、功能验证 |
| `mcp-builder` | 开发 | 构建 Model Context Protocol 服务器 | 扩展 Claude 与股票数据源交互 |
| `xlsx` | 文档 | Excel 文件读写 | 导出股票数据报表 |
| `pdf` | 文档 | PDF 文件解析与生成 | 导出选股报告、图表 |
| `docx` | 文档 | Word 文档协作编辑 | 生成文档类报告 |
| `web-artifacts-builder` | 设计 | 构建交互式 Web 内容 | 复杂数据展示页面 |

> 其余 skills（`algorithmic-art`、`canvas-design`、`slack-gif-creator`、`theme-factory` 等）偏向创意/设计，与本项目关联度较低，暂不纳入。

---

## 五、Skills 使用优先级

当多个 skills 规范冲突时，按以下优先级执行：

1. **项目内文档**：根级 `README.md` / `CLAUDE.md` / `SKILLS.md`
2. **子项目文档**：`seele-frontend/CLAUDE.md`、`seele-backend/CLAUDE.md`
3. **内置 Skills**：`vue-best-practices`、`frontend-design` 等
4. **外部 Skills 仓库**：第三方补充规范

---

## 六、建议的下一步

如需将外部 skills 仓库整合进本项目，可选择以下方式之一：

- **方式 A**：创建 `CLAUDE.md`（根级 + 前后端各一份），将规范写入文件
- **方式 B**：配置 `.claude/settings.json`，通过 `skills` 字段引用外部仓库路径
- **方式 C**：更新本 `SKILLS.md` 清单，仅作索引，不修改行为
