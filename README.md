# 공개소프트웨어 11조 팀 프로젝트

이 저장소는 공개소프트웨어 11조의 팀 프로젝트를 관리하기 위한 공간입니다. 요구사항, 구현 코드, 산출물을 체계적으로 기록하고 협업 흐름을 유지하는 것을 목표로 합니다.

## 프로젝트 개요

### MCP 서버 - 제품 정보 수집 및 분석 시스템

**목표**: 사용자가 특정 제품의 구매 여부를 판단할 수 있도록 세부 정보를 빠르게 수집·가공해 주는 MCP 서버를 구현합니다.

### 주요 기능
1. **제품명 정규화**: 사용자 입력을 제조사 기준의 정식 모델명으로 변환
2. **이미지 크롤링**: 다나와 등 쇼핑몰에서 제품 상세 페이지 이미지 수집
3. **Base64 인코딩**: 크롤링한 이미지를 메모리에서 Base64로 인코딩하여 LLM이 접근 가능하도록 제공
4. **제품 비교**: 여러 제품을 동시에 정규화하고 이미지를 수집하여 차이점 위주로 비교 분석

### 시스템 흐름

#### 단일 제품 분석
1. 사용자가 원하는 제품을 LLM 인터페이스에 자연어로 입력합니다.
2. MCP 서버가 입력을 제조사 기준의 정식 모델명으로 정규화합니다.
3. 정규화된 모델명을 이용해 각 제조사·유통사의 상세 페이지 이미지를 크롤링합니다.
4. 이미지를 Base64로 인코딩하여 LLM에 전달합니다.
5. LLM이 수집된 이미지를 분석해 주요 스펙, 장단점, 추천 여부 등을 도출합니다.

#### 제품 비교 분석
1. 사용자가 비교하고 싶은 여러 제품을 LLM 인터페이스에 입력합니다.
2. MCP 서버가 각 제품을 정규화하고 이미지를 수집합니다.
3. 수집된 정보를 구조화하여 LLM에 전달합니다.
4. LLM이 제품 간 차이점(디자인, 특징, 가격대 등)을 중심으로 비교 분석합니다.

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

#### FastAPI 서버 의존성
```bash
cd fastapi
pip install -r requirements.txt
```

#### MCP 서버 의존성 (MCP 서버 사용 시)
```bash
# 루트 디렉터리에서
pip install mcp anyio
```

또는 모든 의존성을 한 번에 설치:
```bash
# 루트 디렉터리에서
pip install -r fastapi/requirements.txt
pip install mcp anyio
```

### 4. Playwright 브라우저 설치
```bash
playwright install chromium
```

**참고**: Playwright는 이미지 크롤링에 사용되며, 비동기 방식으로 동작합니다.

## 프로젝트 구조

```
SW_MCP_Project/
├── fastapi/                        # FastAPI 백엔드 서버
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 애플리케이션 및 REST API 엔드포인트
│   │   ├── normalize_product_name.py  # 제품명 정규화 로직 (다나와 검색)
│   │   ├── new_single_page_crawler.py # 이미지 크롤링 로직 (Playwright)
│   │   ├── compare_products.py     # 제품 비교 로직 (정규화 + 이미지 수집)
│   │   └── schemas.py              # Pydantic 스키마 정의
│   └── requirements.txt            # FastAPI 서버 의존성
├── mcp_server.py                   # MCP 서버 엔트리포인트 (Claude 연동)
├── mcp_config.json                  # MCP 서버 설정 파일 (Claude Desktop/Cursor용)
├── README.md                        # 프로젝트 문서
└── .gitignore                       # Git 무시 파일
```

### 주요 파일 설명

- **`fastapi/app/main.py`**: FastAPI REST API 서버. `/normalize-product-name`, `/crawl`, `/compare-products` 엔드포인트 제공
- **`fastapi/app/normalize_product_name.py`**: 다나와에서 제품명 검색 및 모델명/URL 추출
- **`fastapi/app/new_single_page_crawler.py`**: Playwright를 사용한 동적 페이지 크롤링 및 이미지 Base64 인코딩
- **`fastapi/app/compare_products.py`**: 여러 제품을 비교하기 위한 비즈니스 로직. 제품 정규화 및 이미지 수집을 통합 처리
- **`mcp_server.py`**: MCP 프로토콜을 통해 Claude와 통신하는 서버. FastAPI 로직을 MCP Tool로 노출
- **`mcp_config.json`**: Claude Desktop/Cursor에서 MCP 서버를 등록하기 위한 설정 파일 예시

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

MCP 서버를 사용하면 Claude Desktop 또는 Cursor에서 직접 제품 정보를 분석할 수 있습니다.

#### 설정 방법

1. **MCP 의존성 설치** (아직 설치하지 않았다면)
   ```bash
   pip install mcp anyio
   ```

2. **MCP 설정 파일에 서버 추가**

   **Claude Desktop의 경우:**
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`
   
   설정 파일에 다음 내용을 추가하세요:
   ```json
   {
     "mcpServers": {
       "product-analyzer": {
         "command": "python",
         "args": ["mcp_server.py"],
         "cwd": "C:\\Users\\home\\Desktop\\sw\\SW_MCP_Project",
         "env": {}
       }
     }
   }
   ```
   **주의**: `cwd` 경로를 실제 프로젝트 경로로 변경하세요.

   **Cursor의 경우:**
   - 설정에서 MCP 서버를 추가하거나
   - `mcp_config.json` 파일의 내용을 Cursor의 MCP 설정에 복사하세요.

3. **Claude Desktop/Cursor 재시작**
   - 설정 파일을 수정한 후 Claude Desktop 또는 Cursor를 재시작해야 합니다.

#### 제공되는 MCP Tools

MCP 서버는 다음 세 가지 Tool을 제공합니다:

1. **`normalize_product_name`**
   - 자연어 제품명을 제조사 모델명과 상품 URL로 정규화
   - 예: "삼성 블루스카이 5500" → 모델명 "AX060CG500G" + URL

2. **`crawl_product_images`**
   - 저장된 제품 URL에서 이미지를 최대 4장까지 크롤링
   - Base64로 인코딩하여 Claude에 전달
   - **주의**: 먼저 `normalize_product_name`을 호출해야 합니다.

3. **`compare_products`**
   - 두 개 이상의 제품명을 입력받아 각 제품을 정규화하고 이미지 수집
   - 차이점 위주로 비교 분석할 수 있도록 구조화된 데이터 제공
   - 디자인, 특징, 가격대 등의 차이점에 집중

#### 사용 예시

Claude에서 다음과 같이 사용할 수 있습니다:

```
"삼성 블루스카이 5500"과 "블루스카이 7000"을 비교해줘
```

또는 단일 제품 분석:

```
"삼성 블루스카이 5500" 제품에 대해 분석해줘
```

Claude가 자동으로 필요한 MCP Tool을 호출하여 제품 정보를 수집하고 분석합니다.

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

### 제품 비교 (`compare_products.py`, `/compare-products` 엔드포인트 및 `compare_products` MCP Tool)
- **모듈화된 구조**: `compare_products.py`에 비즈니스 로직을 분리하여 재사용성과 유지보수성 향상
- 두 개 이상의 제품명을 입력받아 각 제품을 자동으로 정규화
- 각 제품의 이미지를 수집하여 구조화된 형태로 반환
- **차이점 위주 비교**: LLM이 제품 디자인, 특징, 가격대 등의 차이점을 중심으로 비교 분석
- 비교 가이드 제공: 디자인, 특징, 가격대, 주요 차이점 등 비교 포인트 제시
- 일부 제품 처리 실패 시에도 다른 제품 처리는 계속 진행
- 에러 처리: 각 제품 처리 실패 시 상세한 오류 메시지 제공

## 환경 변수 설정

Claude와 연동 시 이미지 처리 옵션을 환경 변수로 조절할 수 있습니다:

- `LLM_IMAGE_MAX_COUNT`: 최대 이미지 개수 (기본값: 4)
- `LLM_IMAGE_MAX_BYTES`: 최대 이미지 크기 (바이트 단위)
- `LLM_IMAGE_MAX_DIMENSION`: 최대 이미지 차원 (픽셀 단위)

예시:
```bash
# Windows PowerShell
$env:LLM_IMAGE_MAX_COUNT=6
$env:LLM_IMAGE_MAX_BYTES=1048576

# Linux/Mac
export LLM_IMAGE_MAX_COUNT=6
export LLM_IMAGE_MAX_BYTES=1048576
```

## 주의사항

### 일반 주의사항
- **Windows 환경**: Playwright 실행 시 이벤트 루프 문제가 발생할 수 있어 별도 스레드에서 실행하도록 구현되어 있습니다.
- **이미지 저장**: 크롤링된 이미지는 메모리에서 Base64로 인코딩되어 반환되며, 파일로 저장되지 않습니다.
- **API 사용 순서**: 제품명은 먼저 `/normalize-product-name` 엔드포인트로 등록한 후 `/crawl` 엔드포인트를 사용해야 합니다.

### MCP 서버 사용 시 주의사항
- **경로 설정**: `mcp_config.json` 또는 Claude Desktop 설정 파일의 `cwd` 경로를 실제 프로젝트 경로로 정확히 설정해야 합니다.
- **Python 경로**: `command`가 "python"인 경우, 가상환경이 활성화된 상태에서 실행되도록 설정하거나 절대 경로를 사용하세요.
- **의존성**: MCP 서버 실행 전에 모든 의존성(특히 `mcp`, `anyio`, Playwright)이 설치되어 있어야 합니다.

### 문제 해결

#### 제품을 찾을 수 없는 경우
1. 제품명의 정확성을 확인하세요 (띄어쓰기, 숫자 등)
2. 제조사명 포함 여부를 확인하세요 (예: "삼성 전자 블루스카이 5500")
3. 다나와에서 직접 검색하여 정확한 제품명을 확인하세요

#### MCP 서버가 작동하지 않는 경우
1. Claude Desktop/Cursor를 재시작하세요
2. 설정 파일의 경로가 올바른지 확인하세요
3. Python 가상환경이 활성화되어 있는지 확인하세요
4. 모든 의존성이 설치되어 있는지 확인하세요 (`pip list`로 확인)

#### 크롤링 실패 시
1. 인터넷 연결을 확인하세요
2. Playwright 브라우저가 설치되어 있는지 확인하세요 (`playwright install chromium`)
3. 다나와 웹사이트 접근이 가능한지 확인하세요

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

