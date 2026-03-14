# Installation — Windows

Coffeecord can run on Windows via WSL, Git Bash, or native Python. The install script is Bash-only, so Windows users follow a manual process.

## Option 1: WSL (Recommended)

Use the [Windows Subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install) to run the full install script.

### 1. Install WSL

In PowerShell (Admin):

```powershell
wsl --install
```

Restart if prompted, then open Ubuntu (or your chosen distro) from the Start menu.

### 2. Run the install script

In the WSL terminal:

```bash
git clone https://github.com/peacheseatme/Discordbot.git
cd Discordbot
bash install.sh
```

### 3. Start the bot

```bash
c-cord start
```

The bot runs in WSL. Use `c-cord` commands from the WSL terminal.

---

## Option 2: Git Bash + Manual Setup

If you have [Git for Windows](https://git-scm.com/download/win) (includes Git Bash):

### 1. Clone the repository

In Git Bash:

```bash
git clone https://github.com/peacheseatme/Discordbot.git
cd Discordbot
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/Scripts/activate
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

### 5. Create Storage directories

```bash
mkdir -p Storage/Config Storage/Data Storage/Temp Storage/Logs
```

### 6. Run the bot

```bash
python Src/Bot.py
```

For background runs, use `start /B` or run in a separate terminal.

---

## Option 3: Native Windows (Command Prompt / PowerShell)

### 1. Install Python 3.12+

Download from [python.org](https://www.python.org/downloads/). During install, check **"Add Python to PATH"**.

### 2. Clone the repository

```powershell
git clone https://github.com/peacheseatme/Discordbot.git
cd Discordbot
```

### 3. Create virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 4. Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Create environment file

Create `Src\.env` with:

```
DISCORD_TOKEN=your_bot_token_here
```

### 6. Create Storage directories

```powershell
mkdir Storage\Config, Storage\Data, Storage\Temp, Storage\Logs
```

### 7. Run the bot

```powershell
python Src\Bot.py
```

### Using c-cord on Windows

The `bot.sh` script requires Bash. To use `c-cord`-style commands on Windows:

- Use **WSL** (Option 1), or
- Create a batch file that runs `python Src\Bot.py`, or
- Use a process manager like [NSSM](https://nssm.cc/) to run the bot as a service.
