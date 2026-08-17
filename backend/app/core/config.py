import os
import toml
from pathlib import Path
from typing import Optional
from functools import lru_cache


def _parse_int(value) -> Optional[int]:
    if value == "" or value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config.toml"
            )

        self.config_path = Path(config_path).resolve()
        self._config = toml.load(config_path)
        # Model config split: every model-related setting (LLM / ASR / TTS /
        # embedding / rerank / judge / verifier / subagent / validator /
        # memory / title / providers) lives in config_model.toml, merged
        # OVER the main file so config.toml stays a pure infra file. When the
        # model file is absent (legacy deployments) the main file's sections
        # remain authoritative — every property below is unchanged.
        self.model_config_path = self._resolve_model_config_path(config_path)
        self._config = self._merge_model_config(self._config)

    @staticmethod
    def _resolve_model_config_path(config_path: str) -> Optional[Path]:
        env_override = os.environ.get("CONFIG_MODEL_PATH")
        if env_override:
            return Path(env_override).resolve()
        main = Path(config_path).resolve()
        candidate = main.parent / "config_model.toml"
        return candidate if candidate.exists() else None

    # Sections that belong to config_model.toml. Whole-section moves:
    _MODEL_SECTIONS = {
        "api",               # legacy main LLM endpoint
        "defaults",          # default LLM sampling params
        "default_assistant", # assistant-scoped sampling params
        "asr",               # speech recognition models
        "voice",             # voice LLM / TTS / ASR tuning
        "providers",         # multi-provider LLM routing
        "deathmatch",        # judge / verifier models + goal-loop budgets
        "sub_agent",         # subagent LLM params
        "title_generation",  # title LLM params
        "memory",            # memory LLM / embedding / rerank / cost models
    }
    # [agent] stays in the main file for harness tuning, but its MODEL
    # sub-sections move. Only these keys are taken from the model file.
    _MODEL_AGENT_SUBSECTIONS = {
        "auxiliary",      # per-task auxiliary models (coordinator/classifier/title/…)
        "compression",    # context-compression model params
        "moa",            # mixture-of-agents models
        "memory",         # daily summary / dream models
        "tool_digest",    # subagent tool-result digest model
        "sub_agent",      # subagent model params
    }

    def _merge_model_config(self, base: dict) -> dict:
        if self.model_config_path is None:
            return base
        import logging
        logger = logging.getLogger(__name__)
        try:
            model_cfg = toml.load(self.model_config_path)
        except Exception:
            logger.exception(
                "Failed to load %s — falling back to main config sections. "
                "If this deployment was already split, the server is now "
                "running with EMPTY/default model config and will fail on "
                "the first LLM call.",
                self.model_config_path,
            )
            return base
        merged = dict(base)
        for section in self._MODEL_SECTIONS:
            if section in model_cfg:
                if section in merged:
                    # Section-granular replacement: a partial model file
                    # REPLACES the whole main-file section. Warn so ops can
                    # spot missing keys (e.g. a hand-crafted model file with
                    # only [api].model_name would silently drop base_url/key).
                    logger.warning(
                        "config_model.toml section [%s] REPLACES the main "
                        "config.toml section of the same name (whole-section "
                        "override, not per-key merge)", section,
                    )
                merged[section] = model_cfg[section]
        if "agent" in model_cfg:
            agent = dict(merged.get("agent") or {})
            for key, value in (model_cfg.get("agent") or {}).items():
                if key in self._MODEL_AGENT_SUBSECTIONS:
                    agent[key] = value
            merged["agent"] = agent
        return merged

    def _resolve_project_path(self, value: str, *, default: str) -> Path:
        raw_value = value or default
        path = Path(raw_value)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    @property
    def database_type(self) -> str:
        """数据库后端：sqlite（默认，本地轻量）| postgres（与 chatbot 一致的 asyncpg）。"""
        t = str(self._config.get("database", {}).get("type", "sqlite")).strip().lower()
        if t not in ("sqlite", "postgres"):
            raise ValueError(
                f"[database].type 非法值 {t!r}（仅支持 sqlite / postgres）"
            )
        return t

    @property
    def database_url(self) -> str:
        db = self._config.get("database", {})
        if self.database_type == "sqlite":
            # path 相对于 backend/（config.toml 所在目录）解析为绝对路径，
            # 避免依赖启动时的 cwd；绝对路径需 4 斜杠（sqlite+aiosqlite:/// + /abs）。
            raw_path = db.get("path", "weave_note.db")
            return "sqlite+aiosqlite:///" + str((self.backend_root / raw_path).resolve())
        host = db.get("host", "localhost")
        port = db.get("port", 5432)
        username = db.get("username", "postgres")
        password = db.get("password", "")
        name = db.get("name", "chatllm")
        return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{name}"

    @property
    def database_pool_size(self) -> int:
        return int(self._config.get("database", {}).get("pool_size", 20))

    @property
    def database_max_overflow(self) -> int:
        return int(self._config.get("database", {}).get("max_overflow", 30))

    @property
    def database_pool_recycle(self) -> int:
        return int(self._config.get("database", {}).get("pool_recycle", 1800))

    @property
    def database_pool_timeout(self) -> int:
        return int(self._config.get("database", {}).get("pool_timeout", 30))

    @property
    def api_base_url(self) -> str:
        return self._config.get("api", {}).get("base_url", "https://api.openai.com/v1")

    @property
    def api_key(self) -> Optional[str]:
        key = self._config.get("api", {}).get("api_key", "")
        return key if key else None

    @property
    def security(self) -> dict:
        return self._config.get("security", {})

    @property
    def security_jwt_secret_key(self) -> Optional[str]:
        key = self.security.get("jwt_secret_key", "")
        if key:
            return key
        return os.environ.get("JWT_SECRET_KEY") or None

    @property
    def security_cors_allow_origins(self) -> list:
        origins = self.security.get("cors_allow_origins", ["*"])
        if isinstance(origins, str):
            return [origins]
        return list(origins)

    @property
    def security_cors_allow_credentials(self) -> bool:
        return bool(self.security.get("cors_allow_credentials", True))

    @property
    def model_name(self) -> Optional[str]:
        return self._config.get("api", {}).get("model_name") or None

    @property
    def server_host(self) -> str:
        return self._config.get("server", {}).get("host", "0.0.0.0")

    @property
    def server_port(self) -> int:
        return self._config.get("server", {}).get("port", 8158)

    @property
    def server_scheme(self) -> str:
        """Match the SSL auto-detection in scripts/start.sh: when key.pem and
        cert.pem exist in the backend directory, uvicorn is launched with
        --ssl-keyfile/--ssl-certfile, so the API is https."""
        key_pem = self.backend_root / "key.pem"
        cert_pem = self.backend_root / "cert.pem"
        return "https" if (key_pem.exists() and cert_pem.exists()) else "http"

    @property
    def project_root(self) -> Path:
        return self.config_path.parent.parent

    @property
    def backend_root(self) -> Path:
        return self.config_path.parent

    @property
    def defaults(self) -> dict:
        return self._config.get("defaults", {})

    @property
    def default_temperature(self) -> float:
        return self.defaults.get("temperature", 0.7)

    @property
    def default_top_p(self) -> float:
        return self.defaults.get("top_p", 1.0)

    @property
    def default_top_k(self) -> Optional[int]:
        val = self.defaults.get("top_k")
        return _parse_int(val)

    @property
    def default_presence_penalty(self) -> float:
        return self.defaults.get("presence_penalty", 0.0)

    @property
    def default_frequency_penalty(self) -> float:
        return self.defaults.get("frequency_penalty", 0.0)

    @property
    def default_max_tokens(self) -> Optional[int]:
        val = self.defaults.get("max_tokens")
        return _parse_int(val)

    @property
    def default_assistant(self) -> dict:
        return self._config.get("default_assistant", {})

    @property
    def default_assistant_name(self) -> str:
        return self.default_assistant.get("name", "默认助手")

    @property
    def default_assistant_system_prompt(self) -> str:
        return self.default_assistant.get("system_prompt", "")

    @property
    def default_assistant_temperature(self) -> float:
        return self.default_assistant.get("temperature", 0.7)

    @property
    def default_assistant_top_p(self) -> float:
        return self.default_assistant.get("top_p", 1.0)

    @property
    def default_assistant_top_k(self) -> Optional[int]:
        val = self.default_assistant.get("top_k")
        return _parse_int(val)

    @property
    def default_assistant_presence_penalty(self) -> float:
        return self.default_assistant.get("presence_penalty", 0.0)

    @property
    def default_assistant_frequency_penalty(self) -> float:
        return self.default_assistant.get("frequency_penalty", 0.0)

    @property
    def default_assistant_max_tokens(self) -> Optional[int]:
        val = self.default_assistant.get("max_tokens")
        return _parse_int(val)

    @property
    def workspace(self) -> dict:
        return self._config.get("workspace", {})

    @property
    def workspace_root(self) -> Path:
        return self._resolve_project_path(
            self.workspace.get("root_dir", "user_workspaces"),
            default="user_workspaces",
        )

    @property
    def workspace_use_project_venv(self) -> bool:
        return bool(self.workspace.get("use_project_venv", True))

    @property
    def workspace_create_readme(self) -> bool:
        return bool(self.workspace.get("create_readme", True))

    # ---- Browser skill ----

def get_config() -> Config:
    return Config()


def clear_config_cache() -> None:
    get_config.cache_clear()
