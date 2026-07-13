---
name: tavily-cli
description: |
  Web search, content extraction, crawling, and deep research via the Tavily CLI. Use this skill whenever the user wants to search the web, find articles, research a topic, look something up online, extract content from a URL, grab text from a webpage, crawl documentation, download a site's pages, discover URLs on a domain, or conduct in-depth research with citations. Also use when they say "fetch this page", "pull the content from", "get the page at https://", "find me articles about", or reference extracting data from external websites. Do NOT trigger for local file operations, git commands, deployments, or code editing tasks.
---

# Tavily CLI

Web search, content extraction, site crawling, URL discovery, and deep research. Returns JSON optimized for LLM consumption.

## Prerequisites

Requires `TAVILY_API_KEY` in Cloud Agents Secrets (or `tvly login --api-key "$TAVILY_API_KEY"`).

Check status: `tvly --status`

Install (done automatically in cloud via `.cursor/environment.json`):

```bash
curl -fsSL https://cli.tavily.com/install.sh | bash
export TAVILY_API_KEY=tvly-YOUR_KEY
```

## Workflow

1. **Search** — No specific URL. Find pages, answer questions, discover sources.
2. **Extract** — Have a URL. Pull its content directly.
3. **Research** — Comprehensive multi-source analysis with citations.

| Need | Command | Skill |
|------|---------|-------|
| Find pages on a topic | `tvly search` | [tavily-search](tavily-search/SKILL.md) |
| Get a page's content | `tvly extract` | [tavily-extract](tavily-extract/SKILL.md) |
| Deep research with citations | `tvly research` | [tavily-research](tavily-research/SKILL.md) |

All commands support `--json` for structured output and `-o` to save to a file.
