// Example: Weather Agent with Function Tool
// A complete example showing agent setup, tool creation, and runner configuration.

package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"google.golang.org/adk/agent"
	"google.golang.org/adk/agent/llmagent"
	"google.golang.org/adk/cmd/launcher"
	"google.golang.org/adk/cmd/launcher/full"
	"google.golang.org/adk/model/gemini"
	"google.golang.org/adk/tool"
	"google.golang.org/adk/tool/functiontool"
	"google.golang.org/genai"
)

// WeatherArgs defines the parameters for the weather tool
type WeatherArgs struct {
	City string `json:"city" jsonschema:"description=The city to get weather for,required"`
	Unit string `json:"unit,omitempty" jsonschema:"description=Temperature unit (celsius or fahrenheit),default=celsius"`
}

// NewWeatherTool creates a weather lookup tool
func NewWeatherTool() (tool.Tool, error) {
	return functiontool.New(functiontool.Config{
		Name:        "get_weather",
		Description: "Get the current weather for a specific city. Returns temperature and conditions.",
	}, func(ctx tool.Context, args WeatherArgs) (map[string]any, error) {
		// In a real implementation, you would call a weather API
		// This is a mock implementation for demonstration
		weather := map[string]any{
			"city":        args.City,
			"temperature": 22,
			"unit":        args.Unit,
			"condition":   "sunny",
			"humidity":    45,
		}
		return weather, nil
	})
}

// NewAgent creates the weather agent with the weather tool
func NewAgent(ctx context.Context) (*llmagent.Agent, error) {
	// Initialize the Gemini model
	model, err := gemini.NewModel(ctx, "gemini-2.5-flash", &genai.ClientConfig{
		APIKey: os.Getenv("GOOGLE_API_KEY"),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create model: %w", err)
	}

	// Create the weather tool
	weatherTool, err := NewWeatherTool()
	if err != nil {
		return nil, fmt.Errorf("failed to create weather tool: %w", err)
	}

	// Create the agent
	return llmagent.New(llmagent.Config{
		Name:        "weather_agent",
		Model:       model,
		Description: "An agent that provides weather information for cities worldwide.",
		Instruction: `You are a helpful weather assistant.
Your primary function is to provide weather information using the get_weather tool.
When users ask about weather:
1. Extract the city name from their request
2. Call the get_weather tool with the city
3. Present the weather information in a friendly, readable format
If users ask about something other than weather, politely redirect them to weather topics.`,
		Tools: []tool.Tool{weatherTool},
	})
}

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
