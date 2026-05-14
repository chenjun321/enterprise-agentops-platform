# 运行与验证

## 本地启动

标准开发准备：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

如果本机没有 PostgreSQL，可以直接用 SQLite：

```bash
APP_ENV=development DATABASE_URL=sqlite:///./local_dev.db .venv/bin/python -c "from app.db.database import Base, engine, SessionLocal; from app.db.seed import seed_demo_data; Base.metadata.create_all(bind=engine); db = SessionLocal(); seed_demo_data(db); db.close()"
APP_ENV=development DATABASE_URL=sqlite:///./local_dev.db .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 测试

优先跑：

```bash
.venv/bin/python -m pytest -q
```

如果改了下面这些内容，至少重跑 smoke tests：

- 接口鉴权
- 生产配置
- trace 暴露策略
- executor 容错逻辑

## 生产约束

生产模式下注意：

- `INTERNAL_API_KEY` 必须配置
- `AUTH_TOKENS_JSON` 必须配置
- 默认关闭公开 docs
- 默认不向调用方暴露内部 trace

重点文件：

- `app/core/config.py`
- `app/security/auth.py`
- `app/main.py`
- `app/api/routes.py`

## 修改提醒

- 改客服链路时，注意 `support` 角色的数据可见范围
- 改工具权限时，同时检查 `app/security/policies.py`
- 改响应结构时，同时检查 `tests/test_smoke.py`
- 改数据库结构时，补 `migrations/versions/`
