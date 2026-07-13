---
name: tavily-research
description: |
  Conduct comprehensive AI-powered research with citations via the Tavily CLI. Use this skill when the user wants deep research, a detailed report, a comparison, market analysis, literature review, or says "research", "investigate", "analyze in depth", "compare X vs Y". Takes 30-120 seconds. For quick fact-finding, use tavily-search instead.
---

# tavily research

AI-powered deep research that gathers sources, analyzes them, and produces a cited report.

## Prerequisites

Requires the Tavily CLI. See [tavily-cli](../tavily-cli/SKILL.md) for install and auth setup.

## Quick start

```bash
tvly research "competitive landscape of AI code assistants"
tvly research "electric vehicle market analysis" --model pro
tvly research "fintech trends 2025" --model pro -o fintech-report.md --json
```

## Model selection

| Model | Use for | Speed |
|-------|---------|-------|
| `mini` | Single-topic, targeted research | ~30s |
| `pro` | Comprehensive multi-angle analysis | ~60-120s |
| `auto` | API chooses based on complexity | Varies |

For quick facts, use `tvly search` instead.
