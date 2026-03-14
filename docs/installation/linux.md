# Installation — Manual Linux

Manual installation for Linux when you prefer not to use the install script or need a custom setup.

## Prerequisites

- **Python 3.12+**
- **pip** (usually bundled with Python)
- **Git**

## Steps

### 1. Clone the repository

```bash
git clone https://github.com/peacheseatme/Discordbot.git
cd Discordbot
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create environment file

Create `Src/.env` with your Discord token:

```bash
echo "DISCORD_TOKEN=your_bot_token_here" > Src/.env
```

Replace `your_bot_token_here` with your bot token from the [Discord Developer Portal](https://discord.com/developers/applications).

### 5. Ensure Storage directories exist

```bash
mkdir -p Storage/Config Storage/Data Storage/Temp Storage/Logs
```

If `scripts/generate_storage_placeholders.py` exists:

```bash
python scripts/generate_storage_placeholders.py
```

### 6. Run the bot

**Option A: Direct Python**

```bash
cd /path/to/Discordbot
source .venv/bin/activate
python Src/Bot.py
```

**Option B: Use the c-cord wrapper**

Install the `c-cord` command for start/stop/restart:

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/bot.sh" ~/.local/bin/c-cord
chmod +x bot.sh
export PATH="$HOME/.local/bin:$PATH"
```

Add the `export` line to `~/.bashrc` or `~/.zshrc` to make it permanent. Then:

```bash
c-cord start
```

## Running in the background

Without `c-cord`, you can use `nohup` or a process manager:

```bash
nohup python Src/Bot.py >> Storage/Logs/bot.log 2>&1 &
```

Or use `systemd`, `screen`, or `tmux` for persistent runs.
