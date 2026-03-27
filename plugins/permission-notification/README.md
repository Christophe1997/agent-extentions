# Permission Notification

Sends macOS desktop notifications when Claude Code needs permission to execute commands.

## Features

- **Permission Request Notification**: Notifies you when Claude needs permission to run a command
- **Task Completion Notification**: Notifies you when Claude finishes and is waiting for input
- **Command Details**: Shows the actual command or file being accessed in the notification
- **Click to Focus**: Clicking the notification brings you back to your terminal

## Requirements

- **macOS** (currently supported)
- [terminal-notifier](https://github.com/julienXX/terminal-notifier) - Install via Homebrew:
  ```bash
  brew install terminal-notifier
  ```
- `jq` - JSON processor (usually pre-installed on macOS)

## Installation

This plugin is part of the agent-extensions marketplace. To use it:

1. Add to your project's `.claude-plugin/marketplace.json`:
   ```json
   {
     "plugins": ["./plugins/permission-notification"]
   }
   ```

2. Restart Claude Code

## How It Works

The plugin uses two hooks:

1. **PermissionRequest**: Fires when Claude needs permission to execute a tool
   - Shows the tool name and details (e.g., `Bash: git status`)

2. **Stop**: Fires when Claude finishes responding and waits for input
   - Alerts you that Claude is ready for your next message

## Supported Terminals

Auto-detects your terminal for click-to-focus:
- Warp (default)
- iTerm2
- Terminal.app
- Alacritty
- Kitty

## Customization

### Disable "Done" Notifications

To only notify on permissions (not task completion), edit `hooks/hooks.json` and remove the `Stop` hook section.

### Custom Terminal Bundle ID

Set the `TERMINAL_BUNDLE_ID` environment variable if auto-detection fails:
```bash
export TERMINAL_BUNDLE_ID="com.googlecode.iterm2"
```

## Cross-Platform Support

Currently macOS only. For Linux/Windows support, consider:

- **Linux**: Use `notify-send` command
- **Windows**: Use PowerShell `BurntToast` module
- **Cross-platform**: [terminal-notifications](https://github.com/StartupBros/terminal-notifications)

Contributions welcome to add cross-platform support!

## License

MIT
