# 测试总结

## 执行结果

| 项目 | 结果 |
|---|---|
| 执行日期 | 2026-10-26 |
| 环境 | Windows，Conda `flask-env`，Python 3.10 |
| 执行命令 | `python -m pytest -q` |
| 用例数 | 47 |
| 通过 / 失败 | 47 / 0 |
| 总耗时 | 11.20 秒 |
| 邮件依赖 | mock SMTP；未发送真实邮件 |
| 数据库 | pytest 临时 SQLite 文件；未连接开发 MySQL |
| GitHub Actions | 成功，47 passed，10.51 秒；[run 40270783302](https://github.com/Scarlett757/campus-trade/actions/runs/40270783302) |

## 覆盖结论

- 9 个认证相关参数化用例覆盖注册、登录、验证码边界及密码哈希。
- 38 个 HTTP API 用例通过 `requests` 覆盖订单创建、最后一件库存并发竞争、发货状态迁移、订单列表、消息、地址权限和邮件验证码。
- 所有测试通过；并发最后一件商品只允许一笔订单成功。
- 对 6 个 Python 文件运行 `python -m py_compile`，未发现语法错误。
- pytest 显示 12 条 SQLAlchemy `Query.get()` 弃用警告；不影响本次用例结果。
- 首次远端运行因应用导入时提前初始化 MySQL engine 而失败；改为在导入应用前配置 SQLite，并加入 engine 后端断言后，远端运行通过。

## 风险与后续工作

- 本次并发回归验证了 SQLite 上的原子库存更新逻辑；上线前还需在实际 MySQL 版本、隔离级别及连接池条件下压测。
- 订单 `completed` / `cancelled` 状态没有 API；取消后库存如何恢复也需要先确定产品规则。
- 验证码发送频率限制/重发策略未纳入本次范围。
