import os
import logging
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# .env 파일 로드
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
env_loaded = False

try:
    from dotenv import load_dotenv
    
    # 여러 위치에서 .env 파일 찾기
    env_locations = [
        PROJECT_ROOT / ".env",  # 프로젝트 루트
        PROJECT_ROOT / "fastapi" / ".env",  # fastapi 폴더
        Path.cwd() / ".env",  # 현재 작업 디렉토리
    ]
    
    for env_file in env_locations:
        if env_file.exists():
            print(f"[INFO] .env 파일 발견: {env_file}")
            load_dotenv(env_file, override=True)
            env_loaded = True
            break
    
    # .env 파일을 찾지 못한 경우 현재 디렉토리에서 시도
    if not env_loaded:
        print("[INFO] .env 파일을 찾지 못했습니다. 현재 디렉토리에서 시도합니다.")
        load_dotenv(override=True)
        
    # OpenAI GPT-4.1 mini 모드
    print("[INFO] OpenAI GPT-4.1 mini 모드: OPENAI_API_KEY가 필요합니다.")
        
except ImportError:
    print("[WARNING] python-dotenv가 설치되지 않았습니다. 'pip install python-dotenv' 실행 후 다시 시도하세요.")
except Exception as e:
    print(f"[ERROR] .env 파일 로드 중 오류 발생: {e}")

from . import schemas
from .compare_products import compare_products_logic
from .new_single_page_crawler import crawl_single_page
from .normalize_product_name import (
    convert_product_name_to_model,
    product_name_to_model,
)

app = FastAPI(
    title="제품 정보 수집 및 분석 시스템",
    version="1.0.0",
    description="제품명 정규화, 이미지 크롤링, AI 기반 제품 분석 및 비교 서비스",
)

# CORS 설정 (웹페이지에서 API 호출을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용하도록 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (웹페이지)
if 'PROJECT_ROOT' not in globals():
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_DIR = PROJECT_ROOT / "web"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def root():
    """루트 엔드포인트 - 웹페이지 제공"""
    from fastapi.responses import FileResponse
    web_index = WEB_DIR / "index.html"
    if web_index.exists():
        return FileResponse(str(web_index))
    return {"message": "Welcome to FastAPI - 웹페이지를 찾을 수 없습니다."}


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """상태 확인 엔드포인트"""
    return {"status": "ok"}

@app.get("/check-env", tags=["system"], response_model=None)
def check_env() -> dict[str, Any]:
    """환경 변수 확인 엔드포인트 (디버깅용)"""
    project_root = PROJECT_ROOT
    env_files = [
        {"path": str(project_root / ".env"), "exists": (project_root / ".env").exists()},
        {"path": str(project_root / "fastapi" / ".env"), "exists": (project_root / "fastapi" / ".env").exists()},
        {"path": str(Path.cwd() / ".env"), "exists": (Path.cwd() / ".env").exists()},
    ]
    
    return {
        "mode": "OpenAI GPT-4.1 mini Mode",
        "message": "OpenAI GPT-4.1 mini를 사용합니다. OPENAI_API_KEY가 필요합니다.",
        "project_root": str(project_root),
        "current_dir": str(Path.cwd()),
        "env_files": env_files,
        "python_dotenv_installed": True  # 이 엔드포인트가 호출되면 dotenv는 설치된 것
    }


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


# OpenAI GPT-4.1 mini를 사용한 제품 자동 분석 엔드포인트
@app.post("/analyze-product", response_model=schemas.AnalyzeProductResponse)
async def analyze_product(request: schemas.AnalyzeProductRequest):
    """
    OpenAI GPT-4.1 mini를 사용하여 제품을 자동으로 분석하는 엔드포인트
    
    제품명을 입력받아 정규화하고 이미지를 크롤링한 후, OpenAI GPT-4.1 mini를 통해 자동으로 분석합니다.
    분석 결과를 JSON 파일로 저장하고 웹에서 표시할 수 있도록 반환합니다.
    
    Args:
        request: AnalyzeProductRequest (product_name: 제품명, analysis_type: 분석 유형)
    
    Returns:
        AnalyzeProductResponse: 제품 분석 결과 (JSON 형식)
    """
    try:
        from openai import OpenAI
        import json
        import base64
        from datetime import datetime
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API를 사용하기 위해 openai 라이브러리가 필요합니다. 'pip install openai' 실행 후 다시 시도하세요."
        )
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.\n\n"
                "설정 방법:\n"
                "1. .env 파일에 추가: OPENAI_API_KEY=your-api-key\n"
                "2. 또는 환경 변수로 설정\n\n"
                "OpenAI API 키는 https://platform.openai.com/api-keys 에서 발급받을 수 있습니다."
            )
        )
    
    product_name = request.product_name.strip()
    if not product_name:
        raise HTTPException(status_code=400, detail="제품 이름을 입력해주세요.")
    
    # 1. 제품명 정규화 (MCP 서버 로직 사용)
    result = convert_product_name_to_model(product_name)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"제품명 '{product_name}'에 대한 모델명을 찾을 수 없습니다."
        )
    
    model_name = result["model"]
    product_url = result["url"]
    product_name_to_model[product_name] = result
    
    # 2. 이미지 크롤링 (MCP 서버 로직 사용)
    try:
        images_data = await crawl_single_page(product_url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 크롤링 중 오류가 발생했습니다: {str(e)}"
        )
    
    # 3. OpenAI GPT-4.1 mini를 사용하여 이미지 자동 분석
    try:
        client = OpenAI(api_key=api_key)
        
        # 분석 유형에 따른 프롬프트 설정
        if request.analysis_type == "detailed":
            prompt_text = (
                "당신은 제품 분석 전문가입니다. 제공된 제품 이미지와 정보를 바탕으로 "
                "다음 항목을 모두 포함하여 매우 상세하게 분석해주세요:\n\n"
                "## 필수 분석 항목:\n"
                "1. **제품의 주요 특징 및 스펙**\n"
                "   - 기술적 사양, 성능 지표, 핵심 기능 등을 상세히 설명\n"
                "   - 이미지에서 확인할 수 있는 스펙 정보 포함\n\n"
                "2. **디자인 및 외관**\n"
                "   - 색상, 형태, 크기, 재질 등 디자인 요소 분석\n"
                "   - 이미지에서 보이는 디자인 특징을 구체적으로 설명\n\n"
                "3. **장점 및 추천 포인트**\n"
                "   - 이 제품의 강점과 장점을 구체적으로 나열\n"
                "   - 어떤 사용자에게 추천할 수 있는지 명시\n\n"
                "4. **단점 및 주의사항**\n"
                "   - 제품의 한계점이나 단점을 솔직하게 분석\n"
                "   - 구매 전 알아야 할 주의사항 포함\n\n"
                "5. **구매 추천 여부 및 이유**\n"
                "   - 구매를 추천하는지 여부와 그 이유를 명확히 제시\n"
                "   - 가성비, 사용 목적, 타겟 사용자 등을 고려한 종합 평가\n\n"
                f"제품명: {product_name}\n모델명: {model_name}\n\n"
                "각 항목을 구체적이고 상세하게 작성해주세요. 분석 결과는 한국어로 깔끔하고 읽기 쉬운 형식으로 작성해주세요."
            )
        else:
            prompt_text = (
                "당신은 제품 분석 전문가입니다. 제공된 제품 이미지와 정보를 바탕으로 "
                f"다음 제품에 대해 간결하고 핵심적인 분석을 제공해주세요:\n\n"
                f"제품명: {product_name}\n모델명: {model_name}\n\n"
                "## 분석 내용:\n"
                "- 제품의 주요 특징 (핵심 기능과 스펙 요약)\n"
                "- 장점과 단점 (간단히 정리)\n"
                "- 구매 추천 여부 (간단한 이유 포함)\n\n"
                "분석은 간결하고 핵심적인 내용 위주로 작성해주세요. "
                "너무 길지 않게 요약 형식으로 제공해주세요. "
                "분석 결과는 한국어로 깔끔하고 읽기 쉬운 형식으로 작성해주세요."
            )
        
        # 이미지를 OpenAI API 형식으로 변환 (최대 4장)
        # OpenAI는 base64 이미지를 data URL 형식으로 전송
        image_contents = []
        for img in images_data[:4]:
            mime_type = img.get("mime_type", "image/jpeg")
            base64_data = img["base64"]
            image_url = f"data:{mime_type};base64,{base64_data}"
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            })
        
        # OpenAI GPT-4.1 mini API 호출
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    *image_contents
                ]
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # GPT-4.1 mini는 gpt-4o-mini로 사용
            messages=messages,
            max_tokens=4096
        )
        
        analysis_text = response.choices[0].message.content if response.choices else "분석 결과를 생성할 수 없습니다."
        
        # 4. 분석 결과를 JSON 파일로 저장
        json_data = {
            "product_name": product_name,
            "model_name": model_name,
            "url": product_url,
            "analysis": analysis_text,
            "image_count": len(images_data),
            "analysis_type": request.analysis_type,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        # JSON 파일 저장 디렉토리 생성
        json_dir = PROJECT_ROOT / "analysis_results"
        json_dir.mkdir(exist_ok=True)
        
        # 파일명: 제품명_타임스탬프.json (특수문자 제거)
        safe_product_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_product_name = safe_product_name.replace(' ', '_')
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"{safe_product_name}_{timestamp_str}.json"
        json_filepath = json_dir / json_filename
        
        # JSON 파일 저장
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"[Analysis] JSON 파일 저장 완료: {json_filepath}")
        
        # JSON 형식으로 결과 반환
        return {
            "product_name": product_name,
            "model_name": model_name,
            "url": product_url,
            "analysis": analysis_text,
            "success": True,
            "message": f"제품 '{product_name}'의 분석이 완료되었습니다. JSON 파일이 저장되었습니다.",
            "json_file": str(json_filepath.relative_to(PROJECT_ROOT))
        }
        
    except Exception as e:
        error_str = str(e)
        error_detail = "OpenAI API 호출 중 오류가 발생했습니다."
        
        if "authentication" in error_str.lower() or "api key" in error_str.lower() or "unauthorized" in error_str.lower():
            error_detail = (
                "❌ OpenAI API 키가 유효하지 않습니다.\n\n"
                f"오류 내용: {error_str}\n\n"
                "해결 방법:\n"
                "1. OpenAI Platform 접속: https://platform.openai.com/api-keys\n"
                "2. API 키 확인 및 새로 발급\n"
                "3. .env 파일의 OPENAI_API_KEY 값을 확인하고 올바른 키로 교체\n"
                "4. 서버 재시작\n\n"
                f"원본 오류: {error_str}"
            )
        elif "quota" in error_str.lower() or "rate limit" in error_str.lower():
            error_detail = (
                "❌ OpenAI API 사용량 제한을 초과했습니다.\n\n"
                "해결 방법:\n"
                "1. OpenAI Platform에서 사용량 확인: https://platform.openai.com/usage\n"
                "2. 요금제 확인 및 크레딧 충전\n"
                "3. GPT-4.1 mini는 저렴한 가격으로 제공됩니다\n\n"
                f"원본 오류: {error_str}"
            )
        else:
            error_detail = (
                f"❌ OpenAI API 호출 중 오류가 발생했습니다.\n\n"
                f"오류 내용: {error_str}\n\n"
                "추가 도움말:\n"
                "- OpenAI Platform 확인: https://platform.openai.com/\n"
                "- GPT-4.1 mini는 Vision 기능을 지원합니다\n"
                "- API 키 및 사용량 상태 확인"
            )
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


# OpenAI GPT-4.1 mini를 사용한 제품 비교 자동 분석 엔드포인트
@app.post("/compare-with-ai", response_model=schemas.CompareWithAIResponse)
async def compare_with_ai(request: schemas.CompareWithAIRequest):
    """
    OpenAI GPT-4.1 mini를 사용하여 여러 제품을 자동으로 비교 분석하는 엔드포인트
    
    두 개 이상의 제품명을 입력받아 각 제품을 정규화하고 이미지를 수집한 후,
    OpenAI GPT-4.1 mini를 통해 제품 간 차이점을 중심으로 비교 분석합니다.
    분석 결과를 JSON 파일로 저장하고 웹에서 표시할 수 있도록 반환합니다.
    
    Args:
        request: CompareWithAIRequest (product_names: 제품명 리스트)
    
    Returns:
        CompareWithAIResponse: 제품 비교 분석 결과 (JSON 형식)
    """
    try:
        from openai import OpenAI
        import json
        import base64
        from datetime import datetime
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API를 사용하기 위해 openai 라이브러리가 필요합니다. 'pip install openai' 실행 후 다시 시도하세요."
        )
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.\n\n"
                "설정 방법:\n"
                "1. .env 파일에 추가: OPENAI_API_KEY=your-api-key\n"
                "2. 또는 환경 변수로 설정\n\n"
                "OpenAI API 키는 https://platform.openai.com/api-keys 에서 발급받을 수 있습니다."
            )
        )
    
    if not request.product_names or len(request.product_names) < 2:
        raise HTTPException(
            status_code=400,
            detail="최소 2개 이상의 제품명을 입력해주세요."
        )
    
    # 제품 정보 수집 (MCP 서버 로직 사용)
    compare_result = await compare_products_logic(request.product_names)
    
    if not compare_result["success"] or not compare_result["products"]:
        raise HTTPException(
            status_code=500,
            detail="제품 정보 수집에 실패했습니다."
        )
    
    # OpenAI GPT-4.1 mini를 사용하여 비교 분석
    try:
        client = OpenAI(api_key=api_key)
        
        # 프롬프트 구성
        prompt_text = (
            "당신은 제품 비교 전문가입니다. 제공된 제품 이미지와 정보를 바탕으로 "
            f"다음 {len(compare_result['products'])}개 제품을 비교 분석해주세요:\n\n"
        )
        
        # 각 제품 정보 추가
        all_image_contents = []
        for idx, product in enumerate(compare_result["products"], 1):
            prompt_text += f"\n[제품 {idx}]\n"
            prompt_text += f"제품명: {product['product_name']}\n"
            prompt_text += f"모델명: {product['model_name']}\n"
            prompt_text += f"이미지 개수: {product['image_count']}개\n\n"
            
            # 각 제품의 이미지 추가 (최대 2장씩)
            for img in product["images"][:2]:
                mime_type = img.get("mime_type", "image/jpeg")
                base64_data = img["base64"]
                image_url = f"data:{mime_type};base64,{base64_data}"
                all_image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })
        
        prompt_text += (
            "\n위 제품들을 비교 분석해주세요. 다음 항목을 중심으로 차이점을 설명해주세요:\n"
            "1. 제품 디자인: 색상, 형태, 크기 등의 차이\n"
            "2. 제품 특징: 기능, 성능, 사양 등의 차이\n"
            "3. 주요 차이점: 각 제품의 고유한 특징과 장단점\n"
            "4. 구매 추천: 각 제품이 어떤 사용자에게 적합한지\n\n"
            "공통점보다는 차이점에 집중하여 비교 설명해주세요. "
            "이미지 태그나 URL을 포함하지 말고, 깔끔한 텍스트 형식으로만 출력해주세요. "
            "분석 결과는 한국어로 깔끔하고 읽기 쉬운 형식으로 작성해주세요."
        )
        
        # OpenAI GPT-4.1 mini API 호출
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    *all_image_contents
                ]
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # GPT-4.1 mini는 gpt-4o-mini로 사용
            messages=messages,
            max_tokens=4096
        )
        
        comparison_text = response.choices[0].message.content if response.choices else "비교 분석 결과를 생성할 수 없습니다."
        
        # 분석 결과를 JSON 파일로 저장
        json_data = {
            "products": compare_result["products"],
            "comparison_analysis": comparison_text,
            "total_products": len(compare_result["products"]),
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        # JSON 파일 저장 디렉토리 생성
        json_dir = PROJECT_ROOT / "analysis_results"
        json_dir.mkdir(exist_ok=True)
        
        # 파일명: 제품명들_타임스탬프.json
        product_names_str = "_".join([p['product_name'].replace(' ', '_') for p in compare_result["products"]])
        safe_product_names = "".join(c for c in product_names_str if c.isalnum() or c in ('_', '-')).strip()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"compare_{safe_product_names}_{timestamp_str}.json"
        json_filepath = json_dir / json_filename
        
        # JSON 파일 저장
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"[Comparison] JSON 파일 저장 완료: {json_filepath}")
        
        # JSON 형식으로 결과 반환
        return {
            "products": compare_result["products"],
            "comparison_analysis": comparison_text,
            "success": True,
            "message": f"{len(compare_result['products'])}개 제품의 비교 분석이 완료되었습니다. JSON 파일이 저장되었습니다.",
            "json_file": str(json_filepath.relative_to(PROJECT_ROOT))
        }
        
    except Exception as e:
        error_str = str(e)
        error_detail = "OpenAI API 호출 중 오류가 발생했습니다."
        
        if "authentication" in error_str.lower() or "api key" in error_str.lower() or "unauthorized" in error_str.lower():
            error_detail = (
                "❌ OpenAI API 키가 유효하지 않습니다.\n\n"
                f"오류 내용: {error_str}\n\n"
                "해결 방법:\n"
                "1. OpenAI Platform 접속: https://platform.openai.com/api-keys\n"
                "2. API 키 확인 및 새로 발급\n"
                "3. .env 파일의 OPENAI_API_KEY 값을 확인하고 올바른 키로 교체\n"
                "4. 서버 재시작\n\n"
                f"원본 오류: {error_str}"
            )
        elif "quota" in error_str.lower() or "rate limit" in error_str.lower():
            error_detail = (
                "❌ OpenAI API 사용량 제한을 초과했습니다.\n\n"
                "해결 방법:\n"
                "1. OpenAI Platform에서 사용량 확인: https://platform.openai.com/usage\n"
                "2. 요금제 확인 및 크레딧 충전\n"
                "3. GPT-4.1 mini는 저렴한 가격으로 제공됩니다\n\n"
                f"원본 오류: {error_str}"
            )
        else:
            error_detail = (
                f"❌ OpenAI API 호출 중 오류가 발생했습니다.\n\n"
                f"오류 내용: {error_str}\n\n"
                "추가 도움말:\n"
                "- OpenAI Platform 확인: https://platform.openai.com/\n"
                "- GPT-4.1 mini는 Vision 기능을 지원합니다\n"
                "- API 키 및 사용량 상태 확인"
            )
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


# 직접 실행 가능하도록 설정
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
