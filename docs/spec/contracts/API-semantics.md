# API 语义补充（规范）

本目录描述本产品自有接口，不是官方 dsh 已有接口。`openapi.json` 管字段，本文补充授权、事务和失败行为。部署替换 example.invalid；不存在可调用的生产服务。

## 通用

- JSON UTF-8，控制请求体最多 2 MiB，模型请求体最多 8 MiB；模型文本按实际 tokenizer 再受上下文限制。V0.1 不接收任意远程图片 URL 或整份文件上传到网关。
- 时间 RFC3339 UTC，ID UUID，整数 unit 最大 2^53−1；输入整数乘费率使用 Python 整数/数据库数值，先算总和后一次向上取整。provider 金额为十进制字符串，绝不使用 float。
- 普通资源只允许拥有者读取。别人 run_id 返回 404，避免枚举；管理员需独立角色，公网后台强制受控网络或二次验证。只校验前端按钮不算授权。
- 查询列表按 created_at DESC,id DESC 做游标分页；cursor 签名/校验并绑定过滤条件；不得信任游标里的 user_id。limit 1—100，默认20。
- 业务错误见主 spec；400 malformed，401未认证，403无权益/停用，404不存在/非本人，409幂等/版本冲突，422参数，429限频，502上游明确失败，503平台不可用。所有错误都带 request_id，不返回堆栈/密钥/正文。
- 所有管理写、模型和搜索写请求要求 Idempotency-Key。唯一范围是 user_id + key，保存至少7天；记录 operation 与 body hash，不能跨接口复用同键。模型 body.request_id 与该 key 必须相同，其余接口 body.request_id（若有）也须相同。
- 同键同体不产生第二次业务副作用；同键异体409。模型重放只返回已有流/状态（无法再返回原流时HTTP 409，code=RUN_ALREADY_EXISTS，details.run_id），不能新派发。客户端用GET run查询。不会为了返回同样文字在服务端持久化推理正文。
- 单次秘密例外：激活码仅首次生成响应返回；幂等重放 activation_code=null + secret_unavailable=true，返回相同user_id。幂等元数据不保存激活码。需要新码走rotate-activation，旧码随即失效，完整审计。

## 认证/激活与设备

用户名规格默认3—128字符、去首尾空白、以归一化小写唯一键比较；显示名可保留原文。数据库 username 存规范值。邮箱可为空，仅作为联系信息，无邮件依赖。

activate仅用于存在、未过期、未使用的激活/密码重置码；设置密码并创建设备会话。密码重置完成撤销该用户此前所有refresh family。管理员rotate-activation在已激活用户上明确选password_reset，不静默修改密码；事件需原因，客户端提示恢复流程。

refresh一次性轮换，旧token再次使用视为重放并撤销整个family；绝对失效时间沿用初次登录30天，不随轮换无限延期。客户端访问凭据在宿主与系统凭据保护层处理。登出撤销当前family；停用/设备撤销会撤销相关family。所有付费请求实时校验账号和会员，停用不等待15分钟token过期。

设备installation_id为本机随机UUID，不采集硬件指纹；用户行锁保护设备计数。相同已激活设备重复登录不新增设备；第三设备超额返回DEVICE_LIMIT，后台可列出并撤销旧设备。被撤销设备的access也不能再发付费请求。

## 模型调用

`model_role=quality-assistant`为稳定产品别名；purpose仅用于chat/task/news预算和统计，不允许客户端选不授权路由。服务端添加平台硬约束，校验可见工具集合、消息序列、token/输出/成本上界、账号并发、未知结算和权益。

请求body、prompt、tool result只在转发内存里存在。APM、网关access log不记录body。服务端不接受任意Key、URL、温度或额外provider参数。模型工具名必须在对应发行版本的服务端白名单内；tool schema不能扩大本地broker权限。

预留事务先锁user行再按expires_at,id锁grant，所有路径一致防死锁；再更新预留、分配、run和幂等记录，提交后才派发。并发数以数据库活动状态判定，不能只用进程内Semaphore。尚未派发的进程崩溃由恢复任务释放；已标dispatched但服务商接收未知则pending核对，不当未派发处理。

首token超时默认120s，单run最大600s，总task仍受30min限制。HTTP断开向上游尝试取消，但不能据此归零收费。usage缺失时保持billing_state=pending_usage，执行state可completed/cancelled/unknown；二者独立。

服务端每分钟扫描待核对run；若服务商提供按request_id查询用量，有限调用其官方接口，否则记录不可得。72h后用户预留释放并豁免，迟到usage只作成本证据。预留超过实际扣减差额释放；超过预留的实际应扣平台承担并暂停问题路由。结算分录与grant聚合在一个数据库事务内更新，调用账本只写一次。

SSE首次响应前的错误为HTTP JSON；流开始后的错误发error事件，随后final（能正常收尾时）。异常断开且无final视为未知，不当作成功。心跳15s SSE注释；可保留内存短缓存最多5分钟帮助原连接恢复，但不得依赖缓存实现账本正确性。GET run只含状态/usage/额度，不返回完整回复；本地partial文字可保留，用户重试会创建新付费调用。

## 搜索

search/read均需有效membership和web_search功能，默认不扣unit但计运营成本。每账户每分钟最多10个搜索及30次正文读取，任务上限按主 spec；所有实例共用数据库/网关限流。source_id绑定当次用户，read提交的URL必须匹配该source允许的URL并通过每跳SSRF检查，不允许借source_id抓任意内网。

搜索正文不在服务端落盘；客户端可本地保存来源与必要摘录。服务端只记录query/body的hash、成本与状态。搜索失败可恢复，但同键不能再产生未知的重复收费；提供商查询无幂等机制时，记录已知状态并由用户新请求。

## 管理与成本

UserAdmin.version对应users.version，改会员/发grant也在用户行锁内提升该版本；Grant.version对应grant自身版本。Run.version用于核对操作。用户停用撤销session；会员缩短只阻止新调用，已派发调用照原预留结算。

grant.amount是最初发放量，revoked/spent/reserved均非负且总和不超过amount。撤销amount只能占当前未使用未预留部分，生成审计；不得更新usage_ledger。未来订单可以写origin_ref，但该字段不证明已付款。

AdminRun包含provider/route/price_card与成本，普通Run不包含平台价格；provider_cost_amount的汇总从幂等cost events得到，修正用delta追加，不能把累计值重复加总。成本未知显示null，不能显示为0冒充没有成本。

余额界面各字段只统计当前有效grant；`valid_grants_total_units = available + reserved + used`（扣除revoked），历史全部扣减通过usage列表查看。服务端系统成本预算单独统计，不作为用户余额。

自动资讯的purpose由宿主任务类型绑定。服务端在账户业务日（Asia/Shanghai）第一次news调用前快照余额，整数计算floor(available*5/100)，与已冻结绝对上限取较小值；feature_daily_budgets与run预留/结算同事务更新，派发计数每天最多2。跨设备或日程时区变更不重置。释放失败预留可返预算，但已派发次数不返；未派发失败不消耗次数。

Office计划中table布局必须有table_data，chart布局必须有chart_data；各行列和series长度匹配。append_table/append_image只用于支持的生成格式，aggregate_range只用于xlsx；其余operation/step兼容矩阵、目标存在性、用户输入来源与公式白名单由broker业务验证，不因通过JSON Schema就直接执行。
