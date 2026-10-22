# ADR-G00：上游 DeepSeek Harness 候选提交与产品集成清单

状态：proposed（W00-1 候选冻结与预检已完成，待 W00-2 原生 Windows x64 构建与双平台干净机实测后转 accepted）  
日期：2026-10-22  
负责人：技术负责人  
关联门槛/需求/工作包：G00 / BASE-01、ARCH-01 / W00-1（TC-001、TC-002、TC-003）

## 问题与证据

1. 产品需基于官方开源 DeepSeek Harness (`dsh`) 桌面端派生，保留完整上游历史、锁文件、规则和许可证，并形成可重复构建与可追溯的发行基线（`BASE-01`、`ARCH-01`）。
2. 2026-10-22 在本机（Microsoft Windows 11 Pro x64，`10.0.26200` Build `26200`）克隆官方仓库 `https://github.com/deepseek-ai/deepseek-harness.git`，核实当前发布标签 `dsh-v0.2.1-rc.2` 对应的 40 位提交为 `687f282e8625c6b8d11ff58211a90524be2e4317`（根包与桌面包版本均为 `0.2.1-rc.2`，Node 引擎要求 `^22.19.0 || >=24.0.0`，包管理器固定 `pnpm@11.28.5`）。
3. 核实锁文件与运行资产哈希：
   - `pnpm-lock.yaml`：`1090222` bytes，SHA256 `4637cca3b89c4c8d5a147321710e597aa62ec2444a3772ab542be5690893dfe4`
   - `scripts/primary-runtime/lock.json`：`10216` bytes，SHA256 `733c3c53d95ae524bddb123e1319c48ecacb0dc729be956c25188f930c095bd5`
   - `package.json`：`18994` bytes，SHA256 `12bb41cd8212021a784b33a20c2b84372189a9505b42081d5e3869e21ff5cffc`
   - `apps/desktop/package.json`：`3904` bytes，SHA256 `913095d3048ad424335acccf8e3193bb9523961604709062a430f57c4ac22479`
4. 逐项评估三个社区候选插件与 `dsh@0.2.1-rc.2` 的兼容性和运行依赖边界（证据见 `packages/boot/app-boot/src/plugin-compatibility.ts` 与各仓库 manifest）：
   - `dsh-open-file`（`https://github.com/hyper-dsh-plugins/dsh-open-file.git`，commit `39636d198993c5980da0091056d307bb5a8a48c5`，版本 `0.1.2-rc.1`）：`peerDependencies` 精确要求 `@deepseek-ai/dsh-agent: 0.1.2-rc.1`、`@deepseek-ai/dsh-session: 0.1.2-rc.1`、`@deepseek-ai/dsh-skill: 0.1.2-rc.1`、`@deepseek-ai/dsh-tools: 0.1.2-rc.1` 等 9 个官方包版本为 `0.1.2-rc.1`，与当前运行时 `0.2.1-rc.2` 不兼容，兼容预检直接拒绝（满足 `TC-002`）。
   - `dsh-cowork`（`https://github.com/Jesse-njx/dsh-cowork.git`，commit `2ae5cf755c4294a1e988eebf3b12dd062425d84c`）：子包 `@dsh-cowork/plugin@0.1.0` 的 `peerDependencies` 要求 `@deepseek-ai/dsh-fs: ^0.1.0-rc.6`、`@deepseek-ai/dsh-system-prompt: ^0.1.0-rc.6`、`@deepseek-ai/dsh-tools: ^0.1.0-rc.6`（`0.x` 次版本下 `^0.1.0-rc.6` 仅匹配 `<0.2.0-0`），与 `0.2.1-rc.2` 同样不匹配，预检拒绝（满足 `TC-002`）。
   - `dsh-quicksight`（`https://github.com/Isanti2016/dsh-quicksight.git`，commit `648123d4a605e53bf74c0e6189462004ba4bc9b7`，版本 `0.1.1`）：虽未声明 `engines.dsh` 或 `@deepseek-ai/dsh-*` peer，但其 README 要求用户手工执行 `python -m venv ~/.dsh/tools/ocr-venv` 与 `pip install rapidocr_onnxruntime` 及 `npx @liustack/modlens` 本地配置 API Key，直接违反 `BASE-02`（无开发环境开箱即用）、`ACC-02`（不要求用户配置 Key）与 `ARCH-02`（受控工具代理）。

## 方案与决定

1. **上游基线冻结**：锁定官方仓库 `https://github.com/deepseek-ai/deepseek-harness.git` 发布标签 `dsh-v0.2.1-rc.2` 对应的精确 40 位提交 `687f282e8625c6b8d11ff58211a90524be2e4317` 作为 QualityOffice AI V0.1 候选底座；禁止在发行或构建配置中使用 `master`、`main` 或 `latest` 浮动引用。
2. **官方内置能力复用**：
   - 桌面宿主与生命周期：复用 `@deepseek-ai/dsh-desktop@0.2.1-rc.2`（Electron `44.7.0`）及 `@deepseek-ai/dsh-app-boot`、`@deepseek-ai/dsh-web-app`。
   - 受控运行环境：复用 `scripts/primary-runtime/lock.json` 锁定的独立 `win-x64` Node `24.21.0`、Python `3.12.14 (20260901)` 与 11 个锁定 SHA256 的 Python wheels（`numpy`、`pandas`、`python-docx`、`python-pptx`、`openpyxl`、`Pillow`、`lxml`、`XlsxWriter`、`python-dateutil`、`six`、`tzdata`、`typing_extensions`、`et_xmlfile`）。
   - Office 技能与转换预览：复用官方 `@deepseek-ai/dsh-skill-office@0.2.1-rc.2`、`@deepseek-ai/dsh-office-to-pdf@0.2.1-rc.2` 及 `@deepseek-ai/libreoffice-kit@0.1.5`（含 `@deepseek-ai/libreoffice-kit-win32-x64@0.1.5`）。
   - Windows 进程与权限底座：复用 `@deepseek-ai/dsh-sandbox-windows-acl`、`@deepseek-ai/dsh-win32-process`，并在 W00-3 按 `ARCH-02` 封装为只读原件 + 每 attempt 独立可写目录的受控固定执行器。
3. **社区候选插件处置**：
   - **不启用** `dsh-open-file@0.1.2-rc.1`、`@dsh-cowork/plugin@0.1.0`、`dsh-quicksight@0.1.1`；严禁通过手工修改插件 `package.json` 版本声明或写入 `compatibility.json` 风险豁免来绕过 `evaluatePluginCompatibility` 预检。
   - **产品自有统一解析与 OCR 链路**：按 Spec §4.1—4.2 与 `contracts/local-tools.schema.json`、`contracts/parse-result.schema.json`，在产品 `product/local-worker/` 中基于随包 Python/Node 实现单一主文件导入与解析链路；本地离线 OCR 资产（引擎、模型/语言数据、许可证及 SHA256）在 W00-2 实测并补齐完整许可证后才允许闭合 G00。
4. **许可证与运行资产阻断策略（`TC-003`）**：
   - 已核实上游 MIT 许可证、`vendor/` MIT 许可证、`THIRD_PARTY_NOTICES.md`、`@deepseek-ai/libreoffice-kit` MPL-2.0 源码告知义务及 Bundled Python wheels 许可证。
   - 保持 `G00` 状态为 `open`、`release/release-manifest.json` 中 `status` 为 `draft_unfrozen`，因为：(a) 拟分发的本地 OCR 语言数据/模型资产与中文字体尚未最终选定并记录 SHA256；(b) `@anthropic-ai/claude-agent-sdk*` 与 `@openai/codex*` 专有附加包需在产品裁剪中剔除；(c) 尚未完成干净 Windows 10/11 双系统安装包构建与实测。

## 影响

- **架构与目录**：开发基准包整体迁入 `docs/spec/`，根目录保留并整合上游 `AGENTS.md` 与 `README.md`，新增集中补丁台账 `upstream-patches/PATCH-LEDGER.md` 与发行清单实值草案 `release/release-manifest.json`。
- **需求与契约**：不改变 `docs/spec/` 下 67 项需求、45 个工作包和 153 条计划测试；仅对 `docs/spec/validate_spec.py` 做 Windows POSIX 路径分隔符兼容修复并同步 `PACKAGE-MANIFEST.json`。
- **后续工作包**：W00-2 直接基于本 ADR 锁定的 `687f282e8625c6b8d11ff58211a90524be2e4317` 与 `pnpm@11.28.5` 在 Windows x64 执行原生构建、OCR 资产封装与无开发环境机器安装验证。

## 验证与回退

- **已验证项**：
  - `python docs/spec/validate_spec.py`：1354 项检查全部通过。
  - `TC-001`（提交与依赖可追溯）：固定 40 位提交、锁文件与 `primary-runtime/lock.json` SHA256 已核实并可通过 `pnpm install --frozen-lockfile` 复现。
  - `TC-002`（不兼容插件不被强行启用）：使用上游 `evaluatePluginCompatibility` 对 `dsh-open-file@0.1.2-rc.1` 和 `@dsh-cowork/plugin@0.1.0` 执行兼容预检，准确检出版本不匹配并拒绝纳入。
  - `TC-003`（许可与运行资产清单完整）：完成现有运行时、Python wheels、LibreOffice Kit 与 npm 依赖许可盘点，并明确列出未冻结的 OCR/字体/专有 SDK 剔除阻断项。
- **尚未验证项**：Windows 10/11 干净镜像安装与运行（`TC-004`）、离线 OCR 实测（`TC-005`）、超限样本（`TC-006`）。
- **回退方式**：若 W00-2 实测发现 `0.2.1-rc.2` 在 Windows 干净机存在阻断缺陷，可通过新建 ADR 切换至修复后的固定 40 位提交并重新执行 `TC-001`—`TC-003`。
