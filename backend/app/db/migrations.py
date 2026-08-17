import logging
import re

from sqlalchemy import text

logger = logging.getLogger(__name__)

_EXT_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


STARTUP_MIGRATIONS = [
    ("create_export_tasks", """CREATE TABLE IF NOT EXISTS export_tasks (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE NOT NULL,
        task_type VARCHAR(20) NOT NULL DEFAULT 'single',
        format VARCHAR(10) NOT NULL DEFAULT 'pdf',
        note_id VARCHAR(36),
        note_ids TEXT,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        progress FLOAT DEFAULT 0.0,
        file_path VARCHAR(500),
        filename VARCHAR(255),
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP
    )"""),
    ("users_agent_permissions", "ALTER TABLE users ADD COLUMN IF NOT EXISTS agent_permissions TEXT"),
]


# §9.5 pgvector 缺失降级：启动探测结果（run_startup_migrations 期间更新）。
# False 时 memory v2 迁移整体跳过、init_db 的 create_all 排除 memory 表、
# main.py 强制 memory.enabled=false —— 服务继续以旧记忆方案运行，不崩溃。
PGVECTOR_AVAILABLE = True

_MEMORY_MIGRATION_START = "pgvector_extension"

_VECTOR_TABLES = [
    ("subconscious_log", "embedding", "idx_sub_embedding"),
    ("memory_concepts", "embedding", "idx_concepts_embedding"),
    ("memory_episodes", "embedding", "idx_epi_embedding"),
    ("memory_clusters", "embedding", None),
]


async def probe_pgvector(conn, extension: str = "vector") -> bool:
    """§9.5 启动探测：pgvector 扩展是否可用（已安装或可创建）。

    SQLite 后端无 pgvector 概念，直接返回 False（memory 迁移整体跳过）。
    CREATE EXTENSION 失败（无权限/未安装）会被 PG 拒绝并使事务进入 aborted
    状态——savepoint 隔离保证探测失败不毒化调用方事务（init_db 后续
    create_all 依赖同一事务）。
    """
    if conn.dialect.name != "postgresql":
        return False
    if not _EXT_IDENT_RE.fullmatch(extension):
        logger.error("probe_pgvector: 非法扩展名标识符 %r", extension)
        return False
    try:
        async with conn.begin_nested():
            await conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
    except Exception:
        return False
    try:
        r = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = :ext"),
                               {"ext": extension})
    except Exception:
        # SELECT 失败属异常环境（事务已毒化等），与"扩展缺失"区分开——
        # 不当静默禁用：记录 warning 便于排查当次启动 memory 被禁的原因
        logger.warning("probe_pgvector: pg_extension 查询失败，按不可用处理", exc_info=True)
        return False
    return r.scalar() is not None


async def _reconcile_vector_dims(conn) -> None:
    """检测 DB 中 vector 列维度是否与配置 embedding_dim 一致，不一致则 ALTER 重建。

    典型场景：旧迁移创建 vector(1536)，用户切换 embedding 模型后配置改为 1024。
    """
    try:
        from app.core.config import get_config
        cfg = get_config()
        expected = int(cfg.memory.get("embedding_dim", 1536))
    except Exception:
        return

    for table, col, idx_name in _VECTOR_TABLES:
        try:
            async with conn.begin_nested():
                r = await conn.execute(text(
                    "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                    "WHERE attrelid = CAST(:tbl AS regclass) AND attname = :col AND NOT attisdropped"
                ), {"tbl": table, "col": col})
                fmt = r.scalar()
                if not fmt:
                    continue
                match = re.search(r"vector\((\d+)\)", fmt)
                if not match:
                    continue
                current = int(match.group(1))
                if current == expected:
                    continue
                logger.warning(
                    "vector dim mismatch: %s.%s is vector(%d), config expects %d — altering",
                    table, col, current, expected,
                )
                if idx_name:
                    await conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                await conn.execute(text(
                    f"ALTER TABLE {table} ALTER COLUMN {col} TYPE vector({expected})"
                ))
                if idx_name:
                    await conn.execute(text(
                        f"CREATE INDEX {idx_name} ON {table} USING hnsw ({col} vector_cosine_ops) "
                        f"WITH (m = 16, ef_construction = 64)"
                    ))
                logger.info("vector dim reconciled: %s.%s → vector(%d)", table, col, expected)
        except Exception:
            logger.warning("vector dim reconcile failed for %s.%s", table, col, exc_info=True)


async def run_startup_migrations(conn) -> None:
    global PGVECTOR_AVAILABLE
    # §9.5：无条件探测（ cheap + 幂等）——已记录 applied 的旧库亦需覆盖
    # “migration_versions 被恢复进无 pgvector 集群”场景，不能靠 applied 跳过探测
    PGVECTOR_AVAILABLE = await probe_pgvector(conn)

    await conn.execute(text(
        """CREATE TABLE IF NOT EXISTS migration_versions (
            version VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    ))

    versions = [v for v, _ in STARTUP_MIGRATIONS]
    mem_start = versions.index(_MEMORY_MIGRATION_START) if _MEMORY_MIGRATION_START in versions else len(STARTUP_MIGRATIONS)

    for idx, (version, statement) in enumerate(STARTUP_MIGRATIONS):
        if idx >= mem_start and not PGVECTOR_AVAILABLE:
            # memory v2 迁移块（pgvector_extension 起，必须保持连续后缀——
            # 由 tests/memory_md_round4_test.py #7 后缀纯度断言守护）整体跳过，
            # 不记录版本号，安装 pgvector 后重启可补跑
            if idx == mem_start:
                msg = (
                    "pgvector 扩展不可用（CREATE EXTENSION vector 失败或未安装）；"
                    "跳过 memory v2 全部迁移，memory 子系统将被禁用。"
                    "请安装 pgvector（如 brew install pgvector）并授予 CREATE EXTENSION 权限后重启。")
                try:
                    from app.core.config import get_config
                    _mem_requested = bool(get_config().memory.get("enabled")) or \
                        bool(get_config().memory.get("migration_enabled"))
                except Exception:
                    _mem_requested = True  # 配置读不出时按高调处理，不错过告警
                if _mem_requested:
                    logger.error(msg)
                else:
                    # memory 未开启时降级为 info，避免每次启动刷错误日志
                    logger.info(msg)
            continue

        result = await conn.execute(
            text("SELECT 1 FROM migration_versions WHERE version = :version"),
            {"version": version},
        )
        if result.scalar_one_or_none():
            continue

        if conn.dialect.name == "sqlite" and version == "users_agent_permissions":
            # SQLite 的 ALTER TABLE 不支持 IF NOT EXISTS ADD COLUMN：
            # users 表由 create_all 按模型建出（含 agent_permissions 列），
            # 列已存在则跳过，避免 SQL 语法错误。
            if await _sqlite_column_exists(conn, "users", "agent_permissions"):
                logger.info("migration users_agent_permissions skipped on SQLite (column already exists)")
                await conn.execute(
                    text("INSERT INTO migration_versions (version) VALUES (:version)"),
                    {"version": version},
                )
                continue

        await conn.execute(text(statement))
        await conn.execute(
            text("INSERT INTO migration_versions (version) VALUES (:version)"),
            {"version": version},
        )

    # 静态迁移跑完后，校验 vector 列维度是否与配置一致
    if PGVECTOR_AVAILABLE:
        await _reconcile_vector_dims(conn)


async def _sqlite_column_exists(conn, table: str, column: str) -> bool:
    """SQLite 方言列存在性检查（PRAGMA table_info）。非 SQLite 后端恒 False。"""
    if conn.dialect.name != "sqlite":
        return False
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result.fetchall())
