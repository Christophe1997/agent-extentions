---
name: init-agent
description: Scaffold a new ADK-Go agent project with proper structure
argument-hint: "[agent-name]"
allowed-tools: [Read, Write, Glob, Grep, Bash, Skill]
---

# Initialize ADK-Go Agent Project

Create a new ADK-Go agent project with the specified name.

## Steps

1. **Get agent name**: If not provided as argument, ask user for agent name (kebab-case, e.g., "weather-agent")

2. **Check if directory exists**: If `.` is provided, use current directory; otherwise create `{agent-name}/`

3. **Create project structure**:
```
{agent-name}/
├── main.go          # Entry point with runner setup
├── agent.go         # Agent configuration
├── tools.go         # Custom tools (if needed)
├── go.mod           # Go module file
└── README.md        # Project documentation
```

4. **Generate main.go**:
```go
package main

import (
    "context"
    "log"
    "os"

    "google.golang.org/genai"

    "google.golang.org/adk/agent"
    "google.golang.org/adk/cmd/launcher"
    "google.golang.org/adk/cmd/launcher/full"
)

func main() {
    ctx := context.Background()

    agent, err := NewAgent(ctx)
    if err != nil {
        log.Fatalf("Failed to create agent: %v", err)
    }

    config := &launcher.Config{
        AgentLoader: agent.NewSingleLoader(agent),
    }

    l := full.NewLauncher()
    if err = l.Execute(ctx, config, os.Args[1:]); err != nil {
        log.Fatalf("Run failed: %v\n\n%s", err, l.CommandLineSyntax())
    }
}
```

5. **Generate agent.go**:
```go
package main

import (
    "context"

    "google.golang.org/adk/agent/llmagent"
    "google.golang.org/adk/model/gemini"
    "google.golang.org/adk/tool"
    "google.golang.org/genai"
)

func NewAgent(ctx context.Context) (*llmagent.Agent, error) {
    model, err := gemini.NewModel(ctx, "gemini-2.5-flash", &genai.ClientConfig{
        APIKey: os.Getenv("GOOGLE_API_KEY"),
    })
    if err != nil {
        return nil, err
    }

    return llmagent.New(llmagent.Config{
        Name:        "{{AGENT_NAME}}",
        Model:       model,
        Description: "{{DESCRIPTION}}",
        Instruction: `{{INSTRUCTION}}`,
        Tools:       []tool.Tool{}, // Add tools here
    })
}
```

6. **Generate go.mod**:
```go
module {{AGENT_NAME}}

go 1.24

require google.golang.org/adk v0.0.0-latest
```

7. **Ask user for**: Description and Instruction for the agent

8. **Run `go mod tidy`** to fetch dependencies

## Output

Report created files and next steps:
- Add tools to `agent.go`
- Configure session/memory services if needed
- Run with `go run .`
