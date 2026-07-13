---
name: tavily-extract
description: |
  Extract clean markdown or text content from specific URLs via the Tavily CLI. Use this skill when the user has one or more URLs and wants their content, says "extract", "grab the content from", "pull the text from", "get the page at", "read this webpage", or needs clean text from web pages.
---

# tavily extract

Extract clean markdown or text content from one or more URLs.

## Prerequisites

Requires the Tavily CLI. See [tavily-cli](../tavily-cli/SKILL.md) for install and auth setup.

## Quick start

```bash
tvly extract "https://example.com/article" --json
tvly extract "https://example.com/docs" --query "authentication API" --chunks-per-source 3 --json
tvly extract "https://app.example.com" --extract-depth advanced --json
```

## Options

| Option | Description |
|--------|-------------|
| `--query` | Rerank chunks by relevance to this query |
| `--extract-depth` | `basic` (default) or `advanced` (for JS pages) |
| `--format` | `markdown` (default) or `text` |
| `--json` | Structured JSON output |

Max 20 URLs per request.
