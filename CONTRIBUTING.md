# 贡献指南

## 分支规范

本项目采用 **GitHub Flow** 工作流，严格禁止直接向 `main` 分支推送代码。

### 分支策略

| 分支 | 说明 | 保护规则 |
|------|------|----------|
| `main` | 主分支，仅接受 PR 合并 | 禁止直接推送，需审查通过 |
| `feature/*` | 功能分支 | 从 main 切出，完成后合并回 main |
| `fix/*` | 修复分支 | 从 main 切出，完成后合并回 main |
| `hotfix/*` | 紧急修复 | 从 main 切出，尽快合并回 main |

### 开发流程

1. **创建功能分支**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **提交修改**
   ```bash
   git add .
   git commit -m "feat: 描述你的变更"
   ```

3. **推送分支**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **创建 Pull Request**
   - 在 GitHub 上创建 PR，目标分支为 `main`
   - 填写 PR 描述，说明变更内容
   - 等待 AI 代码审查和人工审查
   - 审查通过后合并

### 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `style:` 格式（不影响代码运行）
- `refactor:` 重构
- `test:` 测试
- `chore:` 构建/工具

## AI 代码审查

所有 PR 会自动触发 AI 代码审查，审查通过后方可合并。

## 代码规范

- Vue.js：Composition API + `<script setup>`
- Python：FastAPI + 类型注解
- 2 空格缩进，单引号，无分号
