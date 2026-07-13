---
name: pubmed-research
description: |
  Search PubMed and PubMed Central for biomedical literature via MCP. Use when the user asks about papers, clinical studies, drug mechanisms, disease research, PMID/PMCID lookup, MeSH terms, citation formatting, or says "search PubMed", "find papers about", "literature on", "what does the research say about". Prefer this over web search for peer-reviewed biomedical questions.
---

# PubMed research (MCP)

Search and retrieve peer-reviewed biomedical literature using the `pubmed-mcp-server` MCP tools.

## Prerequisites

1. MCP server enabled in [Cloud Agents MCP dropdown](https://cursor.com/agents) or local Cursor MCP settings
2. Repo config in `.cursor/mcp.json` (stdio server; requires `npm install`)

## Typical workflow

1. **Search** — `pubmed_search_articles` with a focused query (author, topic, date range)
2. **Fetch metadata** — `pubmed_fetch_articles` with PMIDs from search results
3. **Full text** (when available) — `pubmed_fetch_fulltext` with PMCID (`PMC` prefix)
4. **Citations** — `pubmed_format_citations` for formatted references
5. **Related work** — `pubmed_find_related` to expand from a known PMID

## Query tips

- Use MeSH terms when precision matters: `pubmed_lookup_mesh` to find standard terms
- Fix typos: `pubmed_spell_check`
- Crosswalk IDs: `pubmed_convert_ids` (PMID ↔ DOI ↔ PMCID)
- If PubMed is empty, broaden via `pubmed_europepmc_search` (preprints, EPMC-only OA)

## When to use vs other tools

| Need | Tool |
|------|------|
| Peer-reviewed biomedical papers | **PubMed MCP** (this skill) |
| Broad academic synthesis across fields | [Consensus MCP](../consensus-research/SKILL.md) |
| General web / news / non-scholarly | [Tavily search](../tavily-search/SKILL.md) |

## Example prompts for the agent

- "Search PubMed for recent RCTs on GLP-1 agonists and cardiovascular outcomes"
- "Fetch full text and summarize PMID 12345678"
- "Format these PMIDs as APA citations"
