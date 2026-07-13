---
name: consensus-research
description: |
  Explore and synthesize peer-reviewed scientific research via Consensus MCP. Use when the user wants evidence-based answers, literature synthesis, "what does the science say", systematic comparisons of findings, or academic consensus on a topic. Prefer over Tavily for scholarly evidence; prefer PubMed MCP for raw paper search and PMID-specific tasks.
---

# Consensus research (MCP)

Ground answers in peer-reviewed research using the Consensus MCP server (`https://mcp.consensus.app/mcp`).

## Prerequisites

1. MCP server enabled in [Cloud Agents MCP dropdown](https://cursor.com/agents)
2. OAuth sign-in on first use (Consensus account)
3. Repo config in `.cursor/mcp.json` under key `consensus`

## When to use

- "What does the research say about X?"
- Evidence synthesis across multiple studies
- Comparing scientific findings (not just news articles)
- Literature-style answers with scholarly grounding

## When to use other tools instead

| Need | Tool |
|------|------|
| Specific PMID / PMCID / citation lookup | [PubMed MCP](../pubmed-research/SKILL.md) |
| General web, docs, news, product info | [Tavily](../tavily-cli/SKILL.md) |
| Bulk paper metadata or MeSH queries | [PubMed MCP](../pubmed-research/SKILL.md) |

## Tips

- Ask focused, researchable questions (not overly broad prompts)
- For a known paper, use PubMed MCP to fetch details; use Consensus for synthesis across the literature
- Combine: Consensus for "what does science say" → PubMed for retrieving specific papers cited
