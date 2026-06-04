"""PRD Writer Agent — doc_search tool."""

from __future__ import annotations

import json
from pathlib import Path


def search_knowledge(query: str, knowledge_dir: str = "knowledge") -> list[dict[str, str]]:
    """Simple keyword-based search over knowledge files."""
    results: list[dict[str, str]] = []
    kdir = Path(knowledge_dir)
    if not kdir.exists():
        return results

    keywords = set(query.lower().split())
    for f in kdir.glob("*.md"):
        content = f.read_text(encoding="utf-8").lower()
        if any(kw in content for kw in keywords):
            results.append(
                {
                    "file": f.name,
                    "content": f.read_text(encoding="utf-8")[:500],
                }
            )
    return results


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "PRD 模板"
    results = search_knowledge(query)
    print(json.dumps(results, ensure_ascii=False, indent=2))
