# ---- Base image ----
ARG BASE_IMAGE=vllm/vllm-openai:v0.11.0
FROM ${BASE_IMAGE}

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install the FastAPI wrapper deps (vllm/torch come from the base image)
RUN uv pip install --system --no-cache --break-system-packages \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.34" \
    "pydantic-settings>=2.7"

# Install the project (no-deps because vllm/torch are already satisfied)
COPY pyproject.toml .python-version ./
COPY src/ src/
RUN uv pip install --system --no-cache --break-system-packages --no-deps .

EXPOSE 8000

# HF_TOKEN must be injected at runtime — never baked into the image layer.
# Usage examples:
#   docker run --gpus all -p 8000:8000 \
#     -e SERVE_MODEL=meta-llama/Llama-3.1-8B-Instruct \
#     -e HF_TOKEN=<your_token> \
#     vllm-serve
#
# Or via Docker secrets / --env-file (preferred for CI/CD):
#   docker run --gpus all -p 8000:8000 --env-file .env vllm-serve
CMD ["python", "-m", "vllm_serve.app"]
