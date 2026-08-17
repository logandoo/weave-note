from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Float, Integer, JSON
from datetime import datetime
import uuid

from app.core.config import get_config
from app.db import migrations
from app.db.migrations import run_startup_migrations

import logging

logger = logging.getLogger(__name__)

config = get_config()

Base = declarative_base()

IS_SQLITE = config.database_type == "sqlite"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    agent_permissions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    notebooks = relationship("Notebook", back_populates="user", cascade="all, delete-orphan")
    workspace = relationship("UserWorkspace", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(512), unique=True, index=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")


class UserWorkspace(Base):
    __tablename__ = "user_workspaces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    root_path = Column(String(500), nullable=False)
    python_env_path = Column(String(500), nullable=True)
    node_workspace_path = Column(String(500), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="workspace")


class Notebook(Base):
    __tablename__ = "notebooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False, default="新笔记本")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notebooks")
    notes = relationship("Note", back_populates="notebook", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    notebook_id = Column(String(36), ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, default="")
    raw_transcription = Column(Text, nullable=True)  # Original voice transcription before editing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    notebook = relationship("Notebook", back_populates="notes")


class ExportTask(Base):
    __tablename__ = "export_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String(20), nullable=False, default="single")
    format = Column(String(10), nullable=False, default="pdf")
    note_id = Column(String(36), nullable=True)
    note_ids = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    progress = Column(Float, default=0.0)
    file_path = Column(String(500), nullable=True)
    filename = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
if IS_SQLITE:
    # SQLite（aiosqlite）：队列池默认即可；busy_timeout 防止写锁竞争直接抛
    # "database is locked"。WAL + foreign_keys 由 _register_sqlite_pragmas 施加。
    _engine_kwargs["connect_args"] = {"timeout": 30}
else:
    _engine_kwargs.update(
        pool_size=config.database_pool_size,
        max_overflow=config.database_max_overflow,
        pool_timeout=config.database_pool_timeout,
        pool_recycle=config.database_pool_recycle,
    )

engine = create_async_engine(config.database_url, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _register_sqlite_pragmas(target_engine) -> None:
    """SQLite 连接级 PRAGMA：WAL（并发读/写不互斥）+ 外键强制（SQLite 默认关闭）+ 忙等待。

    PRAGMA 是 per-connection 的（journal_mode 除外），必须挂 connect 事件；
    foreign_keys 关闭时 ON DELETE CASCADE 等约束不会生效。
    """
    from sqlalchemy import event

    @event.listens_for(target_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


def register_advisory_lock_cleanup(target_engine) -> None:
    """连接归还池时释放该会话持有的全部 session 级 advisory 锁。

    仅 PostgreSQL 后端需要（SQLite 无 advisory 锁概念）。
    背景（2026-08-10 线上事故）：memory scheduler 用 session 级 pg_try_advisory_lock
    做 per-user 互斥；当 per-user 处理异常（超时/事务中止）时 finally 里的 unlock 失败，
    锁随连接回池残留（SQLAlchemy 池 reset 只 rollback 事务、不释放 advisory 锁），
    导致 25/25 用户锁全部挂死在 idle 池连接上，调度器（扫描+consolidation）静默跳过
    所有用户。此监听器在每条连接归还时执行 pg_advisory_unlock_all() 根治泄漏类问题。
    失败必须留痕（降频 warn）：静默吞异常正是本次事故"无任何告警"的原罪。
    """
    from sqlalchemy import event

    _reset_failure_count = 0

    @event.listens_for(target_engine.sync_engine, "reset")
    def _reset_advisory_locks(dbapi_conn, record):
        nonlocal _reset_failure_count
        try:
            dbapi_conn.await_(dbapi_conn._connection.execute("SELECT pg_advisory_unlock_all()"))
        except Exception:
            # 失败路径安全（连接会被池 invalidate 关闭，session 锁随连接消亡自愈），
            # 但必须留痕：连续失败说明清理机制失效，不能回到静默状态。
            _reset_failure_count += 1
            if _reset_failure_count <= 3 or _reset_failure_count % 50 == 0:
                logger.warning(
                    "pg_advisory_unlock_all on pool reset failed (%d times so far) — "
                    "advisory lock cleanup may be broken", _reset_failure_count,
                )


if IS_SQLITE:
    _register_sqlite_pragmas(engine)
else:
    register_advisory_lock_cleanup(engine)


async def init_db():
    async with engine.begin() as conn:
        # weave-note 裁剪：先 create_all 再跑迁移——chatbot 的迁移假定表已由
        # 历史 create_all 建好，而 weave_note 是全新库，迁移里的 export_tasks
        # 外键引用 users(id) 需要先有表。
        if migrations.PGVECTOR_AVAILABLE:
            await conn.run_sync(Base.metadata.create_all)
        else:
            # §9.5：pgvector 缺失时 memory v2 表（含 vector 列）无法建，排除后照常启动
            memory_tables = {
                "memory_concepts", "memory_clusters", "concept_cluster_members",
                "concept_relations", "memory_clarifications", "subconscious_log",
                "memory_episodes", "memory_llm_calls",
            }
            tables = [t for t in Base.metadata.sorted_tables if t.name not in memory_tables]
            await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
        await run_startup_migrations(conn)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()