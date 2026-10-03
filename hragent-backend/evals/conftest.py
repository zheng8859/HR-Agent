"""Evals 共享夹具入口（doc 42 §6.3 / §7：数据库连接、Golden 加载、API client、认证 token）。

夹具定义在 `tests/conftest.py`（PostgreSQL 测试库 + 评测用户/知识库），这里通过
`pytest_plugins` 将其注册为插件，使 `pytest evals/`（或后续把评测测试文件放到本目录）也能
复用同一套夹具：engine / db_session / client / evals_dir / eval_user / eval_kb / auth_headers。
"""
pytest_plugins = ["tests.conftest"]
