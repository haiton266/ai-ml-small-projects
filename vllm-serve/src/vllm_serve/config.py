from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, sourced from environment variables or .env.

    Most settings use the ``SERVE_`` prefix (e.g. ``SERVE_MODEL``).
    The HuggingFace token is intentionally read from the plain ``HF_TOKEN``
    env var so it stays compatible with ``huggingface-cli login``, the HF Hub
    library, and standard CI/CD secret conventions.  It is typed as
    ``SecretStr`` so it is never printed in logs or stack traces.
    """

    model_config = SettingsConfigDict(
        env_prefix="SERVE_",
        env_file=".env",
        env_file_encoding="utf-8",
        # Let individual fields opt out of the prefix via their own alias
        populate_by_name=True,
    )

    # Model
    model: str = "meta-llama/Llama-3.1-8B-Instruct"
    tokenizer: str | None = None
    max_model_len: int | None = None

    # Engine
    tensor_parallel_size: int = 1
    gpu_memory_utilization: float = 0.90
    dtype: str = "auto"
    quantization: str | None = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    max_concurrent_requests: int = 256

    # Generation defaults
    default_max_tokens: int = 1024
    default_temperature: float = 0.7

    # HuggingFace authentication
    # Reads from HF_TOKEN (no SERVE_ prefix). Required for gated models such as
    # Llama 3, Gemma, or any other model that requires accepting a license on HF.
    # Provide it via:
    #   • .env file:         HF_TOKEN=hf_...
    #   • Shell export:      export HF_TOKEN=hf_...
    #   • Docker run flag:   -e HF_TOKEN=hf_...
    #   • K8s Secret:        valueFrom.secretKeyRef
    # NEVER hardcode the token value in source code.
    hf_token: SecretStr | None = Field(default=None, alias="HF_TOKEN")


settings = Settings()
