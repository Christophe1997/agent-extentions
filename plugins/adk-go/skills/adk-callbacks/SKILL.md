---
name: adk-callbacks
description: ADK-Go callback system and plugin architecture for cross-cutting concerns like telemetry, auth, caching, and state management. Use when implementing lifecycle hooks, adding middleware, or building plugins that apply across all agents. Triggers on queries about "callback", "beforemodel", "aftermodel", "beforeagent", "plugin", "adk plugin", "lifecycle hook".
---

# ADK-Go Callbacks & Plugins

Lifecycle hooks and cross-cutting concerns for ADK agents.

## Callback Reference

All callbacks are **first-non-nil wins** — the first callback returning a non-nil result short-circuits the rest.

| Callback | Signature | Short-circuits |
|---|---|---|
| `BeforeAgentCallback` | `func(CallbackContext) (*genai.Content, error)` | Skips entire agent run |
| `AfterAgentCallback` | `func(CallbackContext) (*genai.Content, error)` | Replaces agent output |
| `BeforeModelCallback` | `func(CallbackContext, *LLMRequest) (*LLMResponse, error)` | Skips LLM call (cache hit) |
| `AfterModelCallback` | `func(CallbackContext, *LLMResponse, error) (*LLMResponse, error)` | Replaces LLM response |
| `OnModelErrorCallback` | `func(CallbackContext, *LLMRequest, error) (*LLMResponse, error)` | Recovers from LLM error |
| `BeforeToolCallback` | `func(tool.Context, Tool, map[string]any) (map[string]any, error)` | Skips tool execution |
| `AfterToolCallback` | `func(tool.Context, Tool, args, result map[string]any, error) (map[string]any, error)` | Replaces tool result |
| `OnToolErrorCallback` | `func(tool.Context, Tool, map[string]any, error) (map[string]any, error)` | Recovers from tool error |

## Agent-Level Callbacks

```go
llmagent.New(llmagent.Config{
    BeforeModelCallbacks: []llmagent.BeforeModelCallback{
        func(ctx agent.CallbackContext, req *model.LLMRequest) (*model.LLMResponse, error) {
            // Inject RAG context into the request
            chunks := ragService.Search(extractLastUserText(req.Contents))
            req.Contents = prependSystemContent(req.Contents, buildContext(chunks))
            return nil, nil  // nil = continue, non-nil = short-circuit
        },
    },
    AfterModelCallbacks: []llmagent.AfterModelCallback{
        func(ctx agent.CallbackContext, resp *model.LLMResponse, err error) (*model.LLMResponse, error) {
            if err != nil {
                return nil, err  // Pass through error
            }
            // Post-process response
            resp.Content.Parts[0].Text = sanitize(resp.Content.Parts[0].Text)
            return resp, nil
        },
    },
})
```

## Plugin System (Global)

Plugins apply across **all agents in the runner tree**. Use for auth, telemetry, tenant context, audit logging.

```go
import "google.golang.org/adk/plugin"

p, _ := plugin.New(plugin.Config{
    Name: "my-plugin",

    // Fires once per runner.Run() — per-invocation setup
    BeforeRunCallback: func(ctx agent.InvocationContext) (*genai.Content, error) {
        ctx.Session().State().Set("app:tenant", getTenantID(ctx))
        return nil, nil
    },

    // Fires before every LLM call in every agent
    BeforeModelCallback: func(ctx agent.CallbackContext, req *model.LLMRequest) (*model.LLMResponse, error) {
        injectTenantContext(req, ctx)
        return nil, nil
    },

    // Fires on every emitted session event — for audit / tracing
    OnEventCallback: func(ctx agent.InvocationContext, ev *session.Event) (*session.Event, error) {
        auditLog(ctx.UserID(), ev)
        return nil, nil  // pass through unchanged
    },
})

runner.New(runner.Config{
    PluginConfig: runner.PluginConfig{Plugins: []*plugin.Plugin{p}},
})
```

## Built-in Plugin: FunctionCallModifier

Injects extra args (e.g. `user_id`, `trace_id`) into all matching function declarations:

```go
import "google.golang.org/adk/plugin/functioncallmodifier"

p := functioncallmodifier.MustNewPlugin(functioncallmodifier.FunctionCallModifierConfig{
    Predicate: func(toolName string) bool { return true }, // all tools
    Args: map[string]*genai.Schema{
        "user_id": {Type: "STRING", Description: "The invoking user ID"},
    },
})
```

## Context Hierarchy

```
InvocationContext   — full access: Agent, Session, Memory, Artifacts, UserContent
      ↓
ReadonlyContext     — safe for InstructionProvider / GlobalInstructionProvider
      ↓
CallbackContext     — adds mutable State + Artifacts (all callbacks)
      ↓
tool.Context        — adds Actions, FunctionCallID, HITL (tool.Run only)
```

## Instruction Template Engine

```go
Instruction: `You are an expert in {user:domain}.
Skill guide: {artifact.active_skill}
Company policy: {app:policy?}
Current task: {task_context?}`

// Supported placeholders:
// {key}              → session state
// {user:key}         → user-scoped state
// {app:key}          → app-scoped state
// {artifact.name}    → text content of a saved artifact
// {key?}             → optional (empty string if missing)
```

## Dynamic Instruction Provider

When `InstructionProvider` is set, `{placeholder}` substitution is **NOT** automatic:

```go
import "google.golang.org/adk/util/instructionutil"

InstructionProvider: func(ctx agent.ReadonlyContext) (string, error) {
    role, _ := ctx.ReadonlyState().Get("user:role")
    template := skillLibrary[role.(string)]
    // Must call InjectSessionState manually
    return instructionutil.InjectSessionState(ctx, template)
},
```

## Artifact-Based Skill Loading

```go
// Pre-load skill doc in BeforeAgentCallback
BeforeAgentCallbacks: []agent.BeforeAgentCallback{
    func(ctx agent.CallbackContext) (*genai.Content, error) {
        skill := skillRegistry.Fetch(ctx.ReadonlyState())
        ctx.Artifacts().Save(ctx, "active_skill", genai.NewPartFromText(skill))
        return nil, nil
    },
},
Instruction: "Use this skill: {artifact.active_skill}",
```

## Common Patterns

### Caching with BeforeModelCallback

```go
func cachingCallback(ctx agent.CallbackContext, req *model.LLMRequest) (*model.LLMResponse, error) {
    cacheKey := hashRequest(req)
    if cached, ok := cache.Get(cacheKey); ok {
        return cached.(*model.LLMResponse), nil  // Cache hit — skip LLM
    }
    return nil, nil  // Cache miss — continue to LLM
}
```

### Error Recovery

```go
OnModelErrorCallback: func(ctx agent.CallbackContext, req *model.LLMRequest, err error) (*model.LLMResponse, error) {
    if isRateLimitError(err) {
        time.Sleep(time.Second * 2)
        // Return nil to retry, or return a fallback response
        return &model.LLMResponse{
            Content: genai.NewContentFromText("Rate limited. Please try again.", "model"),
        }, nil
    }
    return nil, err  // Propagate other errors
},
```

## Gotchas

### InstructionProvider disables auto-injection
When `InstructionProvider` is set, you must call `instructionutil.InjectSessionState(ctx, template)` manually.

### `EndInvocation()` is immediate
Calling `ctx.EndInvocation()` stops all subsequent agent calls in the invocation tree.

### `GlobalInstruction` propagates to ALL sub-agents
Unlike `Instruction` (per-agent only), `GlobalInstruction` is appended to every agent's system prompt.

## See Also

- [adk-basics](../adk-basics) - Core agent setup
- [adk-tools](../adk-tools) - Tool callbacks
