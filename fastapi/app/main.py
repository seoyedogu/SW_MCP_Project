from fastapi import FastAPI, HTTPException

from . import schemas
from .compare_products import compare_products_logic
from .new_single_page_crawler import crawl_single_page
from .normalize_product_name import (
    convert_product_name_to_model,
    product_name_to_model,
)

app = FastAPI(
    title="FastAPI Application",
    version="1.0.0",
    description="FastAPI 기본 애플리케이션",
)


@app.get("/")
def root() -> dict[str, str]:
    """루트 엔드포인트"""
    return {"message": "Welcome to FastAPI"}


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """상태 확인 엔드포인트"""
    return {"status": "ok"}


# 제품명을 모델명으로 변환하는 엔드포인트
@app.post("/normalize-product-name", response_model=schemas.ProductNameToModelResponse)
def normalize_product_name(request: schemas.ProductNameToModelRequest):
    """
    제품 이름을 모델명으로 정규화
    
    사용자가 제품 이름을 입력하면 모델명으로 변환하여 저장합니다.
    변환된 매핑은 메모리에 저장되며, 나중에 크롤링할 때 사용됩니다.
    
    Args:
        request: ProductNameToModelRequest (product_name: 제품 이름)
    
    Returns:
        ProductNameToModelResponse: 변환된 모델명 및 저장된 매핑 정보
    """
    if not request.product_name or not request.product_name.strip():
        raise HTTPException(status_code=400, detail="제품 이름을 입력해주세요.")
    
    product_name = request.product_name.strip()
    
    # 제품명을 모델명과 URL로 변환하는 로직
    # 예: "삼성 블루스카이 5500" -> {"model": "AX060CG500G", "url": "http://..."}
    result = convert_product_name_to_model(product_name)
    
    if not result:
        # 더 상세한 오류 메시지 제공
        error_detail = (
            f"제품명 '{product_name}'에 대한 모델명을 찾을 수 없습니다.\n\n"
            "가능한 원인:\n"
            "1. 정확한 제품명 확인 필요\n"
            f"   • \"{product_name}\" 대신 다른 숫자나 명칭일 수 있습니다\n"
            "   • 예: \"블루스카이 3100\" → \"블루스카이 3000\" 또는 \"블루스카이 3500\"\n"
            "2. 제품명 변형 시도\n"
            "   • 제조사명 포함 여부 확인 (예: \"삼성 전자 블루스카이 3100\")\n"
            "   • 띄어쓰기 확인\n"
            "3. 다나와에서 직접 검색하여 정확한 제품명 확인"
        )
        raise HTTPException(
            status_code=404,
            detail=error_detail
        )
    
    model_name = result["model"]
    product_url = result["url"]
    
    # 메모리에 저장 (key: 제품명, value: {"model": 모델명, "url": URL})
    product_name_to_model[product_name] = result
    
    return {
        "product_name": product_name,
        "model_name": model_name,
        "url": product_url,
        "saved": True,
        "message": f"제품명 '{product_name}'이 모델명 '{model_name}'과 URL로 저장되었습니다."
    }


# 크롤링 엔드포인트
@app.post("/crawl", response_model=schemas.CrawlResponse)
async def crawl_product_images(request: schemas.CrawlRequest):
    """
    저장된 제품 URL을 사용하여 이미지를 크롤링하는 엔드포인트
    
    제품명을 입력하면 저장된 URL을 찾아서 해당 페이지의 이미지를 다운로드합니다.
    
    Args:
        request: CrawlRequest (product_name: 제품 이름, outdir: 저장 경로 (선택))
    
    Returns:
        CrawlResponse: 크롤링 결과 정보
    """
    if not request.product_name or not request.product_name.strip():
        raise HTTPException(status_code=400, detail="제품 이름을 입력해주세요.")
    
    product_name = request.product_name.strip()
    
    # 저장된 매핑에서 URL 찾기
    if product_name not in product_name_to_model:
        # 대소문자 무시로 검색
        found = False
        for key, value in product_name_to_model.items():
            if key.lower() == product_name.lower():
                product_name = key  # 원본 키 사용
                found = True
                break
        
        if not found:
            raise HTTPException(
                status_code=404,
                detail=f"제품명 '{product_name}'에 대한 저장된 URL을 찾을 수 없습니다. 먼저 /normalize-product-name 엔드포인트를 사용하여 제품명을 등록해주세요."
            )
    
    product_info = product_name_to_model[product_name]
    product_url = product_info["url"]
    
    # 크롤링 실행
    try:
        print(f"[INFO] 크롤링 시작 - 제품명: {product_name}, URL: {product_url}")
        images_data = await crawl_single_page(product_url)
        
        print(f"[INFO] 크롤링 완료 - 이미지 {len(images_data)}개 base64 인코딩 완료")
        
        return {
            "product_name": product_name,
            "url": product_url,
            "image_count": len(images_data),
            "images": images_data,
            "success": True,
            "message": f"제품 '{product_name}'의 이미지 {len(images_data)}개를 성공적으로 크롤링하고 base64로 인코딩했습니다."
        }
    except Exception as e:
        import traceback
        error_detail = str(e)
        error_traceback = traceback.format_exc()
        # 더 자세한 오류 정보를 로그에 출력
        print(f"[ERROR] 크롤링 실패 - 제품명: {product_name}")
        print(f"[ERROR] 오류 내용: {error_detail}")
        print(f"[ERROR] 전체 트레이스백:")
        print(error_traceback)
        raise HTTPException(
            status_code=500,
            detail=f"크롤링 중 오류가 발생했습니다: {error_detail}"
        )


# 제품 비교 엔드포인트
@app.post("/compare-products", response_model=schemas.CompareProductsResponse)
async def compare_products(request: schemas.CompareProductsRequest):
    """
    여러 제품을 비교하기 위해 각 제품을 정규화하고 이미지를 수집하는 엔드포인트
    
    두 개 이상의 제품명을 입력받아 각 제품을 정규화하고 이미지를 수집합니다.
    반환된 데이터를 통해 LLM이 공통점과 차이점을 분석할 수 있습니다.
    
    Args:
        request: CompareProductsRequest (product_names: 제품명 리스트)
    
    Returns:
        CompareProductsResponse: 각 제품의 정규화된 정보와 이미지 리스트
    """
    return await compare_products_logic(request.product_names)


# 직접 실행 가능하도록 설정
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
