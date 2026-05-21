"""Dates de publication World News : parsing et tri par récence."""

from __future__ import annotations

from datetime import datetime, timezone

from services.news import (
    parse_worldnews_publish_date,
    sort_articles_by_recency,
)


def test_parse_worldnews_publish_date_datetime() -> None:
    raw = datetime(2024, 4, 6, 22, 44, 18, tzinfo=timezone.utc)
    assert parse_worldnews_publish_date(raw) == raw


def test_parse_worldnews_publish_date_string() -> None:
    dt = parse_worldnews_publish_date("2024-04-06 22:44:18")
    assert dt is not None
    assert dt.year == 2024 and dt.month == 4 and dt.day == 6


def test_sort_articles_by_recency_newest_first() -> None:
    old = datetime(2024, 1, 1, tzinfo=timezone.utc)
    recent = datetime(2026, 5, 1, tzinfo=timezone.utc)
    items = [
        {"title": "Ancien", "published_at": old},
        {"title": "Récent", "published_at": recent},
        {"title": "Sans date"},
    ]
    ordered = sort_articles_by_recency(items)
    assert ordered[0]["title"] == "Récent"
    assert ordered[1]["title"] == "Ancien"
