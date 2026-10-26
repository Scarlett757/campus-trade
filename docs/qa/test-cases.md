# 核心接口测试用例

用例由 `tests/test_auth.py` 和 `tests/test_core_api.py` 执行。参数化数据会展开为独立 pytest case。

| ID | 场景 / 输入类别 | 预期结果 | 自动化实现 |
|---|---|---|---|
| AUTH-01 | 正常注册，验证码匹配且未过期 | 返回成功；密码为哈希；验证码删除 | `test_register_boundary` |
| AUTH-02 | 邮箱为空 | 注册失败，不创建用户 | `test_register_boundary` |
| AUTH-03 | 密码为空 | 注册失败，不创建用户 | `test_register_boundary` |
| AUTH-04 | 邮箱已注册 | 注册失败，原用户保留 | `test_register_boundary` |
| AUTH-05 | 正确密码登录 | 返回成功并设置登录 session | `test_login_boundary` |
| AUTH-06 | 用户不存在、密码错误或邮箱/密码为空 | 返回统一认证失败结果 | `test_login_boundary` |
| OTP-01 | 空邮箱、空字符串或格式错误邮箱申请验证码 | 不发送邮件 | `test_email_code_endpoint_does_not_send_for_invalid_email` |
| OTP-02 | 有效邮箱且邮件发送成功 | 返回成功并保存 6 位数字验证码 | `test_email_code_endpoint_persists_code_after_successful_send` |
| OTP-03 | 邮件发送失败 | 返回失败，不保存验证码 | `test_email_code_endpoint_does_not_persist_when_delivery_fails` |
| OTP-04 | 注册时邮箱与验证码邮箱不一致 | 注册失败 | `test_registration_rejects_mismatched_invalid_or_expired_codes` |
| OTP-05 | 错误验证码 | 注册失败 | `test_registration_rejects_mismatched_invalid_or_expired_codes` |
| OTP-06 | 验证码超过 30 分钟 | 注册失败 | `test_registration_rejects_mismatched_invalid_or_expired_codes` |
| OTP-07 | 验证码时间晚于当前时间 | 注册失败 | `test_registration_rejects_mismatched_invalid_or_expired_codes` |
| OTP-08 | 注册成功后重放同一验证码 | 重放失败，用户只有一条 | `test_registration_accepts_matching_recent_code_and_consumes_it` |
| ORD-01 | 未登录下单 | 重定向至登录页 | `test_login_required_order_endpoint_redirects_anonymous_request` |
| ORD-02 | 缺失 body、字段缺失、非整数 ID、零 ID | 返回 400，不创建订单、不扣库存 | `test_order_create_rejects_invalid_payloads` |
| ORD-03 | 正常下单 | 返回订单 ID；状态为 `paid`；库存减一；创建系统消息 | `test_create_order_decrements_stock_and_creates_order_with_message` |
| ORD-04 | 两个请求竞争最后一件商品 | 一个成功、一个失败；只产生一单；库存为零 | `test_concurrent_orders_cannot_oversell_single_unit` |
| ORD-05 | 库存为零 | 返回 400，不创建订单 | `test_order_rejects_sold_out_self_purchase_and_foreign_address` |
| ORD-06 | 买家购买自己的商品 | 返回 400，不创建订单 | `test_order_rejects_sold_out_self_purchase_and_foreign_address` |
| ORD-07 | 使用他人地址下单 | 返回 400，不创建订单 | `test_order_rejects_sold_out_self_purchase_and_foreign_address` |
| ORD-08 | 商品 ID 不存在 | 返回 404，不创建订单 | `test_order_create_returns_not_found_for_missing_product` |
| ORD-09 | 创建订单提交失败 | 返回 500；库存、订单、消息均回滚 | `test_order_failure_rolls_back_stock_and_order` |
| ORD-10 | 卖家发货 | 状态仅从 `paid` 迁移至 `shipped`，通知只写一次 | `test_only_seller_can_ship_and_repeated_transition_is_rejected` |
| ORD-11 | 买家发货或重复发货 | 买家返回 403；重复状态迁移返回 4xx | `test_only_seller_can_ship_and_repeated_transition_is_rejected` |
| ORD-12 | 读取买家/卖家订单列表 | 仅返回当前账号关联的订单 | `test_order_lists_are_scoped_to_logged_in_user` |
| SEC-01 | 未登录访问需登录的订单 API | 重定向至登录页 | `test_login_required_order_endpoint_redirects_anonymous_request` |
| SEC-02 | 订单非参与方读取或发送消息 | 返回 403，不泄露或写入消息 | `test_non_participant_cannot_access_order_messages` |
| SEC-03 | 订单非参与方打开聊天页 | 返回 403 | `test_non_participant_cannot_open_order_chat_page` |
| SEC-04 | 订单消息为缺失、空白或非字符串 | 返回 400，不写入消息 | `test_order_messages_reject_invalid_payloads` |
| SEC-05 | 修改、删除或设为默认的地址属于他人 | 返回 403，原地址不变 | `test_address_mutations_reject_another_users_address` |
