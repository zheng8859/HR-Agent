-- 首次初始化时由 docker-entrypoint-initdb.d 自动执行
-- 幂等：已存在则跳过
CREATE EXTENSION IF NOT EXISTS vector;
