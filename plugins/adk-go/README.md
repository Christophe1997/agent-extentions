# ADK-Go Plugin

Build production-grade AI agents with Google's Agent Development Kit (ADK) for Go.

## What is ADK-Go?

ADK (Agent Development Kit) for Go is a **code-first, framework-level toolkit** for building production-grade AI agents. It features:

- **Idiomatic Go**: Designed to leverage Go's concurrency and performance
- **Model-Agnostic**: Works with Gemini, OpenAI, or custom LLM implementations
- **Rich Tool Ecosystem**: Function tools, MCP integration, built-in tools
- **Multi-Agent Patterns**: Sequential, parallel, and loop agent workflows
- **Production-Ready**: Session management, memory services, artifact storage

## Installation

```bash
go get google.golang.org/adk
```

## Skills

| Skill | Purpose |
|-------|---------|
| `adk-basics` | Core concepts, minimal agent setup, custom models |
| `adk-tools` | Function tools, MCP toolsets, HITL patterns |
| `adk-multi-agent` | Sequential, parallel, loop agents, handoffs |
| `adk-callbacks` | Callback system, plugins, state management |

## Commands

| Command | Description |
|---------|-------------|
| `/adk-go:init-agent` | Scaffold a new ADK agent project |
| `/adk-go:add-tool` | Add a new function tool to an agent |

## Agents

| Agent | Purpose |
|-------|---------|
| `adk-architect` | Help design ADK agent architectures and debug issues |

## Quick Start

```go
package main

import (
    "context"
    "google.golang.org/adk/agent/llmagent"
    "google.golang.org/adk/model/gemini"
    "google.golang.org/adk/runner"
    "google.golang.org/adk/session"
    "google.golang.org/genai"
)

func main() {
    ctx := context.Background()

    model, _ := gemini.NewModel(ctx, "gemini-2.5-flash", &genai.ClientConfig{
        APIKey: os.Getenv("GOOGLE_API_KEY"),
    })

    agent, _ := llmagent.New(llmagent.Config{
        Name:        "my_agent",
        Model:       model,
        Description: "A helpful assistant.",
        Instruction: "You are a helpful assistant.",
    })

    r, _ := runner.New(runner.Config{
        AppName:        "my_app",
        Agent:          agent,
        SessionService: session.InMemoryService(),
    })

    // Run the agent...
}
```

## Resources

- [ADK Documentation](https://google.github.io/adk-docs/)
- [Go Package Docs](https://pkg.go.dev/google.golang.org/adk)
- [GitHub Repository](https://github.com/google/adk-go)
- [Examples](https://github.com/google/adk-go/tree/main/examples)
