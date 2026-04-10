# A2A CLI Reference

## Global Flags

| Flag | Description |
|------|-------------|
| `--auth <creds>` | Shorthand for `--svc-param Authorization=<creds>` — covers the Authorization header only; use `--svc-param` for any other header |
| `--svc-param k=v` | Service parameter (repeatable) — transmitted as HTTP headers for REST/JSON-RPC, or as gRPC metadata |
| `--transport rest\|jsonrpc\|grpc` | Force specific transport. Auto-detection inspects the URL path: `/a2a` suffix → REST, presence of `.well-known/agent.json` capabilities field → JSON-RPC, explicit `grpc://` scheme → gRPC |
| `--timeout <duration>` | Request timeout (default: 30s) |
| `--insecure` | Plaintext gRPC transport (disables TLS) |
| `-o json\|text` | Output format. `json` returns the raw Task/Message proto as JSON; `text` formats for human reading (default: text) |
| `-v` | Verbose output to stderr — shows transport selection, request/response headers |
| `--tenant <id>` | Tenant identifier |

## send

```
a2a send <url> [message] [flags]
  --task <id>      Continue existing task
  --context <id>   Group related tasks under one context ID
  --immediate      Fire-and-forget (non-blocking) — returns task ID without waiting
  --stream         Streaming response via SSE — only use if agent card declares streaming support
  --history <n>    Request n history messages in response
  --file <path>    Read message from JSON file
  --json <json>    Raw JSON Message object
  --parts <json>   Raw JSON parts array
```

## discover / get card

```
a2a discover <url> [--extended]
a2a get card <url> [--extended]    # alias for discover
```

`discover` is the canonical subcommand. `get card` is an alias — both are equivalent.
Use `--extended` to fetch the authenticated extended Agent Card (requires auth; only available
if `capabilities.extendedAgentCard` is `true` in the public card).

## get task

Use this to check task status or retrieve artifacts after a non-blocking send:

```
a2a get task <url> <task-id> [--history <n>]
```

## list tasks

```
a2a list tasks <url> [--page-token <token>]
```

Tasks are returned sorted by last-update time descending. Use `--page-token` with the
`nextPageToken` from the previous response to paginate.

## cancel

```
a2a cancel <url> <task-id>
```

Returns the updated Task. Cancellation is not guaranteed — if the task is already in a
terminal state, the CLI returns an error (`TaskNotCancelableError`).

## subscribe

```
a2a subscribe <url> <task-id>
```

Streams `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent` until the task reaches a
terminal state (`completed`, `failed`, `canceled`, `rejected`). The stream begins with the
current Task object. Exits with code 0 on clean terminal state; can be interrupted with Ctrl-C.
