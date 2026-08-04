"""US equity multifactor knowledge-base search for LLM RAG."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

KB_ROOT = Path(__file__).resolve().parents[2] / "knowledge_base" / "us_multifactor"
CHUNKS_PATH = KB_ROOT / "chunks" / "chunks.jsonl"
DIGESTS_DIR = KB_ROOT / "digests"
CATALOG_PATH = KB_ROOT / "catalog" / "catalog.yaml"

# Keep Latin tokens separate from CJK so "什么是BAB" -> ["什么是", "bab"].
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*|[0-9]+|[\u4e00-\u9fff]+")

_SYNONYMS: dict[str, list[str]] = {
    "价值": ["value", "hml", "book-to-market", "book to market"],
    "动量": ["momentum", "wml", "umd", "winners", "losers"],
    "规模": ["size", "smb", "small", "big"],
    "盈利": ["profitability", "rmw", "roe", "gross profits", "gp/a"],
    "投资": ["investment", "cma", "investment-to-assets"],
    "质量": ["quality", "qmj", "junk"],
    "低波": ["low beta", "bab", "betting against beta", "low volatility"],
    "五因子": ["five-factor", "five factor", "rmw", "cma"],
    "三因子": ["three-factor", "three factor", "smb", "hml"],
    "因子": ["factor", "anomaly", "premium"],
    "冗余": ["redundant", "redundancy"],
    "夏普": ["sharpe"],
    "美股": ["u.s.", "us equities", "equity"],
    "bab": ["betting against beta", "low beta", "leverage"],
    "qmj": ["quality minus junk", "quality", "junk"],
    "hml": ["value", "book-to-market"],
    "smb": ["size", "small", "big"],
    "rmw": ["profitability", "robust minus weak"],
    "cma": ["investment", "conservative minus aggressive"],
    "负相关": ["negatively correlated", "negative correlation"],
    "正相关": ["positively correlated", "positive correlation"],
}

_STOPWORDS = {
    "什么",
    "是",
    "的",
    "了",
    "和",
    "与",
    "在",
    "为",
    "如何",
    "怎么",
    "为什么",
    "哪些",
    "一个",
    "什么是",
    "the",
    "a",
    "an",
    "of",
    "and",
    "or",
    "to",
    "in",
    "on",
    "for",
    "is",
    "are",
    "what",
    "how",
    "why",
}


@dataclass
class Chunk:
    id: str
    source: str
    title: str
    chunk_index: int
    text: str


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _expand_query(query: str) -> list[str]:
    tokens = [t for t in _tokenize(query) if t not in _STOPWORDS]
    # Pull known Chinese/English concept keys out of unspaced queries.
    for key in _SYNONYMS:
        if key in query or key in query.lower():
            tokens.append(key.lower() if key.isascii() else key)
    expanded: list[str] = []
    for tok in tokens:
        expanded.append(tok)
        for syn in _SYNONYMS.get(tok, []):
            expanded.extend(_tokenize(syn))
        for syn in _SYNONYMS.get(tok.lower(), []):
            expanded.extend(_tokenize(syn))
    seen: set[str] = set()
    out: list[str] = []
    for t in expanded:
        if t in _STOPWORDS or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def load_chunks(path: Path | None = None) -> list[Chunk]:
    path = path or CHUNKS_PATH
    chunks: list[Chunk] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            chunks.append(
                Chunk(
                    id=obj["id"],
                    source=obj["source"],
                    title=obj.get("title", obj["source"]),
                    chunk_index=int(obj.get("chunk_index", 0)),
                    text=obj["text"],
                )
            )
    return chunks


def load_digests() -> list[Chunk]:
    chunks: list[Chunk] = []
    if not DIGESTS_DIR.exists():
        return chunks
    for i, md in enumerate(sorted(DIGESTS_DIR.glob("*.md"))):
        text = md.read_text(encoding="utf-8")
        chunks.append(
            Chunk(
                id=f"digest::{md.stem}",
                source=f"digest/{md.stem}",
                title=md.stem,
                chunk_index=i,
                text=text,
            )
        )
    return chunks


def _score(query_tokens: list[str], chunk: Chunk, df: Counter[str], n_docs: int) -> float:
    if not query_tokens:
        return 0.0
    tf = Counter(_tokenize(chunk.text))
    score = 0.0
    hay = f"{chunk.source} {chunk.title} {chunk.id}".lower()
    for t in query_tokens:
        if t not in tf and t not in hay:
            continue
        idf = math.log(1 + (n_docs - df[t] + 0.5) / (df[t] + 0.5))
        freq = tf.get(t, 0)
        if freq:
            score += idf * (freq * 2.2) / (freq + 1.2)
        if t in hay:
            score += 1.2 * idf
    # Prefer curated digests slightly for equal content matches.
    if chunk.source.startswith("digest/"):
        score *= 1.15
    return score


def search(
    query: str,
    top_k: int = 8,
    include_digests: bool = True,
    source_filter: str | None = None,
) -> list[tuple[float, Chunk]]:
    chunks = load_chunks()
    if include_digests:
        chunks.extend(load_digests())
    if source_filter:
        key = source_filter.lower()
        chunks = [c for c in chunks if key in c.source.lower()]

    q_tokens = _expand_query(query)
    df: Counter[str] = Counter()
    for c in chunks:
        for t in set(_tokenize(c.text)):
            df[t] += 1
    n = max(len(chunks), 1)
    scored = [(_score(q_tokens, c, df, n), c) for c in chunks]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def format_context(hits: list[tuple[float, Chunk]], max_chars: int = 6000) -> str:
    parts: list[str] = []
    used = 0
    for score, c in hits:
        header = f"### {c.id} (score={score:.3f}, source={c.source})\n"
        body = c.text.strip()
        block = header + body + "\n"
        if used + len(block) > max_chars and parts:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts)


def build_ask_prompt(question: str, top_k: int = 8) -> str:
    hits = search(question, top_k=top_k, include_digests=True)
    context = format_context(hits)
    return (
        "你是美股多因子研究助手。只能根据【资料】回答，不要编造论文结论。"
        "若资料不足，明确说「资料库未覆盖」。\n\n"
        f"【资料】\n{context}\n\n"
        f"【问题】\n{question}\n\n"
        "请用中文简明回答，并在文末列出引用的 source id。\n"
    )


def list_catalog() -> str:
    lines = [
        f"KB_ROOT: {KB_ROOT}",
        f"chunks: {CHUNKS_PATH} ({'exists' if CHUNKS_PATH.exists() else 'MISSING'})",
        f"digests: {DIGESTS_DIR}",
        f"catalog: {CATALOG_PATH}",
        "",
        "== Digests ==",
    ]
    for md in sorted(DIGESTS_DIR.glob("*.md")):
        lines.append(f"- {md.name}")
    papers = KB_ROOT / "papers"
    lines.append("\n== Local PDFs ==")
    if papers.exists():
        for pdf in sorted(papers.glob("*.pdf")):
            lines.append(f"- {pdf.name} ({pdf.stat().st_size // 1024} KB)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search the US multifactor knowledge base")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Ranked chunk retrieval")
    p_search.add_argument("query")
    p_search.add_argument("-k", "--top-k", type=int, default=8)
    p_search.add_argument("--source", default=None, help="Filter by source substring")
    p_search.add_argument("--no-digests", action="store_true")

    p_ask = sub.add_parser("ask", help="Build an LLM prompt with retrieved context")
    p_ask.add_argument("question")
    p_ask.add_argument("-k", "--top-k", type=int, default=8)

    sub.add_parser("list", help="List local KB assets")

    args = parser.parse_args(argv)

    if args.cmd == "list":
        print(list_catalog())
        return 0
    if args.cmd == "search":
        hits = search(
            args.query,
            top_k=args.top_k,
            include_digests=not args.no_digests,
            source_filter=args.source,
        )
        for score, c in hits:
            preview = re.sub(r"\s+", " ", c.text)[:220]
            print(f"[{score:.3f}] {c.id}\n  {preview}...\n")
        return 0
    if args.cmd == "ask":
        print(build_ask_prompt(args.question, top_k=args.top_k))
        return 0
    return 1
