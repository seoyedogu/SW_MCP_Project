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
    "compare_products": types.Tool(
        name="compare_products",
        description=(
            "두 개 이상의 제품명을 입력받아 각 제품을 정규화하고 이미지를 수집하여 비교 가능한 형태로 반환합니다. "
            "각 제품의 정보와 이미지를 구조화하여 제공하므로 LLM이 차이점을 위주로 비교 분석할 수 있습니다. "
            "비교 시 디자인, 특징, 가격대 등의 차이점에 집중하여 설명해주세요. "
            "출력 시 이미지 태그나 URL을 포함하지 말고, 깔끔한 텍스트 형식으로만 비교 분석 결과를 제공하세요."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "product_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "비교할 제품명 리스트 (최소 2개 이상)",
                    "minItems": 2,
                }
            },
            "required": ["product_names"],
        },
        outputSchema={
            "type": "object",
            "properties": {
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_name": {"type": "string"},
                            "model_name": {"type": "string"},
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
                                },
                            },
                        },
                        "required": ["product_name", "model_name", "url", "image_count", "images"],
                    },
                },
                "total_products": {"type": "integer"},
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "comparison_hint": {
                    "type": "object",
                    "properties": {
                        "focus": {"type": "string"},
                        "comparison_points": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "note": {"type": "string"},
                    },
                },
            },
            "required": ["products", "total_products", "success", "message"],
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
        # 더 상세한 오류 메시지 제공
        error_msg = (
            f"MCP 서버에서 \"{cleaned}\" 제품을 찾지 못했습니다.\n\n"
            "몇 가지 가능성이 있습니다:\n"
            "1. 정확한 제품명 확인 필요\n"
            "   • 제품명이 정확하지 않을 수 있습니다\n"
            f"   • \"{cleaned}\" 대신 다른 숫자나 명칭일 수 있습니다\n"
            "   • 예: \"블루스카이 3100\" → \"블루스카이 3000\" 또는 \"블루스카이 3500\"\n"
            "2. 제품명 변형 시도\n"
            "   • 제조사명 포함 여부 확인 (예: \"삼성 전자 블루스카이 3100\")\n"
            "   • 띄어쓰기 확인 (예: \"블루스카이3100\" vs \"블루스카이 3100\")\n"
            "3. 다나와에서 직접 검색\n"
            "   • 다나와 웹사이트에서 정확한 제품명을 확인해보세요"
        )
        raise ValueError(error_msg)

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


async def _compare_products(product_names: list[str]) -> dict[str, object]:
    """여러 제품을 정규화하고 이미지를 수집하여 비교 가능한 형태로 반환"""
    if not product_names or len(product_names) < 2:
        raise ValueError("최소 2개 이상의 제품명을 입력해주세요.")
    
    products_info = []
    errors = []
    
    for product_name in product_names:
        try:
            # 1. 제품명 정규화
            normalized = _normalize_product(product_name)
            model_name = normalized["model_name"]
            url = normalized["url"]
            
            # 2. 이미지 크롤링
            images = await crawl_single_page(url)
            
            products_info.append({
                "product_name": normalized["product_name"],
                "model_name": model_name,
                "url": url,
                "image_count": len(images),
                "images": images,
            })
        except ValueError as e:
            # 정규화 실패 시 상세한 오류 메시지 포함
            error_msg = f"제품 '{product_name}': {str(e)}"
            errors.append(error_msg)
            # 오류가 발생해도 다른 제품 처리는 계속 진행
        except Exception as e:
            error_msg = f"제품 '{product_name}' 처리 중 오류: {str(e)}"
            errors.append(error_msg)
            # 오류가 발생해도 다른 제품 처리는 계속 진행
    
    if not products_info:
        all_errors = "\n".join(errors) if errors else "알 수 없는 오류"
        raise ValueError(
            f"모든 제품 처리에 실패했습니다.\n\n"
            f"실패한 제품들:\n{all_errors}\n\n"
            "해결 방법:\n"
            "1. 각 제품명의 정확성을 확인하세요\n"
            "2. 제조사명 포함 여부를 확인하세요\n"
            "3. 다나와에서 직접 검색하여 정확한 제품명을 확인하세요"
        )
    
    message = f"{len(products_info)}개 제품의 정보를 수집했습니다."
    if errors:
        message += f"\n\n주의: {len(errors)}개 제품 처리 실패:\n" + "\n".join(errors[:3])  # 최대 3개만 표시
        if len(errors) > 3:
            message += f"\n... 외 {len(errors) - 3}개"
    
    # 비교를 위한 가이드 추가
    comparison_guide = (
        "\n\n[비교 분석 가이드]\n"
        "수집된 제품 이미지와 정보를 바탕으로 다음 항목을 중심으로 차이점을 비교 분석해주세요:\n"
        "1. 제품 디자인: 색상, 형태, 크기 등의 차이\n"
        "2. 제품 특징: 기능, 성능, 사양 등의 차이\n"
        "3. 가격대: 다나와 링크를 통해 최신 가격 확인 가능\n"
        "4. 주요 차이점: 각 제품의 고유한 특징과 장단점\n"
        "\n[출력 형식]\n"
        "- 이미지 태그나 URL을 출력하지 마세요. 이미지는 이미 제공되었으므로 직접 참조하여 분석하세요.\n"
        "- 깔끔하고 읽기 쉬운 텍스트 형식으로만 출력하세요.\n"
        "- 제품명, 모델명, 주요 특징, 차이점을 명확하게 정리하여 설명하세요.\n"
        "- 공통점보다는 차이점에 집중하여 비교 설명해주세요."
    )
    
    return {
        "products": products_info,
        "total_products": len(products_info),
        "success": len(products_info) > 0,
        "message": message + comparison_guide,
        "comparison_hint": {
            "focus": "차이점",
            "comparison_points": [
                "제품 디자인 (색상, 형태, 크기)",
                "제품 특징 (기능, 성능, 사양)",
                "가격대",
                "주요 차이점 및 고유 특징"
            ],
            "note": "공통점보다는 차이점에 집중하여 비교해주세요.",
            "output_format": "이미지 태그나 URL을 출력하지 말고, 깔끔한 텍스트 형식으로만 비교 분석 결과를 제공하세요."
        },
    }


@server.list_tools()
async def handle_list_tools():
    return list(TOOL_DEFINITIONS.values())


@server.call_tool()
async def handle_call_tool(tool_name: str, arguments: dict[str, object]):
    if tool_name not in TOOL_DEFINITIONS:
        raise ValueError(f"알 수 없는 도구: {tool_name}")

    if tool_name == "normalize_product_name":
        product_name = str(arguments.get("product_name", "")).strip()
        return _normalize_product(product_name)

    if tool_name == "crawl_product_images":
        product_name = str(arguments.get("product_name", "")).strip()
        return await _crawl_product(product_name)

    if tool_name == "compare_products":
        product_names_raw = arguments.get("product_names", [])
        if not isinstance(product_names_raw, list):
            raise ValueError("product_names는 리스트여야 합니다.")
        product_names = [str(name).strip() for name in product_names_raw if str(name).strip()]
        return await _compare_products(product_names)

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

