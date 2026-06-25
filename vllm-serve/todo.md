# Phase 1 — Understand vllm-serve Repo

> **Goal**: Deeply understand how vLLM and FastAPI are wired together.
> No new features. Read, annotate, fix, test with a real GPU.

---

## 1. Read & Annotate Source Files

- [ ] **config.py** — understand `pydantic-settings` pattern
  - [ ] Why `env_prefix = "SERVE_"`? How does it read from `.env`?
  - [ ] Why are some fields `Optional` (e.g. `quantization: str | None`)?
  - [ ] Add inline comments explaining each setting group (Model / Engine / Server)

- [ ] **models.py** — understand OpenAI-compatible schema design
  - [ ] Why does `ChatRequest` default `model` from `settings.model`?
  - [ ] Trace how `Message → ChatRequest → Choice → ChatResponse` chains together
  - [ ] Understand `DeltaMessage` vs `Message` — why two separate classes for streaming?
  - [ ] Add inline comments explaining each field's purpose

- [ ] **engine.py** — understand vLLM internals
  - [ ] What is `AsyncLLMEngine`? Why `Async` (vs sync `LLMEngine`)?
  - [ ] What is `AsyncEngineArgs`? Which args matter most for GPU memory?
  - [ ] What is `SamplingParams`? Understand: `temperature`, `top_p`, `top_k`
  - [ ] What is `RequestOutputKind.DELTA` vs `CUMULATIVE`? Why does streaming need DELTA?
  - [ ] Read vLLM docs: what is PagedAttention in plain words?
  - [ ] Add inline comments

- [ ] **app.py** — understand FastAPI + streaming
  - [ ] What is `@asynccontextmanager lifespan`? Why is it better than `@app.on_event`?
  - [ ] Trace `POST /v1/chat/completions` → `_apply_chat_template` → `engine.generate` → response
  - [ ] Understand `StreamingResponse` + `text/event-stream` — what is SSE?
  - [ ] Understand `async for output in engine.generate(...)` — what does each iteration yield?
  - [ ] What does `output.finished` mean? Why is it the loop break condition?
  - [ ] Why does streaming yield `data: [DONE]\n\n` at the end? (OpenAI SSE convention)
  - [ ] Add inline comments

---

## 2. Draw the Request Flow

- [ ] Draw the full lifecycle of a **non-streaming** request:
  ```
  curl POST /v1/chat/completions
    → FastAPI validates ChatRequest (Pydantic)
    → _apply_chat_template (tokenizer formats messages)
    → build_sampling_params
    → engine.generate (async generator)
    → collect final output
    → return ChatResponse JSON
  ```
- [ ] Draw the full lifecycle of a **streaming** request:
  ```
  curl POST /v1/chat/completions (stream=true)
    → StreamingResponse wraps _stream() async generator
    → engine.generate yields DELTA chunks
    → each chunk → StreamChunk JSON → "data: ...\n\n"
    → final "[DONE]" sentinel
  ```

---

## 3. Fix Security Issue

- [ ] **engine.py line 22**: HF token is hardcoded — move it to use `settings.hf_token`
  - Current: `hf_token='abc'`
  - Fix: `hf_token=settings.hf_token`
  - Verify `.env.example` already has `HF_TOKEN=` placeholder

---

## 4. Understand the Dockerfile

- [ ] Why use `vllm/vllm-openai` as base image (not plain Python)?
- [ ] Why install only `fastapi`, `uvicorn`, `pydantic-settings` — not `vllm` itself?
- [ ] Why `--no-deps` when installing the project package?
- [ ] What does `EXPOSE 8000` do vs `-p 8000:8000` in `docker run`?
- [ ] What is `uv` and why use it instead of `pip`?

---

## 5. Manually Test with Real GPU

- [ ] Start the server: `uv run vllm-serve`
- [ ] Test non-streaming:
  ```bash
  curl http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "Hello!"}], "stream": false}'
  ```
- [ ] Test streaming:
  ```bash
  curl http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "Hello!"}], "stream": true}'
  ```
- [ ] Call `GET /v1/models` — confirm model name matches `.env`
- [ ] Call `GET /health` — confirm `{"status": "ok"}`
- [ ] Try changing `temperature` and `top_p` — observe output differences

---

## Done Criteria

- [ ] Every source file has inline comments you wrote yourself
- [ ] You can explain the full streaming request flow without looking at code
- [ ] Security fix committed (no hardcoded token)
- [ ] All manual curl tests pass against the live server
