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


#실질적인 크롤링 함수
async def crawl_single_page(url: str, outdir: str):
    Path(outdir).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=DEFAULT_UA)
        page = await context.new_page()

        print(f"[open] {url}")
        await page.goto(url, wait_until="networkidle", timeout=20000)

        imgs = await collect_images(page)
        print(f"[found] {len(imgs)} images")

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

        await context.close()
        await browser.close()

    print(f"[done] saved {len(imgs)} images to {outdir}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        #프로그램은 인자로 url과 함께 호출되어야 함
        print("잘못된 호출입니다.")
        sys.exit(1)

    url = sys.argv[1]
    outdir = sys.argv[2]

    asyncio.run(crawl_single_page(url, outdir))
