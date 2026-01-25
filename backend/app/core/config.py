import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LyceumDocBot API"
    secret_key: str = Field(validation_alias="SECRET_KEY")
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = Field(
        default_factory=list,
        validation_alias="CORS_ORIGINS",
    )
    database_url: str = Field(
        validation_alias="DATABASE_URL",
    )
    admin_email: str = Field(validation_alias="ADMIN_EMAIL")
    admin_password: str = Field(validation_alias="ADMIN_PASSWORD")
    docs_path: str = Field(default="/data/documents", validation_alias="DOCS_PATH")
    indexes_path: str = Field(default="/data/indexes", validation_alias="INDEXES_PATH")
    llm_provider: str = Field(default="stub", validation_alias="LLM_PROVIDER")
    ollama_base_url: str = Field(
        default="http://ollama:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(default="qwen3:4b-instruct", validation_alias="OLLAMA_MODEL")
    ollama_fallback_model: str = Field(default="qwen2.5:3b-instruct", validation_alias="OLLAMA_FALLBACK_MODEL")
    ollama_temperature: float = Field(default=0.1, validation_alias="OLLAMA_TEMPERATURE")
    ollama_top_p: float = Field(default=0.9, validation_alias="OLLAMA_TOP_P")
    ollama_top_k: int = Field(default=40, validation_alias="OLLAMA_TOP_K")
    ollama_repeat_penalty: float = Field(default=1.05, validation_alias="OLLAMA_REPEAT_PENALTY")
    ollama_num_predict: int = Field(default=256, validation_alias="OLLAMA_NUM_PREDICT")
    ollama_seed: str | None = Field(default=None, validation_alias="OLLAMA_SEED")
    ollama_stop: str = Field(default="", validation_alias="OLLAMA_STOP")
    retrieve_k_for_llm: int = Field(default=12, validation_alias="RETRIEVE_K_FOR_LLM")
    llm_sources_k: int = Field(default=7, validation_alias="LLM_SOURCES_K")
    ui_sources_k: int = Field(default=5, validation_alias="UI_SOURCES_K")
    llm_excerpt_chars: int = Field(default=1200, validation_alias="LLM_EXCERPT_CHARS")
    llm_sources_char_limit: int = Field(default=9000, validation_alias="LLM_SOURCES_CHAR_LIMIT")
    embedding_model_name: str = Field(
        default="intfloat/multilingual-e5-base",
        validation_alias="EMBEDDING_MODEL_NAME",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                return []
            if trimmed.startswith("["):
                try:
                    parsed = json.loads(trimmed)
                except json.JSONDecodeError:
                    return [item.strip() for item in trimmed.split(",") if item.strip()]
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                return [str(parsed)]
            return [item.strip() for item in trimmed.split(",") if item.strip()]
        return [str(value)]


settings = Settings()
