#!/usr/bin/env python3
"""Discover the current TCIA access links for the M6 challenge substrate.

This is a metadata-only network diagnostic. It fetches public HTML pages, records
response provenance and links, and does not download DICOM or run any experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ANALYSIS_PAGE = "https://www.cancerimagingarchive.net/analysis-result/isbi-mr-prostate-2013/"
DOWNLOAD_PATH_MARKER = "/tcia-downloads/isbi-mr-prostate-2013-da-other/"
USER_AGENT = "truemargin-research/0.1"
TIMEOUT_SECONDS = 45


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        values = dict(attrs)
        href = values.get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        self.links.append({"href": self._href, "text": " ".join("".join(self._text).split())})
        self._href = None
        self._text = []


def fetch_page(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = response.read()
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            status = int(getattr(response, "status", 200))
    except urllib.error.HTTPError as exc:
        body = exc.read(1024)
        return {
            "requested_url": url,
            "status": "http_error",
            "http_status": exc.code,
            "reason": str(exc.reason),
            "response_excerpt": body.decode("utf-8", errors="replace"),
        }
    except urllib.error.URLError as exc:
        return {
            "requested_url": url,
            "status": "url_error",
            "reason": str(exc.reason),
        }

    record: dict[str, Any] = {
        "requested_url": url,
        "final_url": final_url,
        "status": "ok",
        "http_status": status,
        "content_type": content_type,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    if "html" in content_type.lower() or payload.lstrip().startswith(b"<"):
        text = payload.decode("utf-8", errors="replace")
        parser = LinkParser()
        parser.feed(text)
        record["links"] = [
            {
                "href": urllib.parse.urljoin(final_url, link["href"]),
                "text": link["text"],
            }
            for link in parser.links
        ]
    return record


def build_discovery() -> dict[str, Any]:
    analysis = fetch_page(ANALYSIS_PAGE)
    links = analysis.get("links", [])
    landing_urls = sorted(
        {
            str(link["href"])
            for link in links
            if DOWNLOAD_PATH_MARKER in str(link.get("href", ""))
        }
    )
    landings = [fetch_page(url) for url in landing_urls]
    candidate_assets: list[dict[str, str]] = []
    for page in landings:
        for link in page.get("links", []):
            href = str(link.get("href", ""))
            lowered = href.lower().split("?", 1)[0]
            if lowered.endswith((".tcia", ".zip", ".nrrd")):
                candidate_assets.append({"href": href, "text": str(link.get("text", ""))})

    return {
        "schema_version": 1,
        "milestone": "M6",
        "diagnostic": "tcia-current-access-discovery",
        "result_bearing_authorized": False,
        "analysis_page": analysis,
        "download_landing_urls": landing_urls,
        "download_landings": landings,
        "candidate_assets": sorted(candidate_assets, key=lambda item: item["href"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/m6_tcia_access_discovery.json"),
    )
    args = parser.parse_args()
    result = build_discovery()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
