# 공개소프트웨어 11조 팀 프로젝트

이 저장소는 공개소프트웨어 11조의 팀 프로젝트를 관리하기 위한 공간입니다. 요구사항, 구현 코드, 산출물을 체계적으로 기록하고 협업 흐름을 유지하는 것을 목표로 합니다.

## 프로젝트 개요

### MCP 서버 - 제품 정보 수집 및 분석 시스템

**목표**: 사용자가 특정 제품의 구매 여부를 판단할 수 있도록 세부 정보를 빠르게 수집·가공해 주는 MCP 서버를 구현합니다.

### 주요 기능
1. **제품명 정규화**: 사용자 입력을 제조사 기준의 정식 모델명으로 변환
2. **이미지 크롤링**: 다나와 등 쇼핑몰에서 제품 상세 페이지 이미지 수집
3. **Base64 인코딩**: 크롤링한 이미지를 메모리에서 Base64로 인코딩하여 LLM이 접근 가능하도록 제공

### 시스템 흐름
1. 사용자가 원하는 제품을 LLM 인터페이스에 자연어로 입력합니다.
2. MCP 서버가 입력을 제조사 기준의 정식 모델명으로 정규화합니다.
3. 정규화된 모델명을 이용해 각 제조사·유통사의 상세 페이지 이미지를 크롤링합니다.
4. 이미지를 Base64로 인코딩하여 LLM에 전달합니다.
5. LLM이 수집된 이미지를 분석해 주요 스펙, 장단점, 추천 여부 등을 도출합니다.

### 역할 분담
- **MCP 서버**: 정규화·크롤링·데이터 가공까지의 파이프라인을 담당
- **프런트/클라이언트**: 결과를 시각화해 사용자의 의사결정을 돕습니다.

## 기술 스택

- **Backend**: FastAPI
- **MCP Server**: fastmcp (Anthropic Claude MCP 프로토콜)
- **Web Scraping**: Playwright (비동기)
- **Data Processing**: Python 3.x
- **API**: RESTful API

## 설치 방법

### 1. 저장소 클론
```bash
git clone <repository-url>
cd SW_MCP_Project
```

### 2. Python 가상환경 생성 및 활성화
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 의존성 설치
```bash
cd fastapi
pip install -r requirements.txt
```

### 4. MCP 서버 의존성 설치 (MCP 서버 사용 시)
```bash
# 루트 디렉터리에서
pip install mcp anyio
```

### 5. Playwright 브라우저 설치
```bash
playwright install chromium
```

## 프로젝트 구조

```
SW_MCP_Project/
├── fastapi/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 애플리케이션 및 엔드포인트
│   │   ├── normalize_product_name.py  # 제품명 정규화 로직
│   │   ├── new_single_page_crawler.py # 이미지 크롤링 로직
│   │   └── schemas.py              # Pydantic 스키마 정의
│   └── requirements.txt
├── mcp_server.py                   # MCP 서버 엔트리포인트
├── mcp_config.json                  # MCP 서버 설정 파일
├── README.md
└── .gitignore
```

## API 엔드포인트

### 1. 제품명 정규화
**POST** `/normalize-product-name`

제품명을 모델명과 URL로 변환하여 저장합니다.

**Request:**
```json
{
  "product_name": "삼성 블루스카이 5500"
}
```

**Response:**
```json
{
  "product_name": "삼성 블루스카이 5500",
  "model_name": "AX060CG500G",
  "url": "http://prod.danawa.com/info/...",
  "saved": true,
  "message": "제품명 '삼성 블루스카이 5500'이 모델명 'AX060CG500G'과 URL로 저장되었습니다."
}
```

### 2. 이미지 크롤링
**POST** `/crawl`

저장된 제품 URL을 사용하여 이미지를 크롤링하고 Base64로 인코딩합니다.

**Request:**
```json
{
  "product_name": "삼성 블루스카이 5500"
}
```

**Response:**
```json
{
  "product_name": "삼성 블루스카이 5500",
  "url": "http://prod.danawa.com/info/...",
  "image_count": 2,
  "images": [
    {
      "url": "https://...",
      "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
      "mime_type": "image/jpeg",
      "index": 1,
      "original_size_bytes": 245760,
      "optimized_size_bytes": 89234
    },
    {
      "url": "https://...",
      "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
      "mime_type": "image/png",
      "index": 2,
      "original_size_bytes": 189234,
      "optimized_size_bytes": 87654
    }
  ],
  "success": true,
  "message": "제품 '삼성 블루스카이 5500'의 이미지 2개를 성공적으로 크롤링하고 base64로 인코딩했습니다."
}
```

### 3. 제품 비교
**POST** `/compare-products`

두 개 이상의 제품명을 입력받아 각 제품을 정규화하고 이미지를 수집하여 비교 가능한 형태로 반환합니다.

**Request:**
```json
{
  "product_names": ["삼성 블루스카이 5500", "블루스카이 7000"]
}
```

**Response:**
```json
{
  "products": [
    {
      "product_name": "삼성 블루스카이 5500",
      "model_name": "AX060CG500G",
      "url": "http://prod.danawa.com/info/...",
      "image_count": 2,
      "images": [
        {
          "url": "https://...",
          "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
          "mime_type": "image/jpeg",
          "index": 1,
          "original_size_bytes": 245760,
          "optimized_size_bytes": 89234
        }
      ]
    },
    {
      "product_name": "블루스카이 7000",
      "model_name": "AX060CG700G",
      "url": "http://prod.danawa.com/info/...",
      "image_count": 3,
      "images": [...]
    }
  ],
  "total_products": 2,
  "success": true,
  "message": "2개 제품의 정보를 수집했습니다.\n\n[비교 가이드]\n수집된 제품 정보를 바탕으로 다음 항목을 중심으로 차이점을 비교해주세요:\n1. 제품 디자인: 색상, 형태, 크기 등의 차이\n2. 제품 특징: 기능, 성능, 사양 등의 차이\n3. 가격대: 다나와 링크를 통해 최신 가격 확인 가능\n4. 주요 차이점: 각 제품의 고유한 특징과 장단점\n\n공통점보다는 차이점에 집중하여 비교 설명해주세요.",
  "comparison_hint": {
    "focus": "차이점",
    "comparison_points": [
      "제품 디자인 (색상, 형태, 크기)",
      "제품 특징 (기능, 성능, 사양)",
      "가격대",
      "주요 차이점 및 고유 특징"
    ],
    "note": "공통점보다는 차이점에 집중하여 비교해주세요."
  }
}
```

## 사용 방법

### 1. 서버 실행
```bash
cd fastapi
python -m app.main
# 또는
uvicorn app.main:app --reload
```

서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

### 1-1. MCP 서버(Claude 연동) 실행
1. 루트 디렉터리에서 MCP 의존성을 설치합니다.
   ```bash
   pip install mcp anyio
   ```
2. `mcp_config.json` 파일의 내용을 Claude Desktop 또는 Cursor의 MCP 설정 파일에 추가합니다.
   - Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json` (Windows) 또는 `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac)
   - Cursor: 설정에서 MCP 서버 추가
3. MCP 서버는 STDIO 기반으로 자동 실행되며, `product-analyzer` 서버가 다음 세 가지 Tool을 제공합니다:
   - `normalize_product_name`: 자연어 제품명을 제조사 모델명과 상품 URL로 정규화
   - `crawl_product_images`: 저장된 제품 URL에서 이미지를 최대 4장까지 크롤링하여 Base64로 인코딩
   - `compare_products`: 두 개 이상의 제품명을 입력받아 각 제품을 정규화하고 이미지를 수집하여 비교 가능한 형태로 반환 (공통점/차이점 분석을 위해 구조화된 데이터 제공)
4. Claude에서의 실행 순서는 README 상단의 흐름(사용자 입력 → 모델명 정규화 → 이미지 크롤링 → Base64 전달 → LLM 분석)을 그대로 따르면 됩니다.

### 2. API 문서 확인
브라우저에서 `http://localhost:8000/docs` 접속하여 Swagger UI에서 API를 테스트할 수 있습니다.

## 주요 기능 설명

### 제품명 정규화 (`normalize_product_name.py`)
- 다나와에서 제품명으로 검색
- 첫 번째 결과의 모델명 추출
- 제품명 변형 자동 처리 (예: "삼성 블루스카이" → "삼성 전자 블루스카이", "LG" → "LG전자")
- Playwright 실패 시 requests/BeautifulSoup 기반 폴백 처리
- 모델명과 URL을 메모리에 저장

### 이미지 크롤링 (`new_single_page_crawler.py`)
- Playwright를 사용한 동적 페이지 크롤링
- `[id^="partContents_"]` 선택자 내의 이미지 수집
- 이미지를 Base64로 인코딩하여 반환
- Claude 한도(이미지 1MB) 대응을 위해 최대 4장만 추출하고 Pillow로 자동 리사이즈/재압축
- 원본 및 최적화된 이미지 크기 정보 제공 (`original_size_bytes`, `optimized_size_bytes`)
- Windows 이벤트 루프 문제 해결 (별도 스레드에서 실행)

### 제품 비교 (`/compare-products` 엔드포인트 및 `compare_products` MCP Tool)
- 두 개 이상의 제품명을 입력받아 각 제품을 자동으로 정규화
- 각 제품의 이미지를 수집하여 구조화된 형태로 반환
- **차이점 위주 비교**: LLM이 제품 디자인, 특징, 가격대 등의 차이점을 중심으로 비교 분석
- 비교 가이드 제공: 디자인, 특징, 가격대, 주요 차이점 등 비교 포인트 제시
- 일부 제품 처리 실패 시에도 다른 제품 처리는 계속 진행

## 주의사항

- Windows 환경에서는 Playwright 실행 시 이벤트 루프 문제가 발생할 수 있어 별도 스레드에서 실행하도록 구현되어 있습니다.
- 크롤링된 이미지는 메모리에서 Base64로 인코딩되어 반환되며, 파일로 저장되지 않습니다.
- Claude와 연동 시 `LLM_IMAGE_MAX_COUNT`, `LLM_IMAGE_MAX_BYTES`, `LLM_IMAGE_MAX_DIMENSION` 환경변수로 이미지 개수‧용량을 상황에 맞게 조절할 수 있습니다.
- 제품명은 먼저 `/normalize-product-name` 엔드포인트로 등록한 후 `/crawl` 엔드포인트를 사용해야 합니다.

## 커밋 규칙
- `feat: ...` 새로운 기능 추가
- `fix: ...` 버그 수정
- `docs: ...` 문서 혹은 주석 업데이트
- `refactor: ...` 기능 변화 없이 코드 구조 개선
- `test: ...` 테스트 코드 추가 및 수정
- `chore: ...` 빌드, 설정, 의존성 등 기타 작업

### 공통 원칙
- 한 커밋에는 한 가지 목적만 담습니다.
- 커밋 메시지는 한국어 혹은 영어 중 하나로 일관성을 유지합니다.
- 이슈 번호가 있다면 `feat: #12 사용자 인증 추가`처럼 메시지에 포함합니다.
- PR 전에는 `git status`, `git diff`로 변경 내역을 반드시 확인합니다.
