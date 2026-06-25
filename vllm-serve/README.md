# vllm-serve

A minimal, production-ready LLM serving stack using **vLLM** and **FastAPI**.

## Quickstart

```bash
# Install
uv sync

# Configure
cp .env.example .env
# Edit .env — set SERVE_MODEL and HF_TOKEN if using a gated model

# Run (requires a GPU)
# On WSL, add this first:
export VLLM_USE_V2_MODEL_RUNNER=0
export HF_TOKEN=hf_xxxxxxxxx
uv run vllm-serve

# Chat (streaming)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}], "stream": true}'
```

## Project structure

```
src/vllm_serve/
├── config.py    # All config via SERVE_* env vars + HF_TOKEN
├── models.py    # OpenAI-compatible request/response schemas
├── engine.py    # vLLM engine startup + sampling params
└── app.py       # FastAPI app, routes, streaming
```

## Configuration

All settings are environment variables. Most use the `SERVE_` prefix; the
HuggingFace token is the exception (see [HF_TOKEN](#hf_token) below).

| Variable | Default | Description |
|---|---|---|
| `SERVE_MODEL` | `meta-llama/Llama-3.1-8B-Instruct` | HuggingFace model ID |
| `SERVE_TENSOR_PARALLEL_SIZE` | `1` | Number of GPUs for tensor parallelism |
| `SERVE_GPU_MEMORY_UTILIZATION` | `0.90` | Fraction of GPU memory to use |
| `SERVE_QUANTIZATION` | `None` | Quantization method (`awq`, `gptq`, …) |
| `SERVE_MAX_MODEL_LEN` | `None` | Override max sequence length |
| `SERVE_DTYPE` | `auto` | Model dtype (`auto`, `float16`, `bfloat16`) |
| `SERVE_HOST` | `0.0.0.0` | Server bind address |
| `SERVE_PORT` | `8000` | Server port |
| `SERVE_MAX_CONCURRENT_REQUESTS` | `256` | Request queue depth |
| `SERVE_DEFAULT_MAX_TOKENS` | `1024` | Default generation length |
| `SERVE_DEFAULT_TEMPERATURE` | `0.7` | Default sampling temperature |

## HF_TOKEN

Some models (Llama 3, Gemma, Mistral-Nemo, …) are **gated** — you must accept
their license on HuggingFace before you can download them.

### Setup

1. Create an account at <https://huggingface.co>
2. Accept the model license on its model page
3. Create a **read** token at <https://huggingface.co/settings/tokens>
4. Add it to your environment — choose the method that matches your context:

**Local development (.env file)**
```bash
# .env — git-ignored, never commit this file
HF_TOKEN=hf_your_token_here
```

**Shell export (temporary)**
```bash
export HF_TOKEN=hf_your_token_here
uv run vllm-serve
```

**Docker (runtime injection)**
```bash
# Pass via -e flag
docker run --gpus all -p 8000:8000 \
  -e SERVE_MODEL=meta-llama/Llama-3.1-8B-Instruct \
  -e HF_TOKEN=hf_your_token_here \
  vllm-serve

# Or via --env-file (preferred — keeps the token out of shell history)
docker run --gpus all -p 8000:8000 --env-file .env vllm-serve
```

**Kubernetes (Secret)**
```bash
# Create the secret
kubectl create secret generic hf-secret \
  --from-literal=HF_TOKEN=hf_your_token_here

# Reference it in your Deployment manifest:
# env:
#   - name: HF_TOKEN
#     valueFrom:
#       secretKeyRef:
#         name: hf-secret
#         key: HF_TOKEN
```

**GitHub Actions**
```yaml
# Store HF_TOKEN as a masked repository secret, then inject it:
env:
  HF_TOKEN: ${{ secrets.HF_TOKEN }}
```

> **Security rules**
> - **Never** hardcode a token in source code or a `Dockerfile`.
> - **Never** commit `.env` to version control (already in `.gitignore`).
> - The token is stored internally as `SecretStr` — it will never appear in logs or stack traces.
> - Rotate the token immediately at <https://huggingface.co/settings/tokens> if you suspect exposure.

## Docker

```bash
docker build -t vllm-serve .

# Public model (no token needed)
docker run --gpus all -p 8000:8000 \
  -e SERVE_MODEL=Qwen/Qwen2.5-7B-Instruct \
  vllm-serve

# Gated model
docker run --gpus all -p 8000:8000 \
  -e SERVE_MODEL=meta-llama/Llama-3.1-8B-Instruct \
  -e HF_TOKEN=hf_your_token_here \
  vllm-serve
```

## Interactive docs

FastAPI auto-generates interactive API docs. Once the server is running:

- **Swagger UI** at <http://localhost:8000/docs> — try requests directly in the browser
- **ReDoc** at <http://localhost:8000/redoc> — clean read-only reference

Set `"stream": false` in the Swagger request body to see the full response inline.

---

## FAQ

### What is vLLM?

vLLM is a system designed specifically to run large language models efficiently
for inference (generating text). It doesn't train models, and it doesn't change
how models think. Its entire purpose is to make text generation faster, cheaper,
and able to support many users at the same time.

If you imagine an LLM as an engine, vLLM is a better engine mount and fuel
system — not a different engine.

### Why can't I just load a model in PyTorch and call `generate()`?

You absolutely can, and many people do at first. But that approach breaks down
very quickly.

When you call `generate()` directly, each request blocks GPU resources, memory
gets fragmented, concurrent users fight for GPU space, and throughput collapses.
While it works for one person experimenting, it does not scale. vLLM exists
because production systems need to handle many requests simultaneously, not
sequentially.

### What does vLLM do differently under the hood?

The key idea is that vLLM treats inference as a **systems problem**, not just a
model problem.

**PagedAttention** — Normally, attention layers allocate large continuous memory
blocks for each request's key-value cache. When different users send prompts of
different lengths, this wastes GPU memory. vLLM breaks memory into smaller
"pages" that can be reused and shared efficiently, similar to how an OS manages
virtual memory. This lets you serve 2–4× more concurrent requests on the same GPU.

**Continuous batching** — Instead of waiting for one request to finish before
starting another, vLLM dynamically groups requests together, even if they arrive
at different times or have different prompt lengths. The GPU stays busy doing
useful work instead of waiting.

### Does this change the quality of the model's output?

No. vLLM does not approximate, compress, or modify the model. The weights are
exactly the same. The math is exactly the same. Only how memory is managed and
how requests are scheduled changes. You get identical answers, just faster and at
scale.

Quantization is optional and separate. If you choose to quantize a model, that
does reduce precision, but vLLM itself does not force this.

### How is vLLM different from Ollama?

Ollama is designed for **simplicity and local usage**. It is great for running a
model on your laptop and chatting with it.

vLLM is designed for **throughput and concurrency**. It assumes you care about
how many requests per second you can handle and how efficiently you use GPU
memory.

Think of Ollama as a personal kitchen and vLLM as a restaurant kitchen. Both
cook food, but only one is designed for many customers at once.

### Where does FastAPI fit in?

FastAPI is the HTTP interface. vLLM doesn't care about HTTP, REST, or users
clicking buttons. FastAPI is what turns your model into a service that other
systems can talk to. It receives requests, passes them to vLLM, and returns the
responses.

vLLM has a built-in server, but wrapping it in FastAPI gives you full control:
custom endpoints, auth, rate limiting, request validation, middleware, health
checks for container orchestrators, and an OpenAI-compatible API so any OpenAI
SDK client works out of the box.

This is the standard pattern in production: vLLM handles the GPU and inference,
FastAPI handles everything between the client and the engine.

### What models work with vLLM?

vLLM supports most popular HuggingFace architectures: Llama, Mistral, Mixtral,
Qwen, Gemma, Phi, DeepSeek, Command R, and many more, including
vision-language models. See the full list at
[vLLM Supported Models](https://docs.vllm.ai/en/stable/models/supported_models/).

For gated models (like Llama), you need to accept the license on HuggingFace
and set `HF_TOKEN` — see [HF_TOKEN](#hf_token) above.

### Where is the model stored? Does it reload every time?

Models are downloaded from HuggingFace Hub the first time vLLM loads them.
Weights and tokenizer files are cached in `~/.cache/huggingface/hub/`, so
subsequent starts skip the download.

When a vLLM instance starts, it loads the model once into GPU memory. After
that, the model stays resident. Requests reuse the same loaded weights.
Reloading only happens when the process restarts.

### Isn't loading a huge model slow?

Yes, and that is by design. Model loading is a startup cost, not a per-request
cost. Once loaded, inference is fast. This is why production systems avoid
restarting inference processes frequently.

### What does tensor parallelism mean?

If a model is too large for one GPU, tensor parallelism splits it across
multiple GPUs on the same machine. Set `SERVE_TENSOR_PARALLEL_SIZE=2` (or more)
to use this.

This is different from running multiple independent copies of a model. With
tensor parallelism, one model uses multiple GPUs cooperatively to handle each
request.

### What about quantization?

Quantization reduces model precision (for example, from 16-bit to 4-bit) to fit
larger models into less GPU memory. vLLM supports methods like AWQ and GPTQ.
Set `SERVE_QUANTIZATION=awq` to enable it.

The tradeoff is a small reduction in output quality for a large reduction in
memory usage. For many use cases, the difference is negligible.

### Do I need Kubernetes or Ray to use this?

No. You can run vLLM as a normal process, load a model from HuggingFace, and
serve it through FastAPI locally. This project is designed to work exactly that
way.

Kubernetes is useful for deployment and scaling in production. Ray is useful
when you need to distribute inference across multiple machines. But neither is
required, and you should only add that complexity when you actually need it.

### What is the simplest way to explain vLLM?

vLLM is the system that turns a large language model from a single-user
experiment into a real, scalable service.
