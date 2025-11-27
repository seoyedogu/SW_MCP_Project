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
    outdir: str | None = None  # 기본값은 None으로 설정하고, 엔드포인트에서 기본 경로 설정

class CrawlResponse(BaseModel):
    product_name: str
    url: str
    outdir: str
    image_count: int
    saved_files: list[str]
    success: bool
    message: str

