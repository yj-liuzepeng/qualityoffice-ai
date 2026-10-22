# QualityOffice AI开发基准包 v1.2

本包把《开发需求文档 v0.3》转换为分阶段实施规范。它包含设计和计划，没有把应用源码、真实 Windows 构建或尚未运行的测试结果冒充交付。

产品名称：质量AI助手 · QualityOffice AI。产品定位：面向专业工作的 AI 知识与办公助手。宣传语：专业知识，智能办公。

从 `开发Spec.md` 开始。按 `tasks.json` 的依赖执行，每项任务运行其 `test_ids`；从第一个工作包 W00-1 开始冻结官方 dsh。不要先凭猜测填写 commit 或服务商使用量规则。

| 文件 | 用法 |
| --- | --- |
| 需求文档.md | v0.3 产品方向、范围与原始验收组 |
| 开发Spec.md | 范围、周期、架构、交互、数据、功能、验收及来源 |
| requirements.json | 67项需求，含原PRD编号和新增规格编号 |
| tasks.json | 15周期、45工作包、依赖/步骤/估算/产物/测试 |
| test_cases.json | 153条逐项前置/操作/预期，初始均not_run |
| 实施工作包.md / 测试用例手册.md | 人可直接阅读的详细任务和逐项测试 |
| traceability.json | 需求→任务→测试、原T01—T15及新增T16—T19场景追踪 |
| contracts/ | OpenAPI、解析/工具/Office计划/个人要求/领域订阅/SSE JSON Schema、语义 |
| data/ | SQLite/PostgreSQL结构与跨表事务不变量 |
| baseline/ | 决策门槛、发行清单模板、默认参数 |
| acceptance/ | fixture要求、周期与测试报告模板、ADR |
| validate_spec.py | 标准库可运行的一致性检查，非应用测试 |
| validation_report.json | 本包结构检查结果及未验证范围 |

周期假设：1名全栈开发者、每周30有效小时，C01/C09/C11为3周、其他周期2周；33周共990研发小时（792计划+198缓冲），另有66小时产品/测试评审。V0.1目标前6周期约13周。按实测与投入重估，日期到达不代表验收通过。

测试按 `target_version` 选择当前及历史版本回归；不能因为某个公共NFR需求始于V0.1，就把该需求下V0.4的PPT测试也要求在V0.1实现。V0.1必须满足七类输入、OCR、联网来源、基础Office副本及会员闭环，不能以未来排期删掉已确认范围。

JSON为UTF-8，CSV不是本包的任务真相。可将工作包导入自己的项目管理系统，但修改后保持ID和追踪一致。`build_registry.py`重建清单及主文档第22节；`build_contracts.py`重建契约，直接编辑生成文件会在重建时丢失。

```bash
python3 build_registry.py
python3 build_contracts.py
python3 validate_spec.py
```

检查器验证引用、覆盖、依赖无环、周期小时、原PRD映射、JSON基本结构及本地SQLite DDL可执行。它不代表完整JSON Schema标准符合性认证、不执行PostgreSQL DDL、不运行应用/Windows/模型/OCR/Office效果测试。正式开发应另外接入完整schema/OpenAPI校验器和真实数据库CI。

所有G项初始open，fixture初始required；发行工具必须拒绝未冻结发行清单和未完成fixture。它们是明确交给C00等工作包完成的任务，不是遗漏后默认视为通过。

计划内容变更应修改生成器再重建；实际执行进度和测试成绩保存在独立报告中，不直接用计划生成脚本管理进度。重建不会保留手改的生成JSON。

本次新增：通用引擎与可选领域包；工作台/知识库/办公/资讯统一导航；常用要求和执行快照；用户仅选领域、主题、内容类型与时间。医药是首个验证领域，未发布的领域不向用户提供空选项。新增范围已进入任务和用例，原有ID不变。
