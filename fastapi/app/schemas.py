from pydantic import BaseModel

class ProductNameToModelRequest(BaseModel):
    product_name: str

class ProductNameToModelResponse(BaseModel):
    product_name: str
    model_name: str
    url: str
    saved: bool
    message: str

class ProductNameToModelMappingsResponse(BaseModel):
    mappings: dict[str, dict[str, str]]  # {"제품명": {"model": "모델명", "url": "URL"}}
    total_count: int

class CrawlRequest(BaseModel):
    product_name: str

class ImageData(BaseModel):
    url: str
    base64: str
    mime_type: str
    index: int
    original_size_bytes: int | None = None
    optimized_size_bytes: int | None = None

class CrawlResponse(BaseModel):
    product_name: str
    url: str
    image_count: int
    images: list[ImageData]
    success: bool
    message: str

class ProductInfo(BaseModel):
    """단일 제품의 정규화된 정보와 이미지"""
    product_name: str
    model_name: str
    url: str
    image_count: int
    images: list[ImageData]

class CompareProductsRequest(BaseModel):
    product_names: list[str]  # 비교할 제품명 리스트

class ComparisonHint(BaseModel):
    """비교를 위한 가이드"""
    focus: str
    comparison_points: list[str]
    note: str
    output_format: str | None = None  # 출력 형식에 대한 지시

class CompareProductsResponse(BaseModel):
    """여러 제품 비교 결과"""
    products: list[ProductInfo]  # 각 제품의 정보와 이미지
    total_products: int
    success: bool
    message: str
    comparison_hint: ComparisonHint | None = None  # 비교를 위한 가이드

class AnalyzeProductRequest(BaseModel):
    """제품 분석 요청"""
    product_name: str
    analysis_type: str = "general"  # "general", "detailed", "comparison"

class AnalyzeProductResponse(BaseModel):
    """제품 분석 응답"""
    product_name: str
    model_name: str
    url: str
    analysis: str
    success: bool
    message: str
    json_file: str | None = None  # 저장된 JSON 파일 경로

class CompareWithAIRequest(BaseModel):
    """AI를 통한 제품 비교 요청"""
    product_names: list[str]

class CompareWithAIResponse(BaseModel):
    """AI를 통한 제품 비교 응답"""
    products: list[ProductInfo]
    comparison_analysis: str
    success: bool
    message: str
    json_file: str | None = None  # 저장된 JSON 파일 경로

