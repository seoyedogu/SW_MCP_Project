"""
Anthropic Claude MCP 서버 엔트리포인트.

기존 FastAPI 로직(제품명 정규화 + 이미지 크롤러)을 MCP Tool 형태로 노출한다.
"""

from __future__ import annotations

import anyio
from mcp import types
from mcp.server import stdio
from mcp.server.fastmcp.server import MCPServer

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "fastapi"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.new_single_page_crawler import crawl_single_page
from app.normalize_product_name import (
    convert_product_name_to_model,
    product_name_to_model,
)

SERVER_INSTRUCTIONS = (
    "1) 사용자 입력 제품명을 제조사 모델명으로 정규화하고 "
    "2) 해당 상세 페이지 이미지를 크롤링해 Claude로 전달합니다."
)

server = MCPServer(
    name="product-analyzer",
    version="1.0.0",
    instructions=SERVER_INSTRUCTIONS,
)


TOOL_DEFINITIONS = {
    "normalize_product_name": types.Tool(
        name="normalize_product_name",
        description="자연어 제품명을 제조사 모델명과 상품 URL로 정규화합니다.",
        inputSchema={
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "소비자가 입력한 자연어 제품명",
                }
            },
            "required": ["product_name"],
        },
        outputSchema={
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "model_name": {"type": "string"},
                "url": {"type": "string"},
                "saved": {"type": "boolean"},
                "message": {"type": "string"},
            },
            "required": ["product_name", "model_name", "url", "saved", "message"],
        },
    ),
    "crawl_product_images": types.Tool(
        name="crawl_product_images",
        description="저장된 제품 URL에서 이미지를 최대 4장까지 크롤링하여 Claude에 적합한(base64) 형태로 반환합니다.",
        inputSchema={
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "사전에 정규화해 둔 제품명 (normalize_product_name 호출 필요)",
                }
            },
            "required": ["product_name"],
        },
        outputSchema={
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "url": {"type": "string"},
                "image_count": {"type": "integer"},
                "images": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "base64": {"type": "string"},
                            "mime_type": {"type": "string"},
                            "index": {"type": "integer"},
                            "original_size_bytes": {"type": "integer"},
                            "optimized_size_bytes": {"type": "integer"},
                        },
                        "required": [
                            "url",
                            "base64",
                            "mime_type",
                            "index",
                        ],
                    },
                },
                "success": {"type": "boolean"},
                "message": {"type": "string"},
            },
            "required": [
                "product_name",
                "url",
                "image_count",
                "images",
                "success",
                "message",
            ],
        },
    ),
}


def _store_mapping(product_name: str, mapping: dict[str, str]) -> None:
    product_name_to_model[product_name] = mapping


def _normalize_product(product_name: str) -> dict[str, str]:
    cleaned = product_name.strip()
    if not cleaned:
        raise ValueError("제품 이름을 입력해주세요.")

    result = convert_product_name_to_model(cleaned)
    if not result:
        raise ValueError(f"'{cleaned}' 제품의 모델명을 찾지 못했습니다.")

    _store_mapping(cleaned, result)

    return {
        "product_name": cleaned,
        "model_name": result["model"],
        "url": result["url"],
        "saved": True,
        "message": f"제품명 '{cleaned}'이 모델명 '{result['model']}'과 URL로 저장되었습니다.",
    }


def _lookup_product_info(product_name: str) -> dict[str, str] | None:
    if product_name in product_name_to_model:
        return product_name_to_model[product_name]

    lowered = product_name.lower()
    for key, value in product_name_to_model.items():
        if key.lower() == lowered:
            return value
    return None


async def _crawl_product(product_name: str) -> dict[str, object]:
    cleaned = product_name.strip()
    if not cleaned:
        raise ValueError("제품 이름을 입력해주세요.")

    product_info = _lookup_product_info(cleaned)
    if not product_info:
        raise ValueError("먼저 normalize_product_name 도구를 호출하여 제품 URL을 저장하세요.")

    url = product_info["url"]
    images = await crawl_single_page(url)

    return {
        "product_name": cleaned,
        "url": url,
        "image_count": len(images),
        "images": images,
        "success": True,
        "message": f"제품 '{cleaned}'의 이미지 {len(images)}개를 base64로 인코딩했습니다.",
    }


@server.list_tools()
async def handle_list_tools():
    return list(TOOL_DEFINITIONS.values())


@server.call_tool()
async def handle_call_tool(tool_name: str, arguments: dict[str, object]):
    if tool_name not in TOOL_DEFINITIONS:
        raise ValueError(f"알 수 없는 도구: {tool_name}")

    product_name = str(arguments.get("product_name", "")).strip()

    if tool_name == "normalize_product_name":
        return _normalize_product(product_name)

    if tool_name == "crawl_product_images":
        return await _crawl_product(product_name)

    raise ValueError(f"핸들링되지 않은 도구: {tool_name}")


async def main():
    """STDIO 기반 MCP 서버 실행."""
    async with stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    anyio.run(main)

