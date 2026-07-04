# ADR-004: Server-Sent Events over WebSocket for Streaming

**Status:** Accepted  
**Date:** 2026-06  
**Deciders:** Architecture team

---

## Context

LLM inference generates tokens incrementally. Users experience significantly better latency perception when tokens appear one at a time rather than waiting for the full response. This requires a streaming protocol between the gateway and the client.

Two protocols were evaluated: Server-Sent Events (SSE) and WebSocket.

Ollama's native streaming API already uses NDJSON (newline-delimited JSON) over HTTP — one JSON object per token. The gateway's job is to receive this stream and forward it to the client in a suitable format.

---

## Decision

Use **Server-Sent Events (SSE)** for streaming inference responses to clients.

The gateway proxies Ollama's NDJSON stream and re-emits each token as an SSE frame:

```
data: {"id":"hermes-stream","choices":[{"delta":{"content":"Hello"}}]}\n\n
data: {"id":"hermes-stream","choices":[{"delta":{"content":" world"}}]}\n\n
data: [DONE]\n\n
```

The stream terminates with `data: [DONE]` when Ollama signals `"done": true`.

---

## Alternatives Considered

**WebSocket**  
WebSocket is a full-duplex, persistent, bidirectional protocol. Advantages:
- Client can send messages mid-stream (e.g., stop generation)
- Lower per-message overhead after handshake
- Better for truly interactive conversations

Rejected for this version because:
- Adds protocol complexity (connection lifecycle, ping/pong, close handshakes)
- Requires WebSocket-aware proxies and load balancers
- Most LLM clients (curl, Python httpx, JavaScript fetch) can consume SSE natively without extra libraries
- The use case (token streaming) is unidirectional — the full-duplex capability of WebSocket is unused
- `StreamingResponse` in FastAPI/Starlette makes SSE trivial; WebSocket requires a separate handler and connection manager

**Long Polling**  
Client polls the server repeatedly for new tokens. Rejected outright — adds latency per token, wasteful for high token-rate models, complex buffering required.

**gRPC streaming**  
Efficient binary protocol with bidirectional streaming. Rejected because:
- Requires a Protobuf schema definition
- Browser clients require gRPC-Web proxy
- Overkill for a local developer tool
- Not natively supported by the OpenAI client libraries that users may already have

---

## Consequences

**Pros:**
- SSE is HTTP/1.1 — works through every reverse proxy, firewall, and browser natively
- `Content-Type: text/event-stream` is sufficient — no handshake, no upgrade
- `fetch()` EventSource API in browsers handles SSE without libraries
- OpenAI-compatible response format (`data: {...}` with `choices[].delta.content`) means existing OpenAI client libraries work with zero modification
- Time-to-first-token (TTFT) is easily measurable — first `data:` frame marks first token
- Error injection mid-stream is possible by emitting an error-payload data frame

**Cons:**
- SSE is unidirectional — client cannot stop generation mid-stream via the same connection (would need a separate HTTP DELETE or a cancel endpoint)
- No built-in backpressure — if the client consumes slowly, tokens buffer in the gateway's response buffer
- HTTP/1.1 connection-per-stream; HTTP/2 multiplexing mitigates this but requires explicit configuration

---

## Outcome

SSE selected. Implemented in `gateway/streaming.py` as an async generator yielded through FastAPI's `StreamingResponse`. TTFT tracked via `hermes_time_to_first_token_seconds` histogram. Covered by 4 tests in `tests/test_streaming.py`.
