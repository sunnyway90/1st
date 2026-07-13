---
name: tavily-search
description: |
  Search the web with LLM-optimized results via the Tavily CLI. Use this skill when the user wants to search the web, find articles, look up information, get recent news, discover sources, or says "search for", "find me", "look up", "what's the latest on", "find articles about", or needs current information from the internet.
---

# tavily search

Web search returning LLM-optimized results with content snippets and relevance scores.

## Prerequisites

Requires the Tavily CLI. See [tavily-cli](../tavily-cli/SKILL.md) for install and auth setup.

## Quick start

```bash
tvly search "your query" --json
tvly search "AI news" --time-range week --topic news --json
tvly search "SEC filings" --include-domains sec.gov,reuters.com --json
```

## Options

| Option | Description |
|--------|-------------|
| `--depth` | `ultra-fast`, `fast`, `basic` (default), `advanced` |
| `--max-results` | Max results, 0-20 (default: 5) |
| `--topic` | `general` (default), `news`, `finance` |
| `--time-range` | `day`, `week`, `month`, `year` |
| `--include-domains` | Comma-separated domains to include |
| `--include-raw-content` | Include full page content in results |
| `--json` | Structured JSON output |

## Tips

- Keep queries under 400 characters.
- Use `--time-range` for recent information.
- For deep synthesis, escalate to [tavily-research](../tavily-research/SKILL.md).
