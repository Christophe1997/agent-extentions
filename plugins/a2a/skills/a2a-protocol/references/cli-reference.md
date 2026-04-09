# A2A CLI Reference

## Global Flags

| Flag | Description |
|------|-------------|
| `--auth <creds>` | Shorthand for `--svc-param Authorization=<creds>` |
| `--svc-param k=v` | Service parameter (repeatable) — passed as HTTP headers |
| `--transport rest\|jsonrpc\|grpc` | Force specific transport (default: auto-detect) |
| `--timeout <duration>` | Request timeout (default: 30s) |
| `--insecure` | Plaintext gRPC transport |
| `-o json\|text` | Output format (default: text) |
| `-v` | Verbose output to stderr |
| `--tenant <id>` | Tenant identifier |

## send

```
a2a send <url> [message] [flags]
  --task <id>      Continue existing task
  --context <id>   Group related tasks
  --immediate      Fire-and-forget (non-blocking)
  --stream         Streaming response (SSE)
  --history <n>    Request n history messages in response
  --file <path>    Read message from JSON file
  --json <json>    Raw JSON Message object
  --parts <json>   Raw JSON parts array
```

## discover / get card

```
a2a discover <url> [--extended]
a2a get card <url> [--extended]
```

## get task

```
a2a get task <url> <task-id> [--history <n>]
```

## list tasks

```
a2a list tasks <url> [--page-token <token>]
```

## cancel

```
a2a cancel <url> <task-id>
```

## subscribe

```
a2a subscribe <url> <task-id>
```
Streams `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent` until task reaches terminal state.
