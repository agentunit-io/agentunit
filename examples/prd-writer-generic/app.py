"""PRD Writer Agent Unit — generic-python entry point."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from starlette.requests import Request


def load_skill_prompt() -> str:
    """Load the PRD writer skill prompt."""
    skill_path = Path(__file__).parent / "skills" / "prd_writer.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        # Extract body after YAML frontmatter
        parts = text.split("---", 2)
        return parts[2].strip() if len(parts) >= 3 else text
    return "You are a helpful PRD writing assistant."


def load_knowledge() -> str:
    """Load all knowledge files."""
    kdir = Path(__file__).parent / "knowledge"
    contents: list[str] = []
    if kdir.exists():
        for f in sorted(kdir.glob("*.md")):
            contents.append(f.read_text(encoding="utf-8"))
    return "\n---\n".join(contents)


def generate_prd(requirement_notes: str, project_name: str = "") -> dict[str, Any]:
    """Generate a PRD document.

    In production, this calls the LLM. For demo, returns a template.
    """
    _skill_prompt = load_skill_prompt()
    _knowledge = load_knowledge()
    project = project_name or "未命名项目"

    # Demo: return a structured PRD template
    # In production: call OpenAI API with skill_prompt + knowledge + requirement_notes
    prd = f"""# 产品需求文档（PRD）

## 项目：{project}

---

## 1. 背景与目标

{requirement_notes}

## 2. 用户故事

*基于需求要点自动生成（接入 LLM 后填充）*

## 3. 功能需求

| 编号 | 名称 | 描述 | 优先级 |
|------|------|------|--------|
| F-001 | 核心功能 | 待 LLM 基于需求分析生成 | P0 |

## 4. 非功能需求

- 性能：待确认
- 安全：待确认
- 兼容性：待确认

## 5. 验收标准

- [ ] 核心功能可正常运行

## 6. 风险与依赖

*待 LLM 分析后生成*

---

> 此 PRD 由 PRD Writer Agent Unit v1.0.0 自动生成
> 责任人：待指定
> 状态：草稿（需人工审核）
"""
    return {
        "prd_document": prd,
        "quality_score": 0.6,
    }


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "unit": "prd-writer", "version": "1.0.0"})


async def spec_endpoint(request: Request) -> JSONResponse:
    spec_path = Path(__file__).parent / "agentunit.yaml"
    if spec_path.exists():
        data = yaml.safe_load(spec_path.read_text())
        return JSONResponse(data)
    return JSONResponse({"error": "spec not found"}, status_code=404)


async def run_endpoint(request: Request) -> JSONResponse:
    import time

    body = await request.json()
    skill_id = body.get("skill_id", "")
    notes = body.get("requirement_notes", "")
    project = body.get("project_name", "")

    if not notes:
        return JSONResponse({"error": "requirement_notes is required"}, status_code=400)

    if skill_id and skill_id != "prd_writer":
        return JSONResponse({"error": f"Unknown skill: {skill_id}"}, status_code=400)

    start = time.monotonic()
    output = generate_prd(notes, project)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    return JSONResponse(
        {
            "output": output,
            "telemetry": {
                "skill_id": "prd_writer",
                "latency_ms": elapsed_ms,
            },
        }
    )


app = Starlette(
    routes=[
        Route("/health", health),
        Route("/spec", spec_endpoint),
        Route("/run", run_endpoint, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    if "--input" in sys.argv:
        idx = sys.argv.index("--input")
        input_path = sys.argv[idx + 1]
        data = json.loads(Path(input_path).read_text())
        output = generate_prd(
            data.get("requirement_notes", ""),
            data.get("project_name", ""),
        )
        print(json.dumps({"output": output, "telemetry": {}}, ensure_ascii=False, indent=2))
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8091")))
