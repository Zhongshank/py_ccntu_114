"""LTN_FETCH_CHK_CRE.py

整合兩個用途：
1. 發送 GET 請求抓取自由時報熱門新聞頁面
2. 先確認回應是否可直接解析成 JSON；若不行，則改解析原始 HTML

最後會把前 5 筆熱門新聞寫入 JSON 檔，並在終端機印出結果。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
URL = "https://news.ltn.com.tw/list/breakingnews/popular"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
JSON_PATH = BASE_DIR / "ltn_tmp_check.json"
SOURCE_NAME = "自由時報"


def fetch_response(url: str) -> requests.Response:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response


def try_parse_json(response: requests.Response):
    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        return None
    try:
        return response.json()
    except ValueError:
        return None


def parse_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.whitecon.boxTitle ul.list")
    if container is None:
        return []

    items = []
    seen = set()

    for li in container.find_all("li", recursive=False):
        anchor = li.find("a", href=True)
        if anchor is None:
            continue

        href = urljoin(URL, anchor.get("href"))
        if href in seen:
            continue
        seen.add(href)

        title = anchor.get("title") or anchor.get("aria-label") or anchor.get_text(" ", strip=True)
        if not title:
            continue

        text = li.get_text(" ", strip=True)
        time_match = re.search(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", text)
        time_value = time_match.group(1) if time_match else None

        items.append(
            {
                "title": title,
                "href": href,
                "time": time_value,
                "SOURCE": SOURCE_NAME,
            }
        )

        if len(items) == 5:
            break

    return items


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    response = fetch_response(URL)
    direct_json = try_parse_json(response)

    if direct_json is not None:
        print("RESULT: JSON")
        print(json.dumps(direct_json, ensure_ascii=False, indent=2))
        save_json(JSON_PATH, direct_json)
        return

    print("RESULT: HTML")
    print("CONTENT-TYPE:", response.headers.get("content-type", ""))
    print("HTML HEAD:")
    print(response.text[:1000])

    records = parse_html(response.text)
    save_json(JSON_PATH, records)
    print("PARSED RECORDS:")
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()