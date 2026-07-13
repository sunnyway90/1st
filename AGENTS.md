# AGENTS.md

Instructions for Cursor Cloud Agents working in this repository.

## Project overview

Python toolkit with three modules:

| Module | Path | Purpose |
|--------|------|---------|
| `yield_curve` | `src/yield_curve/` | Bond yield curve bootstrap, pricing, YTM |
| `deribit_options` | `src/deribit_options/` | Deribit BTC options snapshots and ATM analysis |
| `wechat_scraper` | `src/wechat_scraper/` | WeChat article fetch and export |

## Cursor Cloud specific instructions

### Environment setup

The cloud environment installs dependencies via `.cursor/environment.json`:

```bash
python3 -m pip install -e .
npm install
curl -fsSL https://cli.tavily.com/install.sh | bash
```

After install, verify the environment:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m yield_curve
```

### Required secrets

Configure these in [Cloud Agents → Secrets](https://cursor.com/dashboard/cloud-agents) (not in code):

| Secret | Required for | Notes |
|--------|--------------|-------|
| `TAVILY_API_KEY` | Tavily CLI (`tvly`) | Web search, extract, research |
| `WECHAT_MP_COOKIE` | WeChat batch mode | Only when scraping account articles |
| `WECHAT_MP_TOKEN` | WeChat batch mode | Token from mp.weixin.qq.com URL |

Tavily auth in cloud: `tvly login --api-key "$TAVILY_API_KEY"` or export `TAVILY_API_KEY` before running `tvly` commands.

PubMed and Consensus use MCP — enable them in the [Cloud Agents MCP dropdown](https://cursor.com/agents). OAuth may be required on first use.

### MCP servers

Repo config lives in `.cursor/mcp.json`. Cloud Agents also need MCP enabled in the dashboard:

| Server | Transport | Config |
|--------|-----------|--------|
| `pubmed-mcp-server` | stdio | Requires `npm install` (see `package.json`) |
| `consensus` | HTTP | `https://mcp.consensus.app/mcp` — OAuth on first use |

For Tavily, prefer the Tavily CLI with `TAVILY_API_KEY` (see `.cursor/skills/tavily-cli/SKILL.md`) or add a Tavily HTTP MCP in the dashboard if available.

### Skills

Project skills are in `.cursor/skills/`:

- `tavily-cli`, `tavily-search`, `tavily-extract`, `tavily-research` — web search and research
- `pubmed-research` — PubMed literature search via MCP
- `consensus-research` — academic synthesis via Consensus MCP

### Run commands

```bash
# Install (also run automatically on cloud agent startup)
python3 -m pip install -e .
npm install

# Tests (preferred)
PYTHONPATH=src python3 -m unittest discover -s tests -v

# Yield curve demo (writes yield_curve_demo.png)
python3 -m yield_curve

# Deribit options snapshot
PYTHONPATH=src python3 -m deribit_options --snapshot-csv data/btc_option_snapshots.csv

# WeChat single article (no login)
python3 -m wechat_scraper fetch "https://mp.weixin.qq.com/s/..." --format md
```

### Code style

- Python 3.10+, type hints, `from __future__ import annotations` where used
- Tests use `unittest` (not pytest runner required, though pytest is configured in `pyproject.toml`)
- Keep changes focused; match existing module structure under `src/`

### What not to do

- Do not commit API keys, cookies, or tokens
- Do not use `--no-verify` on git commits
- WeChat batch scraping: respect rate limits; personal/learning use only

### Delivering changes

Cloud Agents should push to a `cursor/<descriptive-name>-af78` branch and open a PR against `main`. Include test results in the PR description.
