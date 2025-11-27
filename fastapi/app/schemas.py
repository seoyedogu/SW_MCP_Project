from pydantic import BaseModel

class ProductNameToModelRequest(BaseModel):
    product_name: str

class ProductNameToModelResponse(BaseModel):
    product_name: str
    model_name: str
    saved: bool
    message: str

class ProductNameToModelMappingsResponse(BaseModel):
    mappings: dict[str, str]
    total_count: int

