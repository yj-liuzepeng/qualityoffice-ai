# QualityOffice AI 上游补丁与定制台账 (Upstream Patch Ledger)

基线版本：`dsh-v0.2.1-rc.2`  
固定上游 Commit：`687f282e8625c6b8d11ff58211a90524be2e4317`  
原则（`ARCH-01`）：优先通过独立业务 Bundle、Profile 配置和 `product/` 目录实现定制；确需修改上游源码时，在此台账登记目的、触达模块、回归测试与冲突风险。

## 1. 上游自带 pnpm 依赖补丁（随上游保留，只读不改）

| 序号 | 补丁路径 | 目标依赖 | 分类（`runtime-patch-policy.ts`） | 用途 | 状态 |
| --- | --- | --- | --- | --- | --- |
| UP-01 | `patches/@earendil-works__pi-ai@1.1.0.patch` | `@earendil-works/pi-ai@1.1.0` | shared | 多服务商 LLM 适配修复 | 随上游保留 |
| UP-02 | `patches/@electron__osx-sign@1.3.3.patch` | `@electron/osx-sign@1.3.3` | workspace-only | macOS 签名符号链接处理 | 随上游保留 |
| UP-03 | `patches/@fortune-sheet__core@1.0.4.patch` | `@fortune-sheet/core@1.0.4` | workspace-only | 表格预览核心修复 | 随上游保留 |
| UP-04 | `patches/@fortune-sheet__react@1.0.4.patch` | `@fortune-sheet/react@1.0.4` | workspace-only | 表格预览 React 包装修复 | 随上游保留 |
| UP-05 | `patches/@yao-pkg__pkg@6.21.0.patch` | `@yao-pkg/pkg@6.21.0` | workspace-only | CLI 单文件打包修复 | 随上游保留 |
| UP-06 | `patches/app-builder-lib@26.17.0.patch` | `app-builder-lib@26.17.0` | workspace-only | `electron-builder` 打包增强 | 随上游保留 |
| UP-07 | `patches/exceljs@4.4.0.patch` | `exceljs@4.4.0` | shared | Excel 读写边界修复 | 随上游保留 |
| UP-08 | `patches/node-pty@1.2.0-beta.15.patch` | `node-pty@1.2.0-beta.15` | shared | 终端伪终端兼容修复 | 随上游保留 |

## 2. 本仓库已应用的上游文件改动（W00-1）

| 补丁编号 | 触达文件 | 目的 | 关联工作包/需求 | 回归验证 | 上游升级冲突风险 |
| --- | --- | --- | --- | --- | --- |
| QO-001 | `AGENTS.md` | 在不删除上游任何规范的前提下，于末尾合并 QualityOffice AI 协作约定与 `docs/spec/` 入口，并保持总词数 `2053 <= 2080`（符合 `verify-doc-budgets`、`verify-md-wrap`、`verify-md-links`） | W00-1 / BASE-01 | `pnpm run verify-doc-budgets`、`pnpm run verify-md-wrap`、`pnpm run verify-md-links` | 低（仅文件末尾追加独立章节） |
| QO-002 | `README.md` | 在顶部增加 QualityOffice AI 工程入口说明，指向 `docs/START-HERE.md`、`docs/progress.md` 与 `docs/spec/README.md`，保留上游全文 | W00-1 / BASE-01 | `pnpm run verify-md-wrap`、`pnpm run verify-md-links` | 低（仅顶部插入一段单行段落） |

## 3. 后续工作包计划中的集中定制点（待对应工作包实施）

| 计划编号 | 预计触达模块 | 目的 | 计划工作包 | 策略（优先非侵入配置，次选薄补丁） |
| --- | --- | --- | --- | --- |
| QO-PLAN-01 | `packages/bundle/base/cordis.patch.yml`、`packages/bundle/web-app/cordis.patch.yml` 或产品专属 Profile Bundle | 禁用用户版 `tool-pwsh`、`tool-bash`、`tool-fs` 任意路径写、`tool-plugin-manager`、`ui-sidebar-terminal`、`ui-plugin-manager`，仅暴露 `contracts/local-tools.schema.json` 白名单工具 | W00-3、W01-1 | 优先通过产品专属 Profile Bundle 与 `cordis.patch.yml` 覆盖，不直接改 `dsh-base` 源码 |
| QO-PLAN-02 | `apps/desktop/src/`、`apps/desktop/scripts/electron-builder-config.mjs` | 独立 `appId`、协议、数据目录、隐藏生产环境 `F12`/`Ctrl+Shift+I` DevTools 菜单加速键、替换强制更新与遥测地址（禁用 `dsh-otel-collector.deepseeksvc.com`） | W01-1 | 薄补丁集中于 `apps/desktop/`，并在本台账记录精确 diff |
| QO-PLAN-03 | `apps/desktop/scripts/prepare-package-set.ts` / `runtime-file-policy.ts` | 从用户发行包剔除 `@anthropic-ai/claude-agent-sdk*` 与 `@openai/codex*` 等非必要的第三方专有 CLI 载荷 | W00-2 / W01-1 | 打包配置过滤，减小安装包体积并消除专有许可风险 |
