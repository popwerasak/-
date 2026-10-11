"""MCP server for searching research articles on ThaiJO (https://www.tci-thaijo.org).

Wraps the public JSON API used by the ThaiJO website (/api/v1/...).
"""

from __future__ import annotations

import json
from typing import Any, Literal

import httpx
from mcp.server.mcpserver import MCPServer

BASE_URL = "https://www.tci-thaijo.org/api/v1"
MAX_PER_PAGE = 50  # server caps per_page at 50
MAX_QUERY_LENGTH = 255

mcp = MCPServer("thaijo")
_client = httpx.Client(
    base_url=BASE_URL,
    timeout=30,
    headers={"User-Agent": "thaijo-mcp/0.1 (+https://github.com/popwerasak/-)"},
)

SearchField = Literal["title", "abstract", "author", "keyword", "journal_name", "doi"]


def _request(method: str, path: str, body: dict | None = None) -> Any:
    resp = _client.request(method, path, json=body)
    if resp.status_code >= 400:
        try:
            err = resp.json().get("error", resp.text)
        except ValueError:
            err = resp.text
        raise RuntimeError(f"ThaiJO API error {resp.status_code}: {err}")
    return resp.json()


def _clean(body: dict) -> dict:
    return {k: v for k, v in body.items() if v not in (None, "", [])}


def _bilingual(value: dict | None) -> dict | None:
    if not value:
        return None
    return {"th": value.get("th_TH"), "en": value.get("en_US")}


def _article_summary(hit: dict) -> dict:
    return {
        "id": hit.get("id"),
        "title": _bilingual(hit.get("titles")),
        "authors": _bilingual(hit.get("authors")),
        "journal": _bilingual(hit.get("journal_name")),
        "journal_path": hit.get("journal_path"),
        "year": hit.get("year"),
        "date_published": hit.get("date_published"),
        "keywords": _bilingual(hit.get("keywords")),
        "doi": hit.get("doi"),
        "url": hit.get("article_url"),
    }


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1)


@mcp.tool()
def search_articles(
    query: str = "",
    page: int = 1,
    per_page: int = 20,
    search_fields: list[SearchField] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    language: Literal["th_TH", "en_US"] | None = None,
    journal_path: str | None = None,
    categories: list[str] | None = None,
    sort: Literal["date_desc", "date_asc", "year_desc", "year_asc"] | None = None,
    match: Literal["last", "all", "frequency"] = "last",
    exact: bool = False,
    include_facets: bool = False,
) -> str:
    """Search all research articles indexed on ThaiJO (Thai Journals Online, 400k+ articles).

    Args:
        query: Search terms in Thai or English (max 255 chars). Empty string lists everything.
        page: Page number, starting at 1.
        per_page: Results per page (1-50).
        search_fields: Restrict matching to these fields; default searches all fields.
        year_from: Earliest publication year (Gregorian, e.g. 2020).
        year_to: Latest publication year (Gregorian).
        language: Only articles available in this language.
        journal_path: Only articles from one journal (its "path", e.g. "cmunursing";
            find it with search_journals).
        categories: Subject category codes such as "health01" or "social06"
            (see list_subject_groups).
        sort: Sort order; default is relevance.
        match: "all" requires every word, "last" drops trailing words if needed
            (default), "frequency" drops the most common words first.
        exact: Match the query as an exact phrase.
        include_facets: Also return counts per category and journal_id.
    """
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"query must be at most {MAX_QUERY_LENGTH} characters")
    body = _clean(
        {
            "q": query.strip(),
            "page": max(page, 1),
            "per_page": min(max(per_page, 1), MAX_PER_PAGE),
            "highlight": False,
            "facets": include_facets,
            "search_field": ",".join(search_fields) if search_fields else None,
            "year_from": year_from,
            "year_to": year_to,
            "language": language,
            "journal_path": journal_path,
            "categories": ",".join(categories) if categories else None,
            "sort": sort,
            "matching_strategy": None if match == "last" else match,
            "exact": exact or None,
        }
    )
    data = _request("POST", "/articles/search", body)
    total = data.get("total", 0)
    result = {
        "total": total,
        "page": data.get("page"),
        "per_page": data.get("per_page"),
        "total_pages": -(-total // body["per_page"]),
        "articles": [_article_summary(h) for h in data.get("hits", [])],
    }
    if include_facets:
        result["facets"] = data.get("facets")
    return _dump(result)


@mcp.tool()
def get_article(article_id: str) -> str:
    """Get full details of one article: abstract, authors, keywords, pages, DOI and PDF link.

    Args:
        article_id: The article "id" returned by search_articles, e.g. "health02-276115".
    """
    data = _request("GET", f"/articles/{article_id}")
    result = _article_summary(data)
    result.update(
        {
            "abstract": _bilingual(data.get("abstracts")),
            "pages": data.get("pages"),
            "pdf_url": data.get("pdf_url"),
            "issue_url": data.get("issue_url"),
            "journal_url": data.get("journal_url"),
            "category": data.get("category"),
        }
    )
    return _dump(result)


@mcp.tool()
def search_journals(query: str = "", page: int = 1, per_page: int = 20) -> str:
    """Search journals on ThaiJO by name. Returns each journal's path (usable as
    journal_path in search_articles), ISSN, TCI tier and URL.

    Args:
        query: Journal name terms in Thai or English. Empty string lists all journals.
        page: Page number, starting at 1.
        per_page: Results per page (1-50).
    """
    body = _clean(
        {
            "q": query.strip(),
            "page": max(page, 1),
            "per_page": min(max(per_page, 1), MAX_PER_PAGE),
        }
    )
    data = _request("POST", "/journals/search", body)
    journals = [
        {
            "id": j.get("id"),
            "name": _bilingual(j.get("names")),
            "path": j.get("path"),
            "category": j.get("category"),
            "tci_tier": j.get("tier"),
            "tier_period": j.get("tier_period"),
            "print_issn": j.get("print_issn"),
            "online_issn": j.get("online_issn"),
            "url": j.get("journal_url"),
        }
        for j in data.get("hits", [])
    ]
    return _dump({"total": data.get("total"), "page": data.get("page"), "journals": journals})


@mcp.tool()
def list_subject_groups() -> str:
    """List ThaiJO subject groups and their category codes (for search_articles' categories filter)."""
    return _dump(_request("GET", "/groups"))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
