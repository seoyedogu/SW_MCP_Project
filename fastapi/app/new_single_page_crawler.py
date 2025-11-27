#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
single_page_image_crawler.py

단일 페이지에서 특정 영역([id^="partContents_"]) 안의 이미지를 모두 다운로드.
- Playwright 사용 (동적 로드 대응)
- src / data-src / srcset 자동 처리
- 이미지 없으면 자동 스킵

설치:
    pip install playwright requests
    playwright install

사용 방법:
    프로그램 <URL> <OUTDIR(path)>
사용 예:
    python single_page_image_crawler.py +"https://example.com/product/73614713" ./downloads
"""

import asyncio
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from playwright.async_api import async_playwright


DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


# 가상 브라우저의 해상도에 따른 view 차이를 고려해 가장 고화질 이미지를 불러오기 위한 함수
def choose_from_srcset(srcset: str) -> str:
    try:
        cands = []
        for part in srcset.split(","):
            part = part.strip()
            if " " in part:
                u, sz = part.rsplit(" ", 1)
                m = re.match(r"(\d+)(w|x)", sz)
                weight = int(m.group(1)) if m else 0
                cands.append((weight, u.strip()))
            else:
                cands.append((0, part))
        cands.sort(key=lambda t: t[0], reverse=True)
        return cands[0][1] if cands else ""
    except Exception:
        return ""

# 웹사이트에서 페이지 로딩 지연에 따라 저해상도 이미지를 먼저 로딩시킬때를 대비해 고해상도 이미지를 찾기 위한 함수
async def collect_images(page, container_sel="[id^='partContents_']", img_sel="img"):
    containers = await page.query_selector_all(container_sel)
    img_urls = []

    for c in containers:
        imgs = await c.query_selector_all(img_sel)
        for im in imgs:
            src = await im.get_attribute("src")
            if not src:
                data_src = await im.get_attribute("data-src")
                if data_src:
                    src = data_src
            if not src:
                srcset = await im.get_attribute("srcset")
                if srcset:
                    src = choose_from_srcset(srcset)
            if src:
                img_urls.append(urljoin(page.url, src))
    return img_urls


# 내부 크롤링 함수 (별도 이벤트 루프에서 실행)
async def _crawl_single_page_internal(url: str, outdir: str):
    """
    실제 크롤링 로직을 수행하는 내부 함수
    
    Args:
        url: 크롤링할 페이지 URL
        outdir: 이미지를 저장할 디렉토리 경로 (절대 경로)
    
    Raises:
        Exception: 크롤링 중 오류 발생 시
    """
    browser = None
    context = None
    page = None
    imgs = []
    
    try:
        # Playwright를 context manager로 사용하여 자동 정리 보장
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception as e:
                raise Exception(f"브라우저 실행 실패: {str(e)}")
            
            try:
                context = await browser.new_context(user_agent=DEFAULT_UA)
                page = await context.new_page()
            except Exception as e:
                raise Exception(f"브라우저 컨텍스트 생성 실패: {str(e)}")

            try:
                print(f"[open] {url}")
                # networkidle이 너무 엄격할 수 있으므로 domcontentloaded로 먼저 시도
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    # 페이지가 완전히 로드될 때까지 추가 대기
                    await page.wait_for_timeout(2000)
                except Exception:
                    # domcontentloaded 실패 시 load로 시도
                    await page.goto(url, wait_until="load", timeout=30000)
                    await page.wait_for_timeout(2000)
            except Exception as e:
                raise Exception(f"페이지 로딩 실패 (URL: {url}): {str(e)}")

            try:
                imgs = await collect_images(page)
                print(f"[found] {len(imgs)} images")
            except Exception as e:
                raise Exception(f"이미지 수집 실패: {str(e)}")

            # 이미지가 없는 경우에도 정상적으로 처리
            if len(imgs) == 0:
                print(f"[warning] 이미지를 찾을 수 없습니다. 선택자 '[id^=\"partContents_\"]' 내에 이미지가 없을 수 있습니다.")

            for idx, img_url in enumerate(imgs, start=1):
                try:
                    ext = (os.path.splitext(img_url)[1] or ".jpg").lower()
                    filename = f"result_{idx:03d}{ext}"
                    filepath = Path(outdir) / filename

                    headers = {"User-Agent": DEFAULT_UA, "Referer": url}
                    r = requests.get(img_url, headers=headers, timeout=15)
                    r.raise_for_status()
                    filepath.write_bytes(r.content)

                    print(f"  [saved] {filename}")
                except Exception as e:
                    print(f"  [ERROR] {img_url} - {e}")
                    # 개별 이미지 다운로드 실패는 계속 진행

            # 브라우저 정리 (context manager가 자동으로 정리하지만 명시적으로도 정리)
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

        print(f"[done] saved {len(imgs)} images to {outdir}")
        
    except Exception as e:
        # 추가 정리 작업
        if page:
            try:
                await page.close()
            except Exception:
                pass
        if context:
            try:
                await context.close()
            except Exception:
                pass
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        # 예외를 다시 발생시켜서 상위에서 처리하도록
        raise


#실질적인 크롤링 함수 (Windows 이벤트 루프 문제 해결)
async def crawl_single_page(url: str, outdir: str):
    """
    단일 페이지에서 이미지를 크롤링하는 함수
    Windows에서 이벤트 루프 문제를 해결하기 위해 별도 스레드에서 실행
    
    Args:
        url: 크롤링할 페이지 URL
        outdir: 이미지를 저장할 디렉토리 경로
    
    Raises:
        Exception: 크롤링 중 오류 발생 시
    """
    try:
        # 절대 경로로 변환하여 경로 문제 방지
        outdir_path = Path(outdir).resolve()
        outdir_path.mkdir(parents=True, exist_ok=True)
        outdir = str(outdir_path)
    except Exception as e:
        raise Exception(f"디렉토리 생성 실패: {outdir} - {str(e)}")

    # Windows에서 이벤트 루프 문제 해결: 별도 스레드에서 새 이벤트 루프 생성
    if sys.platform == "win32":
        import concurrent.futures
        
        def run_in_new_loop():
            """새 이벤트 루프에서 크롤링 실행"""
            # Windows에서는 ProactorEventLoop를 명시적으로 사용
            if sys.version_info >= (3, 8):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            else:
                loop = asyncio.new_event_loop()
            
            try:
                loop.run_until_complete(_crawl_single_page_internal(url, outdir))
            except Exception as e:
                # 예외를 다시 발생시켜서 상위로 전파
                raise
            finally:
                try:
                    # 남은 작업 완료
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                finally:
                    loop.close()
        
        # 별도 스레드에서 실행
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_loop)
            future.result()  # 결과 대기 (예외도 전파됨)
    else:
        # Windows가 아닌 경우 현재 이벤트 루프에서 실행
        await _crawl_single_page_internal(url, outdir)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        #프로그램은 인자로 url과 함께 호출되어야 함
        print("잘못된 호출입니다.")
        sys.exit(1)

    url = sys.argv[1]
    outdir = sys.argv[2]

    asyncio.run(crawl_single_page(url, outdir))
