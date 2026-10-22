# 个性化与领域订阅契约语义

本契约为产品本地宿主接口，非 dsh 官方 API，不新增必须联网的配置服务。Schema 描述结构；引用、权限、规则合并和事务由应用层验证。候选资产均需阶段验证。

## 1 本地调用与错误

| 宿主业务命令 | 输入与结果 | 应用条件 |
| --- | --- | --- |
| officeProfiles.list/get | 当前账号，profile_id/revision（可选）；返回有效或历史快照 | 不读取其他账号数据，deleted 默认不列出 |
| officeProfiles.save/duplicate | OfficeProfile + expected_revision（新建为空）；返回不可变新 revision | 名称非空，至多50有效项，当前修订CAS，复制产生新ID |
| officeProfiles.setDefault/delete | profile_id + expected_revision | 同账号单个默认；删默认置空，不偷偷选另一个；历史快照保留 |
| officePreferences.resolve | 当前任务要求、选中profile、template、domain和KB IDs | 返回EffectivePreferences或needs_input；重新校验访问状态与支持字段 |
| domainCatalog.list/get | 当前已发布包；可读旧版用于历史运行 | 按版本返回，不把draft/fixture当可订阅 |
| subscriptionPlan.preview/save | SubscriptionPlan + expected_revision | preview返回覆盖来源/样例/下次执行；save重新校验并CAS保存，不信任客户端resolved_source_ids |
| subscriptionPlan.pause/resume | plan_id + expected_revision | 保存新修订；恢复不重复发已完成日通知；不清空watermark或预算 |

通用错误：VALIDATION_ERROR、REVISION_CONFLICT、PROFILE_LIMIT、PROFILE_DELETED、TEMPLATE_UNAVAILABLE、KB_SCOPE_UNAVAILABLE、UNSUPPORTED_PREFERENCE、PREFERENCE_CONFLICT、DOMAIN_NOT_PUBLISHED、DOMAIN_VERSION_UNAVAILABLE、SOURCE_COVERAGE_MISSING、SOURCE_LIMIT、PACKAGE_INTEGRITY_FAILED、ADAPTER_NOT_ALLOWED。错误必须携带可显示说明和字段位置，不暴露任意路径或代码。命令经宿主鉴权/输入校验，不开放任意网络RPC；IPC技术形态在C01/C09/C11实现时冻结。

## 2 个人要求与任务快照

OfficeProfile 的 profile_json 为不可变内容；is_default 是当前指针状态，历史配置中该字段仅表示当时状态。保存时同一SQLite事务创建revision、更新current_revision和默认唯一索引。删除为软删除；不得删掉历史attempt使用的EffectivePreferences。

字段合并按 Spec §12.1a：policy > task > profile > template > domain > app。只有已支持字段进入计划；provenance逐字段记录来源，冲突记录实际采用值或needs_input。模板锁定字段属于policy层；模板默认值属于template层。自然语言中的任意代码不成为生成器参数。

有效快照包含选中库、active generation与实际document_version_ids。未选KB时knowledge_scope=[]；执行前再核对资料未删除、权限未撤销。任务不能使用旧generation绕过当前删除过滤。若库重建导致老索引已清理，则提示范围需重新解析，创建新attempt；不得悄换检索依据。文件快照在权限有效时可供原任务恢复，但不得从已全局删除版本读取。

EffectivePreferences.snapshot_sha256 对去掉snapshot_sha256字段后的JSON采用RFC8785/JCS规范化UTF-8再SHA256。package.sha256同理排除sha256；其认证信任由发行清单/平台签名链提供，hash本身不等于来源认证。数据库profile/plan整体hash采用同一规范。实际开发需引入并测试完整JCS实现，不使用随意键排序冒充标准。

V0.1旧OfficePlan缺effective_preferences仍合法；V0.4.1+业务分发器要求存在且与数据库快照hash相符。模板/字段范围和版本检测由应用层执行，Schema合法不代表有权限执行。可验证排版/数字字段需检查，语气等软要求在结果中可反馈重做。

## 3 领域覆盖、筛选与来源展开

包只能有发布允许列表内的adapter_id/version；所有topic/type/default ID唯一且存在。source的topic_ids/content_type_ids是该来源可覆盖选项，不代表来源内每篇文章都匹配。每个可选主题与类型组合必须映射至少一个source，否则在UI禁用并说明。有效source集合为各selection中同时满足所选任一主题、任一类型映射的source并集。后续文章相关性按相同topic/type语义及关键词筛选，不以source相关就全量推送。

同source_id跨包必须映射相同adapter版本与规范配置；冲突拒绝保存，不能随机选版本。展开后去重至多10源。关键词默认为任一词命中，空数组为不加关键词限制；主题与类型分别为组内OR、组间AND，关键词与其AND。时间严格HH:mm，timezone须是实际IANA库存在项；Schema无法验证完整时区目录。

订阅仅选published包。预置样例若来自历史快照需标时间，不承诺下一次必有新条目。发布至少一个真实医药包和4个实测官方栏目；合成第二领域fixture只验证架构，不显示给用户。在线包更新仅数据，无模型工具、shell或可执行模块。撤回强制停止受影响来源，新计划要求重新选择；旧日报仍可看。

## 4 保存、执行与升级事务

save在事务内检查expected_revision，展开目录源并形成完整快照，新建subscription_plan_revisions，更新plan指针，生成/复用内部subscriptions。内部source记录沿用watermark；取消主题不清空游标；重新启用使用7天回看，不承诺无限历史补采。旧source仅停用，不破坏已有文章关联。

时间改变时同事务创建schedule_revision。只改主题创建plan_revision，不必改schedule_revision；一个run在开始时以事务快照锁定当时有效plan_revision，写入schedule_runs外键，恢复该run沿用原修订。effective_from不可回溯，正在运行的run不切配置。当天已完成自动run即使改时间/内容也不自动重复；手动刷新独立run，费用限制仍按账户业务日共享。

所有新V0.3 run必须带plan_id/plan_revision；SQL nullable仅为兼容早期历史迁移。有旧source配置的升级须映射到相应published包，否则保留为停用并提示重新配置，不能猜主题或偷偷迁到新源。旧OfficePlan保留原语义。备份、迁移失败回滚与清理规则沿用data-invariants与Spec；开发时提供真实旧DB fixture。
