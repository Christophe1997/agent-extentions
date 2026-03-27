# Permission Notification

Sends macOS desktop notifications when Claude Code needs permission to execute commands.

## Features

### Hooks

| Hook | Description |
|------|-------------|
| `PermissionRequest` | Fires when Claude needs permission to execute a tool |
| `Stop` | Fires when Claude finishes responding and waits for input |

### Capabilities

- **Permission Request Notification**: Notifies when Claude needs permission to run a command
- **Task Completion Notification**: Notifies when Claude finishes and is waiting for input
- **Command Details**: Shows the actual command or file being accessed (e.g., `Bash: git status`)
- **Click to Focus**: Clicking the notification brings you back to your terminal

### Supported Terminals

Auto-detects your terminal for click-to-focus:
- Warp
- iTerm2
- Terminal.app
- Alacritty
- Kitty

## Installation

### Requirements

- **macOS** (currently supported)
- [terminal-notifier](https://github.com/julienXX/terminal-notifier) - Install via Homebrew:
  ```bash
  brew install terminal-notifier
  ```
- `jq` - JSON processor (usually pre-installed on macOS)

```bash
/plugin install permission-notification@agent-extentions
```

## Usage

The plugin works automatically after installation. When Claude Code needs permission:

1. A notification appears showing the command/tool being requested
2. Click the notification to jump back to your terminal
3. Approve or deny in the terminal as usual

### Customization

**Disable "Done" notifications** (only notify on permissions):
Edit `hooks/hooks.json` and remove the `Stop` hook section.

**Custom terminal bundle ID** (if auto-detection fails):
```bash
export TERMINAL_BUNDLE_ID="com.googlecode.iterm2"
```

### Cross-Platform Support

Currently macOS only. For Linux/Windows:
- **Linux**: `notify-send` command
- **Windows**: PowerShell `BurntToast` module

## License

MIT
