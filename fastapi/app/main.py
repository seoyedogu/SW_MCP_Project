from fastapi import FastAPI, HTTPException

from . import schemas
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
    
    # 제품명을 모델명으로 변환하는 로직
    # 예: "삼성 블루스카이 5500" -> "AX060CG500G"
    model_name = convert_product_name_to_model(product_name)
    
    if not model_name:
        raise HTTPException(
            status_code=404,
            detail=f"제품명 '{product_name}'에 대한 모델명을 찾을 수 없습니다."
        )
    
    # 메모리에 저장 (key: 제품명, value: 모델명)
    product_name_to_model[product_name] = model_name
    
    return {
        "product_name": product_name,
        "model_name": model_name,
        "saved": True,
        "message": f"제품명 '{product_name}'이 모델명 '{model_name}'으로 저장되었습니다."
    }


# 직접 실행 가능하도록 설정
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
