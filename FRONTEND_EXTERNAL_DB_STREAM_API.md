# RCA Agent Stream API — Frontend Integration Spec

Use this spec to integrate the **streaming** RCA chat endpoint in the frontend.

---

## 1. Endpoint

| Property | Value |
|----------|--------|
| **URL** | `https://prod-apis.prayog.io/pinelabs-agent/rca/external-db/stream` |
| **Method** | `POST` |
| **Request body** | JSON |
| **Response** | **Server-Sent Events (SSE)** — `text/event-stream` |

---

## 2. Request

### Headers

| Header | Value | Required |
|--------|--------|----------|
| `Content-Type` | `application/json` | Yes |
| `Accept` | `application/json` or `text/event-stream` | Optional (SSE works either way) |

### Body (JSON)

```json
{
  "user_query": "Analyze failure transactions"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_query` | string | **Yes** | Natural language question or analysis request. Cannot be empty or only whitespace. |

**Validation:** If `user_query` is missing or empty, the API returns **400 Bad Request** with an error message.

---

## 3. Response: Server-Sent Events (SSE)

- **Content-Type:** `text/event-stream`
- **Connection:** long-lived; server pushes events until the final `done` or `error`, then closes.

Each event has:
- **`event:`** — event type (e.g. `start`, `db`, `schema`, `done`, `error`)
- **`data:`** — one line of **JSON**. Parse this to get the payload.

Format per event:
```
event: <event_type>
data: <json_object>

```

---

## 4. Event Types and Payloads

Events arrive in order. Use them to show progress (e.g. “Connecting…”, “Analyzing…”, “Done”).

| Event | When | `data` shape | Notes |
|-------|------|--------------|--------|
| **start** | First event | `{ "message": "Starting RCA analysis" }` | Show “Starting…” |
| **db** | After DB connection | `{ "message": "Connecting to external Postgres" }` then `{ "message": "Connected to database: <db_name>" }` | Optional: show “Connected to DB” |
| **schema** | After schema cache check | `{ "cached": true }` or `{ "cached": false }`; later possibly `{ "message": "Using cached schema embeddings" }` | `cached: true` = no EDA/embedding step |
| **eda** | Only if schema not cached | `{ "message": "Running column-wise EDA on external database" }` then `{ "message": "EDA complete: analyzed <N> columns" }` | First time only; can take a while |
| **embedding** | Only if schema not cached | `{ "message": "Generating schema embeddings" }` then `{ "message": "Schema embeddings stored in vector DB" }` | First time only |
| **agent** | Before RCA agent runs | `{ "message": "Starting RCA agent" }` | Agent is thinking / calling tools; no further progress events until **done** or **error** |
| **done** | Success | `{ "rca_report": "<full markdown/text report>" }` | **Final success.** Use `rca_report` as the chat response (e.g. render as markdown). |
| **error** | Any failure | `{ "message": "<error description>" }` | **Final failure.** Stream ends. Show `message` to the user. |

**Important:** There are no separate `tool` or `llm` events in the current implementation. Between **agent** and **done**/ **error** the connection is open but no further events are sent until the final result.

---

## 5. Typical Event Sequence

**First time (schema not cached):**
```
start → db (×2) → schema (cached: false) → eda (×2) → embedding (×2) → agent → done
```

**Subsequent requests (schema cached):**
```
start → db (×2) → schema (cached: true, then message) → agent → done
```

**On error (any stage):**
```
start → … → error
```
After `error`, no `done` is sent.

---

## 6. Frontend Implementation Notes

### 6.1 Consuming SSE

- Use **EventSource** only for GET. For **POST** you must use **fetch** with `body` and then read the response body as a stream, or use a library that supports POST + SSE (e.g. `fetch` + manual parsing of `ReadableStream`).
- Parse line by line: look for lines starting with `event:` and `data:`; accumulate `data` (there can be multiple lines per event; in this API it’s one line per event). Parse `data` as JSON.

### 6.2 Example (fetch + stream parsing)

Pseudocode:

1. `fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_query: '...' }) })`
2. Get `response.body` (ReadableStream).
3. Read chunks, split by `\n\n` (double newline = event boundary).
4. For each block, split by `\n`, find `event: X` and `data: Y`, parse `Y` as JSON.
5. Switch on `event`: update UI (start/db/schema/eda/embedding/agent), or on **done** set final message from `data.rca_report`, or on **error** set error from `data.message`.

### 6.3 Timeouts

- The connection can stay open for a long time (EDA + agent). Consider:
  - No aggressive read timeout so the stream can complete.
  - Showing a “Still analyzing…” state after **agent** until **done** or **error**.

### 6.4 CORS

- API allows credentials and common headers (see backend CORS config). If the frontend is on a different origin, ensure the backend allows it; credentials may require specific CORS settings.

### 6.5 Displaying the result

- **Success:** Use `data.rca_report` from the **done** event. It’s plain text, often markdown (headings, lists, code). Render with a markdown renderer if desired.
- **Error:** Use `data.message` from the **error** event. Do not treat the stream as successful if you received **error**.

---

## 7. cURL Example

```bash
curl -X 'POST' \
  'https://prod-apis.prayog.io/pinelabs-agent/rca/external-db/stream' \
  -H 'Content-Type: application/json' \
  -d '{"user_query": "Analyze failure transactions"}'
```

You’ll see raw SSE lines; the last event should be either `event: done` with `data: {"rca_report":"..."}` or `event: error` with `data: {"message":"..."}`.

---

## 8. Non-stream alternative (optional)

If the frontend does not need progress and only needs the final report:

- **URL:** `POST https://prod-apis.prayog.io/pinelabs-agent/rca/external-db`
- **Body:** Same — `{ "user_query": "Analyze failure transactions" }`
- **Response:** Single JSON object, e.g. `{ "source": "external_postgres", "rca_report": "<text>", "schema_cached": true }`

Use the **stream** endpoint when you want to show progress and avoid long-request timeouts; use the non-stream one for simple request/response.

---

## 9. Summary for frontend

| Item | Detail |
|------|--------|
| **Endpoint** | `POST` `/pinelabs-agent/rca/external-db/stream` |
| **Request** | JSON body with required `user_query` (string) |
| **Response** | SSE stream (`text/event-stream`) |
| **Success** | Last event `done` → use `data.rca_report` |
| **Failure** | Event `error` → use `data.message`; no `done` |
| **Progress** | Use `start`, `db`, `schema`, `eda`, `embedding`, `agent` to drive progress UI |
