"""
제품 비교 기능 모듈

여러 제품을 정규화하고 이미지를 수집하여 비교 가능한 형태로 반환하는 로직을 제공합니다.
"""

import traceback
from typing import Any

from fastapi import HTTPException

from .new_single_page_crawler import crawl_single_page
from .normalize_product_name import (
    convert_product_name_to_model,
    product_name_to_model,
)


async def compare_products_logic(product_names: list[str]) -> dict[str, Any]:
    """
    여러 제품을 비교하기 위해 각 제품을 정규화하고 이미지를 수집하는 로직
    
    두 개 이상의 제품명을 입력받아 각 제품을 정규화하고 이미지를 수집합니다.
    반환된 데이터를 통해 LLM이 공통점과 차이점을 분석할 수 있습니다.
    
    Args:
        product_names: 비교할 제품명 리스트 (최소 2개 이상)
    
    Returns:
        dict: 각 제품의 정규화된 정보와 이미지 리스트를 포함한 딕셔너리
        
    Raises:
        HTTPException: 입력 검증 실패 또는 모든 제품 처리 실패 시
    """
    # 입력 검증
    if not product_names or len(product_names) < 2:
        raise HTTPException(
            status_code=400,
            detail="최소 2개 이상의 제품명을 입력해주세요."
        )
    
    products_info = []
    errors = []
    
    # 각 제품 처리
    for product_name in product_names:
        product_name = product_name.strip()
        if not product_name:
            continue
            
        try:
            # 1. 제품명 정규화
            result = convert_product_name_to_model(product_name)
            if not result:
                error_detail = (
                    f"제품명 '{product_name}'에 대한 모델명을 찾을 수 없습니다.\n"
                    "가능한 원인: 제품명이 정확하지 않거나, 다른 숫자/명칭일 수 있습니다."
                )
                errors.append(error_detail)
                continue
            
            model_name = result["model"]
            product_url = result["url"]
            
            # 메모리에 저장
            product_name_to_model[product_name] = result
            
            # 2. 이미지 크롤링
            print(f"[INFO] 크롤링 시작 - 제품명: {product_name}, URL: {product_url}")
            images_data = await crawl_single_page(product_url)
            print(f"[INFO] 크롤링 완료 - 제품명: {product_name}, 이미지 {len(images_data)}개 base64 인코딩 완료")
            
            products_info.append({
                "product_name": product_name,
                "model_name": model_name,
                "url": product_url,
                "image_count": len(images_data),
                "images": images_data,
            })
        except Exception as e:
            error_detail = str(e)
            error_traceback = traceback.format_exc()
            print(f"[ERROR] 제품 '{product_name}' 처리 실패")
            print(f"[ERROR] 오류 내용: {error_detail}")
            print(f"[ERROR] 전체 트레이스백:")
            print(error_traceback)
            errors.append(f"제품 '{product_name}' 처리 중 오류: {error_detail}")
            # 오류가 발생해도 다른 제품 처리는 계속 진행
    
    # 모든 제품 처리 실패 시
    if not products_info:
        all_errors = "\n".join(errors) if errors else "알 수 없는 오류"
        raise HTTPException(
            status_code=500,
            detail=(
                f"모든 제품 처리에 실패했습니다.\n\n"
                f"실패한 제품들:\n{all_errors}\n\n"
                "해결 방법:\n"
                "1. 각 제품명의 정확성을 확인하세요\n"
                "2. 제조사명 포함 여부를 확인하세요 (예: \"삼성 전자 블루스카이 3100\")\n"
                "3. 다나와에서 직접 검색하여 정확한 제품명을 확인하세요"
            )
        )
    
    # 결과 메시지 생성
    message = f"{len(products_info)}개 제품의 정보를 수집했습니다."
    if errors:
        error_summary = "\n".join(errors[:3])  # 최대 3개만 표시
        if len(errors) > 3:
            error_summary += f"\n... 외 {len(errors) - 3}개 제품 처리 실패"
        message += f"\n\n주의: {len(errors)}개 제품 처리 실패:\n{error_summary}"
    
    # 비교를 위한 가이드 추가
    comparison_guide = (
        "\n\n[비교 가이드]\n"
        "수집된 제품 정보를 바탕으로 다음 항목을 중심으로 차이점을 비교해주세요:\n"
        "1. 제품 디자인: 색상, 형태, 크기 등의 차이\n"
        "2. 제품 특징: 기능, 성능, 사양 등의 차이\n"
        "3. 가격대: 다나와 링크를 통해 최신 가격 확인 가능\n"
        "4. 주요 차이점: 각 제품의 고유한 특징과 장단점\n"
        "\n공통점보다는 차이점에 집중하여 비교 설명해주세요."
    )
    
    return {
        "products": products_info,
        "total_products": len(products_info),
        "success": True,
        "message": message + comparison_guide,
        "comparison_hint": {
            "focus": "차이점",
            "comparison_points": [
                "제품 디자인 (색상, 형태, 크기)",
                "제품 특징 (기능, 성능, 사양)",
                "가격대",
                "주요 차이점 및 고유 특징"
            ],
            "note": "공통점보다는 차이점에 집중하여 비교해주세요."
        },
    }

