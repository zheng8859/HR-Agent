# HR Agent 后端生产镜像（FastAPI + uvicorn）
# 构建: docker build -t hragent-backend:1.0.0 ./hragent-backend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先复制依赖清单，利用层缓存：仅依赖变化才重建安装层
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码与迁移脚本
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# 非 root 运行；预置上传目录
RUN useradd --create-home --shell /usr/sbin/nologin hragent \
    && mkdir -p /app/uploads \
    && chown -R hragent:hragent /app
USER hragent

EXPOSE 8000

# 数据库迁移在启动前由部署脚本执行（docker compose run backend alembic upgrade head）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
