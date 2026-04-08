import hmac
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from src.db.repository import PostRepository


REQUIRED_FIELDS = ("external_id", "slug", "title", "content_markdown", "weight", "published_date")
SLUG_RE = re.compile(r"^[a-z0-9-]{1,180}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_slug(value: str) -> str:
    return value.strip().lower()


def _normalize_tag(value: str) -> tuple[str, str]:
    cleaned = value.strip()
    slug = re.sub(r"[^a-z0-9-]+", "-", cleaned.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug, cleaned


def _parse_auth_token(headers: dict[str, str]) -> str:
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return ""
    return auth[7:].strip()


def _validate_item(index: int, item: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(item, dict):
        return None, {"index": index, "error_code": "INVALID_ITEM", "reason": "item must be an object"}

    missing = [name for name in REQUIRED_FIELDS if item.get(name) in (None, "")]
    if missing:
        return None, {
            "index": index,
            "external_id": item.get("external_id"),
            "error_code": "MISSING_FIELDS",
            "reason": f"missing required fields: {', '.join(missing)}",
        }

    try:
        weight = int(item["weight"])
    except (TypeError, ValueError):
        return None, {
            "index": index,
            "external_id": item.get("external_id"),
            "error_code": "INVALID_WEIGHT",
            "reason": "weight must be an integer",
        }
    if weight < 0 or weight > 1000:
        return None, {
            "index": index,
            "external_id": item.get("external_id"),
            "error_code": "INVALID_WEIGHT_RANGE",
            "reason": "weight must be between 0 and 1000",
        }

    slug = _normalize_slug(str(item["slug"]))
    if not SLUG_RE.fullmatch(slug):
        return None, {
            "index": index,
            "external_id": item.get("external_id"),
            "error_code": "INVALID_SLUG",
            "reason": "slug must match [a-z0-9-] and be <= 180 chars",
        }

    published_date = str(item["published_date"]).strip()
    if not DATE_RE.fullmatch(published_date):
        return None, {
            "index": index,
            "external_id": item.get("external_id"),
            "error_code": "INVALID_PUBLISHED_DATE",
            "reason": "published_date must be YYYY-MM-DD",
        }

    tags = item.get("tags", [])
    if tags is None:
        tags = []
    if not isinstance(tags, list):
        return None, {
            "index": index,
            "external_id": item.get("external_id"),
            "error_code": "INVALID_TAGS",
            "reason": "tags must be an array",
        }
    if len(tags) > 20:
        return None, {
            "index": index,
            "external_id": item.get("external_id"),
            "error_code": "TOO_MANY_TAGS",
            "reason": "tags cannot exceed 20",
        }

    normalized_tags: list[tuple[str, str]] = []
    seen_tag_slugs: set[str] = set()
    for raw_tag in tags:
        if not isinstance(raw_tag, str) or not raw_tag.strip():
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "INVALID_TAG",
                "reason": "each tag must be a non-empty string",
            }
        tag_slug, tag_name = _normalize_tag(raw_tag)
        if not tag_slug:
            return None, {
                "index": index,
                "external_id": item.get("external_id"),
                "error_code": "INVALID_TAG",
                "reason": "tag contains no valid characters",
            }
        if tag_slug in seen_tag_slugs:
            continue
        seen_tag_slugs.add(tag_slug)
        normalized_tags.append((tag_slug, tag_name))

    normalized = {
        "external_id": str(item["external_id"]).strip(),
        "slug": slug,
        "title": str(item["title"]).strip(),
        "excerpt": item.get("excerpt"),
        "content_markdown": str(item["content_markdown"]),
        "cover_image_url": item.get("cover_image_url"),
        "topic": item.get("topic"),
        "weight": weight,
        "published_date": published_date,
        "published_at": item.get("published_at"),
        "is_published": 1 if item.get("is_published", True) else 0,
        "tags": normalized_tags,
    }
    return normalized, None


def handle_bulk_ingest(
    repo: PostRepository,
    headers: dict[str, str] | None,
    body: str | None,
    ingest_api_key: str,
    max_items: int = 100,
    max_body_bytes: int = 1_000_000,
) -> tuple[int, dict[str, Any]]:
    if not ingest_api_key:
        return 500, {"error": "Ingest API key is not configured"}

    request_headers = headers or {}
    token = _parse_auth_token(request_headers)
    if not token or not hmac.compare_digest(token, ingest_api_key):
        return 401, {"error": "Unauthorized"}

    raw_body = body or ""
    if len(raw_body.encode("utf-8")) > max_body_bytes:
        return 413, {"error": "Payload Too Large"}

    try:
        payload = json.loads(raw_body or "{}")
    except json.JSONDecodeError:
        return 400, {"error": "Invalid JSON body"}

    items = payload.get("items")
    if not isinstance(items, list):
        return 400, {"error": "`items` must be an array"}
    if len(items) > max_items:
        return 400, {"error": f"`items` cannot exceed {max_items}"}

    inserted = 0
    updated = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    seen_external_ids: set[str] = set()
    now_iso = _now_iso()

    for index, item in enumerate(items):
        normalized_item, validation_error = _validate_item(index, item)
        if validation_error is not None:
            failed += 1
            errors.append(validation_error)
            continue

        assert normalized_item is not None
        external_id = normalized_item["external_id"]
        if external_id in seen_external_ids:
            failed += 1
            errors.append(
                {
                    "index": index,
                    "external_id": external_id,
                    "error_code": "DUPLICATE_EXTERNAL_ID_IN_BATCH",
                    "reason": "duplicate external_id in payload",
                }
            )
            continue
        seen_external_ids.add(external_id)

        try:
            action, post_id = repo.upsert_post(normalized_item, now_iso=now_iso)
            repo.replace_post_tags(post_id=post_id, tags=normalized_item["tags"], created_at=now_iso)
            if action == "inserted":
                inserted += 1
            else:
                updated += 1
        except ValueError as error:
            failed += 1
            code = str(error)
            if code == "SLUG_CONFLICT":
                errors.append(
                    {
                        "index": index,
                        "external_id": external_id,
                        "error_code": "SLUG_CONFLICT",
                        "reason": "slug already assigned to another post",
                    }
                )
                continue
            errors.append(
                {
                    "index": index,
                    "external_id": external_id,
                    "error_code": "INGEST_VALIDATION_ERROR",
                    "reason": str(error),
                }
            )
        except sqlite3.Error as error:
            failed += 1
            errors.append(
                {
                    "index": index,
                    "external_id": external_id,
                    "error_code": "DB_ERROR",
                    "reason": str(error),
                }
            )

    repo.conn.commit()
    return 200, {"success": True, "inserted": inserted, "updated": updated, "failed": failed, "errors": errors}
