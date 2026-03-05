---
name: adk-basics
description: ADK-Go fundamentals including agent creation, model configuration, runner setup, and session management. Use when building basic ADK agents, configuring Gemini or custom models, or understanding the core execution loop. Triggers on queries about "adk agent setup", "create llmagent", "gemini model config", "adk runner", "session service", "minimal adk example".
---

# ADK-Go Basics

Core concepts for building agents with Google's Agent Development Kit for Go.

## Core Execution Loop

```
runner.Run(userMessage)
  → BeforeRun (plugins)
  → BeforeAgent callbacks
  → [LLM loop]
      → BeforeModel callbacks  → model.GenerateContent()  → AfterModel callbacks
      → BeforeToolCallback     → tool.Run()               → AfterToolCallback
  → AfterAgent callbacks
  → AfterRun (plugins)
  → emit session.Event stream
```

## Package Map

| Package | Purpose |
|---|---|
| `google.golang.org/adk/agent` | Core context interfaces, agent base types |
| `google.golang.org/adk/agent/llmagent` | LLM-backed agent config & callbacks |
| `google.golang.org/adk/model` | `LLM` interface + request/response types |
| `google.golang.org/adk/model/gemini` | Built-in Gemini implementation |
| `google.golang.org/adk/runner` | Ties agent + services together |
| `google.golang.org/adk/session` | Session service, state, events |

## Minimal Agent

```go
import (
    "google.golang.org/adk/agent/llmagent"
    "google.golang.org/adk/model/gemini"
    "google.golang.org/adk/runner"
    "google.golang.org/adk/session"
    "google.golang.org/genai"
)

model, _ := gemini.NewModel(ctx, "gemini-2.5-flash", &genai.ClientConfig{
    APIKey: os.Getenv("GOOGLE_API_KEY"),
})

myAgent, _ := llmagent.New(llmagent.Config{
    Name:        "my_agent",
    Model:       model,
    Description: "A helpful assistant.",
    Instruction: "You are a helpful assistant. Always be concise.",
})

r, _ := runner.New(runner.Config{
    AppName:        "my_app",
    Agent:          myAgent,
    SessionService: session.InMemoryService(),
})

sess, _ := r.SessionService().Create(ctx, &session.CreateRequest{
    AppName: "my_app", UserID: "u1",
})

for event, err := range r.Run(ctx, runner.RunRequest{
    UserID:    "u1",
    SessionID: sess.Session.ID(),
    NewMessage: genai.NewContentFromText("Hello!", "user"),
}) {
    if event.IsFinalResponse() {
        fmt.Println(event.LLMResponse.Content.Parts[0].Text)
    }
}
```

## Custom Model (Non-Gemini)

Implement the `model.LLM` interface for any LLM:

```go
// model/llm.go — the contract
type LLM interface {
    Name() string
    GenerateContent(ctx context.Context, req *LLMRequest, stream bool) iter.Seq2[*LLMResponse, error]
}
```

```go
// Example: OpenAI adapter
type openAIModel struct {
    name   string
    client *openai.Client
}

func (m *openAIModel) Name() string { return m.name }

func (m *openAIModel) GenerateContent(
    ctx context.Context,
    req *model.LLMRequest,
    stream bool,
) iter.Seq2[*model.LLMResponse, error] {
    return func(yield func(*model.LLMResponse, error) bool) {
        msgs := convertContents(req.Contents)
        resp, err := m.client.Chat.Completions.New(ctx, ...)
        if err != nil { yield(nil, err); return }
        content := genai.NewContentFromText(resp.Choices[0].Message.Content, "model")
        yield(&model.LLMResponse{Content: content}, nil)
    }
}
```

## Session State

State is scoped by key prefix:

| Key prefix | Scope | Lifetime |
|---|---|---|
| `key` (no prefix) | Session | Until session deleted |
| `user:key` | User (all sessions) | Permanent per user |
| `app:key` | App (all users) | Permanent for app |
| `temp:key` | Invocation only | Discarded after run |

```go
// In a tool
ctx.Actions().StateDelta["my_key"] = "value"
val, _ := ctx.Session().State().Get("my_key")

// In agent instruction — auto-resolved at runtime
Instruction: "You speak {user:preferred_language}. App: {app:company_name}."

// OutputKey: store agent's final reply in state
llmagent.Config{ OutputKey: "last_reply" }
```

## Services Reference

| Service | In-Memory | Production-Ready |
|---|---|---|
| Session | `session.InMemoryService()` | `session/database` (SQL/SQLite via GORM) |
| Memory | `memory.InMemoryService()` | Implement `memory.Service` with vector DB |
| Artifact | `artifact.InMemoryService()` | `artifact/gcsartifact` (Google Cloud Storage) |

## See Also

- [adk-tools](../adk-tools) - Function tools, MCP integration
- [adk-multi-agent](../adk-multi-agent) - Multi-agent patterns
- [adk-callbacks](../adk-callbacks) - Callbacks and plugins
