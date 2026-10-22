# SSE 事件协议

Content-Type: text/event-stream；Cache-Control: no-store；代理禁用缓冲。每条data是完整JSON envelope：event_id UUID、run_id UUID、seq从1递增、type、data。event字段等于type，id等于event_id；15s心跳用注释。客户端忽略已处理的seq，不执行半条事件。

| type | data必填字段 | 语义 |
| --- | --- | --- |
| run.created | request_id, reserved_units, route_version | 已完成预留，后续将派发/已派发 |
| text.delta | text | 追加可见文字；不代表最终成功 |
| tool.delta | index, arguments_delta；tool_call_id/name_delta可选 | 同index聚合工具调用，只有完整结束并通过schema才执行 |
| usage | uncached_input_tokens,cached_input_tokens,output_tokens,reasoning_tokens,source | 已获usage；reasoning为空或output子集，不重复计价 |
| error | code,message,retryable | 该调用错误，当前partial文字仍可保留 |
| final | state,billing_state,charged_units,finish_reason | 流结束；finish_reason=stop/tool_calls/cancelled/error/length；billing可仍待核对 |

一个run最多一个final，至少一个run.created；正常completed必须final。usage可只有最后一条真实快照，禁止将多个累计usage片段相加。重复final是传输重放时客户端幂等忽略，服务端账本仍只结一次。工具调用结束在final.finish_reason=tool_calls后聚合执行，再发起新的model run继续Agent任务。

执行状态state=reserved/dispatched/streaming/completed/failed/cancelled/unknown；结算状态billing_state=held/settled/pending_usage/released/waived_unknown。最终charged_units未知为null，不强行填0。

SSE正文不落服务端数据库；断流通过GET run查询状态，不把旧POST重新当新调用发送。服务端已存在调用的POST重放返回409 RUN_ALREADY_EXISTS及run_id时，客户端按已存在调用处理。
