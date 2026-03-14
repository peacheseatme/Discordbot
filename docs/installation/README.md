# Installation

Choose the installation method for your platform.

## Installation Methods

| Method | Platform | Best for |
|--------|----------|----------|
| [Install script](install-script.md) | Linux, macOS | Easiest — one command setup |
| [Manual Linux](linux.md) | Linux | Custom setups, no script |
| [Windows](windows.md) | Windows | WSL, Git Bash, or native Python |

## Quick Install (Linux / macOS)

```bash
git clone https://github.com/peacheseatme/Discordbot.git
cd Discordbot
bash install.sh
```

Then restart your terminal and run `c-cord start`.

## After Installation

1. **Invite the bot** — Use the OAuth2 URL with your bot's client ID:
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot+applications.commands
   ```

2. **Configure** — Edit `Src/.env` for your Discord token. The installer prompts for this during setup.

3. **Optional: Ko-fi** — Run `./scripts/add_kofi.sh` to enable Ko-fi supporter perks.
