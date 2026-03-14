# Installation — Install Script (Linux / macOS)

The recommended way to install Coffeecord on Linux and macOS. The script sets up Python, dependencies, and the `c-cord` CLI in one run.

## Prerequisites

- **Bash** — Usually pre-installed on Linux and macOS
- **Git** — To clone the repository
- **Python 3.12+** — The script will check and use the first suitable version

## Steps

### 1. Clone the repository

```bash
git clone https://github.com/peacheseatme/Discordbot.git
cd Discordbot
```

Or, if you already have the repo, `cd` into the project root.

### 2. Run the installer

```bash
bash install.sh
```

### 3. Follow the prompts

The script will:

- Check Python version (3.12+ required)
- Create a virtual environment at `.venv/`
- Install dependencies from `requirements.txt`
- Prompt for your **Discord bot token**
- Write `Src/.env` with your token
- Install the `c-cord` command to `~/.local/bin/`
- Add `~/.local/bin` to your PATH (in `.bashrc`, `.zshrc`, or `.profile`)

### 4. Restart your terminal

If the installer added `~/.local/bin` to your PATH, restart the terminal (or run `source ~/.bashrc` / `source ~/.zshrc`) so `c-cord` is available.

### 5. Start the bot

```bash
c-cord start
```

## Custom install directory

To install to a different directory:

```bash
COFFEECORD_INSTALL_DIR=/opt/coffeecord bash install.sh
```

## Troubleshooting

- **"Python 3.12 or newer is required"** — Install Python 3.12+ from [python.org](https://www.python.org/downloads/) or your package manager (`apt install python3.12`, `brew install python@3.12`).
- **"c-cord: command not found"** — Ensure `~/.local/bin` is in your PATH. Run `source ~/.bashrc` or `source ~/.zshrc`, or add `export PATH="$HOME/.local/bin:$PATH"` to your shell config.
- **Permission denied** — Ensure `install.sh` is executable: `chmod +x install.sh`.
