import logging
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

# 제품명 -> 모델명 및 URL 매핑 저장용 변수 (메모리에 저장)
# 구조: {"제품명": {"model": "모델명", "url": "URL"}}
product_name_to_model: dict[str, dict[str, str]] = {}


def normalize_search_keyword(product_name: str) -> list[str]:
    """
    검색 키워드를 정규화하여 여러 변형을 생성하는 함수
    
    Args:
        product_name: 원본 제품 이름
    
    Returns:
        검색을 시도할 키워드 리스트 (우선순위 순)
    """
    import re
    
    keywords = [product_name]  # 원본을 먼저 시도
    
    # 삼성 관련 정규화
    # "삼성"으로 시작하고 "전자"가 없는 경우
    if re.match(r'^삼성\s*', product_name) and "전자" not in product_name:
        # "삼성" 뒤의 내용 추출
        match = re.match(r'^삼성\s*(.+)', product_name)
        if match:
            rest = match.group(1)
            normalized_name = f"삼성 전자 {rest}".strip()
            if normalized_name != product_name:
                keywords.append(normalized_name)
    # "삼성전자"가 붙어있는 경우 "삼성 전자"로 변경
    elif "삼성전자" in product_name and "삼성 전자" not in product_name:
        normalized_name = product_name.replace("삼성전자", "삼성 전자")
        if normalized_name != product_name:
            keywords.append(normalized_name)
    
    # LG 관련 정규화
    if re.match(r'^(LG|lg|엘지)\s*', product_name, re.IGNORECASE) and "전자" not in product_name:
        match = re.match(r'^(LG|lg|엘지)\s*(.+)', product_name, re.IGNORECASE)
        if match:
            rest = match.group(2)
            normalized_name = f"LG전자 {rest}".strip()
            if normalized_name != product_name:
                keywords.append(normalized_name)
    
    # 중복 제거 및 원본 순서 유지
    seen = set()
    result = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            result.append(keyword)
    
    return result


def _extract_model_from_detail_html(html: str) -> str | None:
    """스펙 테이블/요약 문구에서 모델명을 추출."""
    soup = BeautifulSoup(html, "html.parser")

    # 테이블 기반 추출
    for selector in [
        "table.spec_tbl tr",
        ".spec_tbl tr",
        ".prod_spec tr",
    ]:
        for row in soup.select(selector):
            header = row.find("th")
            value = row.find("td")
            if not header or not value:
                continue
            label = header.get_text(strip=True).lower()
            if any(keyword in label for keyword in ["모델명", "제품모델명", "model", "model name"]):
                text = value.get_text(strip=True)
                if text:
                    return text

    # 제목/요약에서 패턴 검색
    candidates = []
    for selector in [
        "h3.prod_tit",
        "h1.prod_tit",
        ".prod_tit",
        ".prod_summary_info",
        ".product_info",
    ]:
        element = soup.select_one(selector)
        if element:
            candidates.append(element.get_text(" ", strip=True))

    pattern = r"\b[A-Z]{2,}[0-9A-Z]{4,}\b"
    for text in candidates:
        match = re.search(pattern, text or "")
        if match:
            return match.group(0)

    return None


def _search_with_requests(search_url: str, user_agent: str) -> dict[str, str] | None:
    """Playwright 실패 시 requests/BeautifulSoup 기반 크롤링."""
    headers = {"User-Agent": user_agent, "Referer": "https://search.danawa.com/"}
    resp = requests.get(search_url, headers=headers, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    product = soup.select_one(".product_list .prod_item")
    if not product:
        logging.warning("[normalize-fallback] product list empty")
        return None

    link = product.select_one(".prod_name a, a[class^='click_log_product_standard_title_']")
    if not link or not link.get("href"):
        logging.warning("[normalize-fallback] product link missing")
        return None

    product_url = link.get("href")
    if product_url.startswith("/info"):
        product_url = urljoin("http://prod.danawa.com", product_url)

    detail_resp = requests.get(product_url, headers=headers, timeout=10)
    detail_resp.raise_for_status()
    model_name = _extract_model_from_detail_html(detail_resp.text)

    if model_name:
        logging.info(
            "[normalize-fallback] extracted model=%s url=%s",
            model_name,
            product_url,
        )
        return {"model": model_name, "url": product_url}

    logging.warning("[normalize-fallback] unable to find model text")
    return None


def search_danawa_and_extract_model(search_keyword: str) -> dict[str, str] | None:
    """
    다나와에서 검색하여 모델명과 URL을 추출하는 함수
    
    Args:
        search_keyword: 검색 키워드
    
    Returns:
        {"model": "모델명", "url": "URL"} 또는 None
    """
    import urllib.parse

    encoded_keyword = urllib.parse.quote(search_keyword)
    search_url = f"https://search.danawa.com/dsearch.php?query={encoded_keyword}&tab=main"

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    playwright_result: dict[str, str] | None = None
    try:
        with sync_playwright() as playwright:
            browser = None
            context = None
            try:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(user_agent=user_agent)
                page = context.new_page()

                logging.info("[normalize] search_url=%s keyword=%s", search_url, search_keyword)

                page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
                page.wait_for_selector(".product_list .prod_item", timeout=5000)

                product_locator = page.locator(".product_list .prod_item").first
                if product_locator.count() == 0:
                    logging.warning("[normalize] no product items found")
                else:
                    product_link_locator = product_locator.locator(
                        ".prod_name a, a[class^='click_log_product_standard_title_']"
                    ).first
                    if product_link_locator.count() == 0:
                        logging.warning("[normalize] product link not found")
                    else:
                        product_url = product_link_locator.get_attribute("href")
                        if not product_url:
                            logging.warning("[normalize] product link has no href")
                        else:
                            if product_url.startswith("/info"):
                                product_url = "http://prod.danawa.com" + product_url

                            page.goto(product_url, timeout=15000, wait_until="domcontentloaded")

                            model_name = None
                            spec_rows = page.locator("table.spec_tbl tr, .spec_tbl tr, .prod_spec tr")
                            for index in range(spec_rows.count()):
                                row = spec_rows.nth(index)
                                th = row.locator("th").first
                                td = row.locator("td").first

                                if th.count() == 0 or td.count() == 0:
                                    continue

                                try:
                                    label = th.inner_text(timeout=2000).strip().lower()
                                    value = td.inner_text(timeout=2000).strip()
                                except PlaywrightTimeoutError:
                                    continue

                                if any(keyword in label for keyword in ["모델명", "제품모델명", "model", "model name"]):
                                    model_name = value
                                    break

                            if not model_name:
                                product_title_locator = page.locator("h3.prod_tit, h1.prod_tit, .prod_tit").first
                                if product_title_locator.count() > 0:
                                    try:
                                        title_text = product_title_locator.inner_text(timeout=2000)
                                    except PlaywrightTimeoutError:
                                        title_text = ""
                                    matches = re.findall(r"\b[A-Z]{2,}[0-9A-Z]{4,}\b", title_text)
                                    if matches:
                                        model_name = matches[0]

                            if not model_name:
                                detail_info_locator = page.locator(".prod_summary_info, .product_info").first
                                if detail_info_locator.count() > 0:
                                    try:
                                        info_text = detail_info_locator.inner_text(timeout=2000)
                                    except PlaywrightTimeoutError:
                                        info_text = ""
                                    matches = re.findall(r"\b[A-Z]{2,}[0-9A-Z]{4,}\b", info_text)
                                    if matches:
                                        model_name = matches[0]

                            if model_name:
                                logging.info("[normalize] extracted model=%s url=%s", model_name, product_url)
                                playwright_result = {"model": model_name, "url": product_url}
                            else:
                                logging.warning("[normalize] model name not found in detail page")
            finally:
                if context is not None:
                    try:
                        context.close()
                    except Exception as exc:
                        logging.warning("[normalize] context close failed: %s", exc)
                if browser is not None:
                    try:
                        browser.close()
                    except Exception as exc:
                        logging.warning("[normalize] browser close failed: %s", exc)
    except PlaywrightTimeoutError as exc:
        logging.error("[normalize] Playwright timeout: %s", exc)
    except Exception as exc:
        logging.error("[normalize] unexpected error: %s", exc, exc_info=True)

    if playwright_result:
        return playwright_result

    logging.info("[normalize] falling back to requests parser")
    try:
        return _search_with_requests(search_url, user_agent)
    except Exception as exc:  # noqa: BLE001
        logging.error("[normalize-fallback] request parsing failed: %s", exc, exc_info=True)
        return None


def convert_product_name_to_model(product_name: str) -> dict[str, str] | None:
    """
    제품 이름을 모델명과 URL로 변환하는 함수 (다나와에서 자동 검색)
    
    다나와에서 제품명으로 검색하여 첫 번째 결과의 모델명과 URL을 추출합니다.
    이미 저장된 매핑이 있으면 그것을 우선적으로 사용합니다.
    검색 결과가 없을 경우 키워드 변형을 시도합니다.
    
    Args:
        product_name: 제품 이름 (예: "삼성 블루스카이 5500")
    
    Returns:
        {"model": "모델명", "url": "URL"} (예: {"model": "AX060CG500G", "url": "http://..."}) 또는 None
    """
    # 먼저 저장된 매핑에서 확인 (캐시된 결과 우선 사용)
    if product_name in product_name_to_model:
        return product_name_to_model[product_name]
    
    # 대소문자 무시로 저장된 매핑 확인
    for key, value in product_name_to_model.items():
        if key.lower() == product_name.lower():
            return value
    
    # 검색 키워드 변형 생성
    search_keywords = normalize_search_keyword(product_name)
    
    # 각 키워드로 검색 시도
    for keyword in search_keywords:
        result = search_danawa_and_extract_model(keyword)
        if result:
            return result
    
    # 모든 키워드로 검색해도 실패한 경우
    return None

