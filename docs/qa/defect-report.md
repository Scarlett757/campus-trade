# 缺陷报告

以下缺陷由核心链路检查确认，并由相应自动化用例锁定回归行为。

| ID | 严重度 | 缺陷 | 修复 | 回归用例 |
|---|---|---|---|---|
| DEF-01 | 高 | 下单使用库存读取后再普通扣减，并发请求可能同时看到有货并超卖。 | 使用带 `num > 0`、非本人商品条件的原子 SQL 更新；检查受影响行数。 | `test_concurrent_orders_cannot_oversell_single_unit` |
| DEF-02 | 高 | 订单和系统消息分两次提交，第二次提交失败会留下无完整通知的订单。 | 库存更新、订单和系统消息放入同一事务，失败统一回滚。 | `test_order_failure_rolls_back_stock_and_order` |
| DEF-03 | 高 | 非订单参与者可打开聊天页面；消息 API 虽有权限检查，页面路由本身未检查参与者。 | 聊天页面加载订单并验证当前用户为买家或卖家。 | `test_non_participant_cannot_open_order_chat_page` |
| DEF-04 | 中 | 验证码未限制未来创建时间，成功注册后也未消费，增加重放窗口。 | 限定验证码年龄为 `[0, 30 分钟]`；注册成功时与用户创建同事务删除验证码。 | `test_registration_rejects_mismatched_invalid_or_expired_codes`、`test_registration_accepts_matching_recent_code_and_consumes_it` |
| DEF-05 | 中 | 后端生成 4 位验证码，但注册页面提示用户输入 6 位。 | 生成 6 位数字验证码并验证邮件发送及持久化结果。 | `test_email_code_endpoint_persists_code_after_successful_send` |
| DEF-06 | 中 | 下单和订单消息接口直接读取 JSON 字段，缺少 body 或字段类型不对时可能进入异常分支。 | 对 JSON 对象及必要字段做显式校验，错误输入返回 400。 | `test_order_create_rejects_invalid_payloads`、`test_order_messages_reject_invalid_payloads` |
| DEF-07 | 低 | 验证码接口只判断邮箱是否为空，格式错误仍会触发邮件发送尝试。 | 发送邮件前验证邮箱基本格式。 | `test_email_code_endpoint_does_not_send_for_invalid_email` |

## 未关闭的覆盖边界

- `OrderStatus.COMPLETED` 和 `CANCELLED` 目前没有对应状态迁移 API；需先明确收货确认、取消权限及取消后的库存恢复策略，再补充实现与测试。
- 并发回归在 SQLite 临时库运行，尚未在目标 MySQL 版本上进行真实并发压测。
- 验证码发送频率限制尚未实现，本次仅覆盖格式、发送失败、有效期、邮箱匹配和一次性使用。
