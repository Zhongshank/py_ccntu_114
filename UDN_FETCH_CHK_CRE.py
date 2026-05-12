"""UDN_FETCH_CHK_CRE.py

整合三個用途：
1. 發送 GET 請求抓取聯合報熱門新聞頁面
2. 解析原始 HTML，整理成 JSON 資料
3. 將新增新聞寫入新的 JSON 檔，並在 Untitled-1.tx 末尾新增一個 section
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
URL = "https://udn.com/rank/pv/2"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
JSON_PATH = BASE_DIR / "tmp_check_5.json"
TEX_PATH = BASE_DIR / "Untitled-1.tex"
SOURCE_NAME = "聯合報"


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


def parse_rank_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    items = []

    for anchor in soup.find_all("a", href=lambda href: href and "/news/story/" in href):
        href = urljoin(URL, anchor.get("href"))
        if href in seen:
            continue
        seen.add(href)

        container = anchor
        for _ in range(4):
            if container.parent:
                container = container.parent

        eye_el = container.select_one("i.i-eye-3")
        if eye_el is None:
            continue

        time_el = container.select_one(".story-list__time")
        title = anchor.get("aria-label") or anchor.get("title") or anchor.get_text(" ", strip=True)
        views = None
        eye_parent = eye_el.parent
        if eye_parent is not None:
            match = re.search(r"(\d[\d,]*)", eye_parent.get_text(" ", strip=True))
            if match:
                views = match.group(1)

        items.append(
            {
                "title": title,
                "href": href,
                "time": time_el.get_text(" ", strip=True) if time_el else None,
                "SOURCE": SOURCE_NAME,
                "views": views,
            }
        )

    return items


def load_existing_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []


def save_json(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_tex_section(path: Path, section_title: str, records: list[dict]) -> None:
    if not path.exists():
        return

    new_section_lines = [
        f"\\section*{{\\textcolor{{red}}{{{section_title}}}}}",
        "",
        "以下內容為依序整理出的五筆新增新聞資料，並加入非原始 HTML 的 \\textbf{SOURCE} 欄位：",
        "",
        "\\begin{verbatim}",
        json.dumps(records, ensure_ascii=False, indent=2),
        "\\end{verbatim}",
        "",
        "",
    ]

    original = path.read_text(encoding="utf-8")
    marker = "\\end{CJK*}"
    if marker not in original:
        return

    updated = original.replace(marker, "\n".join(new_section_lines) + marker, 1)
    path.write_text(updated, encoding="utf-8")


def main() -> None:
    html = fetch_html(URL)
    all_items = parse_rank_page(html)

    existing = load_existing_json(JSON_PATH)
    existing_hrefs = {item.get("href") for item in existing}

    new_items = []
    for item in all_items:
        if item.get("href") in existing_hrefs:
            continue
        new_items.append(item)
        if len(new_items) == 5:
            break

    if not new_items:
        print("No new items to append.")
        return

    combined = existing + new_items
    save_json(JSON_PATH, combined)
    append_tex_section(TEX_PATH, "聯合報熱門新聞五筆 JSON", new_items)

    print(json.dumps(new_items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
