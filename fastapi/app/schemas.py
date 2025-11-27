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

class CrawlResponse(BaseModel):
    product_name: str
    url: str
    image_count: int
    images: list[ImageData]
    success: bool
    message: str

