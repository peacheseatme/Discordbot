# Storage

Config and data storage patterns.

## Contents

- [Config and data](config-and-data.md) — paths, `json_cache`, file layout

## Overview

- **Config**: `Storage/Config/` — modules.json, module_states.json, automod.json, etc.
- **Data**: `Storage/Data/` — tickets, xp, warns, supporters, transcripts
- **Temp**: `Storage/Temp/` — level card cache, active calls, etc.
- **Logs**: `Storage/Logs/` — bot logs

Most JSON files are under `.gitignore`; the install script creates placeholders as needed.
