# 数据事务与一致性约束

SQL定义实体与局部约束；下列跨表不变量必须在应用事务与测试中实现。DDL不是已部署数据库，也没有替代真实PostgreSQL迁移测试。

1. grant: amount >= revoked + spent + reserved >=0。所有活跃allocation之和等于grant.reserved；settled账本之和与allocation.charged及grant.spent一致。以grant.id为最终稳定排序键消除同到期批次的不确定性。
2. run只有一次usage_ledger，已豁免不再追扣；provider_cost_events通过evidence_key去重，late/correction不改用户账。分配结算优先原预留批次顺序，charge不超过reserved。
3. paid并发/设备数先锁users行；grant修改、会员修改、run预留的事务锁顺序统一。数据库异常回滚后不能已派发服务商请求；派发必须在预留提交以后。
4. credential字段仅hash或配置引用。idempotency结果元数据不得保存一次性激活码或模型正文。refresh family重放整体撤销。
5. 本地操作只接受宿主授权ID。relative_path必须是产品根内的规范相对路径，不接受 ..、绝对路径和reparse逃逸；打开前再次验证。复制用完整文件，禁止硬链接继承源文件可写权限。
6. attempt终态CAS，取消/中断不能被迟到success覆盖。操作产物先staging，格式和hash通过后才创建ready artifact记录；数据库提交前后故障都有孤立文件回收机制。
7. KB有效chunk须经过documents、document_versions、kb_versions、chunks的删除/范围/状态检查。FTS或旧向量里仍残留条目，也不得在过滤后返回它。当前版本不依据上传时间自动认定。
8. active_generation须属于该KB，状态active，向量维度/模型/映射/hash一致。切换更新generation状态及kb指针在同一SQLite事务；准备完成的文件在事务前原子命名。崩溃旧代继续可用。
9. 对象引用由task_inputs、仍有效文档版本、模板等关系计算；清理前在事务中重新核对。删除单库关联不自动删除全局文档；全局删除立即tombstone、清理后保留最小失效元数据。删除后原文不可从历史引用打开。
10. source_ref的本地版本/网页元数据必须真实可对应；模型新建未知source_id不进入正式回答。OCR失败/截断均写coverage。
11. 资讯run的唯一键防同逻辑日重复；manual run另建但通知按schedule+logical_date+kind去重。修改日程保存revision记录。source watermark只在该源成功完成扫描时提交，partial不能跳过失败源。
12. article同URL改正文生成新revision；A→B→A也是新版本，不用正文hash全局唯一阻止修订。重复处理同一抓取证据保持幂等，最新revision通过CAS更新。
13. schedule lease到期可回收，旧worker写回必须校验lease_owner/generation，避免恢复后僵尸进程覆盖新结果。通知先登记唯一记录再派发；崩溃后允许标发送状态未知，站内记录仍在，不重复自动骚扰。
14. DB备份必须一致；从备份恢复时校验对象hash、schema版本及索引manifest。FTS/向量可重建；没有原对象不得假装重建成功。

15. 自动资讯daily budget按账户和固定业务日共用，首次预留快照的预算取floor(available*5/100)与绝对上限较小者；预算预留/结算及请求次数与run同事务更新。阶段失败、取消、双设备、重启或日程时区改变不能绕过计数。
16. FTS写入按chunk_id事务内删除旧行再写，generation查询显式关联generation_chunks；虚表本身不提供业务唯一和删除隔离。partial库版本默认不参与，只有用户允许并已发布索引后方可进入结果。

17. office profile revision、domain package version、subscription plan revision内容不可原地修改；默认profile及当前revision指针在事务中更新。每个owner_user_id至多一个有效默认profile和一个daily计划；跨账号访问先拒绝。
18. Office有效要求与计划同时锁定hash/版本/依据范围；改变个人配置不改历史，执行仍检查删除和授权。新增V0.4计划必须含快照，兼容字段nullable不代表业务可省略。
19. 订阅保存须按已发布包重新展开sources并校验<=10；一次run锁定plan_revision及包版本。撤回包暂停受影响来源，partial不移动失败源watermark；内容改动不重置预算、通知唯一键或已完成逻辑日。
20. 域包来源配置只引用固定adapter允许列表；hash完整性与来源认证分别验证。实际升级使用编号迁移与一致备份；新增表的DDL可执行不能替代旧数据迁移演练。
