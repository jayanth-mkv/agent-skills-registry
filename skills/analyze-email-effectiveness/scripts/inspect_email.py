#!/usr/bin/env python3
"""Extract structural evidence from .eml, HTML, or plain-text email artifacts."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
import unicodedata
from collections import Counter
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

WORD = re.compile(r"\b[\w\u00C0-\u024F\u1E00-\u1EFF]+(?:['’\-][\w\u00C0-\u024F\u1E00-\u1EFF]+)*\b")
SENTENCE = re.compile(r"[.!?]+(?:\s|$)")
PERSONALIZATION = re.compile(
    r"(\{\{[^{}\n]{1,80}\}\}|%%[^%\n]{1,80}%%|\{[a-zA-Z_][^{}\n]{0,79}\}|"
    r"\[(?:first|last|full|company|account)[ _-]?name\])",
    re.IGNORECASE,
)
ACTIVE_TAGS = {"script", "form", "iframe", "object", "embed"}
SHORTENERS = {
    "bit.ly",
    "buff.ly",
    "cutt.ly",
    "goo.gl",
    "ow.ly",
    "rebrand.ly",
    "t.co",
    "tiny.cc",
    "tinyurl.com",
}
SECONDARY_LINK_TEXT = {
    "privacy",
    "privacy policy",
    "terms",
    "unsubscribe",
    "view in browser",
    "view online",
    "manage preferences",
}
INVISIBLE_OR_BIDI_CONTROLS = {
    "\u061c",
    "\u200b",
    "\u200c",
    "\u200d",
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
    "\ufeff",
}
HIGH_RISK_ATTACHMENT_EXTENSIONS = {
    ".app",
    ".apk",
    ".bat",
    ".cmd",
    ".com",
    ".cpl",
    ".dll",
    ".dmg",
    ".exe",
    ".hta",
    ".iso",
    ".jar",
    ".js",
    ".jse",
    ".lnk",
    ".msi",
    ".msp",
    ".ps1",
    ".reg",
    ".scr",
    ".vbe",
    ".vbs",
    ".wsf",
}
MACRO_ATTACHMENT_EXTENSIONS = {".docm", ".dotm", ".xlsm", ".xltm", ".pptm", ".potm"}
ARCHIVE_ATTACHMENT_EXTENSIONS = {
    ".7z",
    ".bz2",
    ".cab",
    ".gz",
    ".rar",
    ".tar",
    ".tgz",
    ".xz",
    ".zip",
}
HIDDEN_STYLE_PATTERNS = (
    "display:none",
    "visibility:hidden",
    "opacity:0",
    "font-size:0",
    "max-height:0",
    "mso-hide:all",
    "color:transparent",
)


def address_domain(value: str) -> str | None:
    address = parseaddr(value)[1].strip()
    if "@" not in address:
        return None
    domain = address.rsplit("@", 1)[1].strip().rstrip(".").casefold()
    try:
        return domain.encode("idna").decode("ascii")
    except UnicodeError:
        return None


def summarize_dkim_signature(value: str) -> dict[str, object]:
    tags: dict[str, str] = {}
    for fragment in value.split(";"):
        if "=" not in fragment:
            continue
        raw_key, raw_value = fragment.split("=", 1)
        key = raw_key.strip().casefold()
        if key and key not in tags:
            tags[key] = " ".join(raw_value.split())
    return {
        "domain": tags.get("d"),
        "selector": tags.get("s"),
        "algorithm": tags.get("a"),
        "canonicalization": tags.get("c"),
        "identity": tags.get("i"),
        "signed_headers": tags.get("h", "").split(":") if tags.get("h") else [],
        "body_length_tag_present": "l" in tags,
        "timestamp": tags.get("t"),
        "expiration": tags.get("x"),
    }


def unicode_control_summary(value: str) -> dict[str, object]:
    counts = Counter(character for character in value if character in INVISIBLE_OR_BIDI_CONTROLS)
    return {
        "count": sum(counts.values()),
        "characters": [
            {
                "codepoint": f"U+{ord(character):04X}",
                "name": unicodedata.name(character, "UNKNOWN"),
                "count": count,
            }
            for character, count in sorted(counts.items(), key=lambda item: ord(item[0]))
        ],
    }


def parse_dimension(value: str) -> int | None:
    match = re.fullmatch(r"\s*(\d+)(?:px)?\s*", value, re.IGNORECASE)
    return int(match.group(1)) if match else None


def compact_destination(raw_url: str) -> str | None:
    try:
        parsed = urlsplit(raw_url)
        port = parsed.port
    except ValueError:
        return None
    if not parsed.scheme and not parsed.netloc:
        return parsed.path or None
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    if port:
        hostname = f"{hostname}:{port}"
    return urlunsplit((parsed.scheme, hostname, parsed.path, "", ""))


def attachment_evidence(part: Message) -> dict[str, object]:
    payload = part.get_payload(decode=True) or b""
    filename = part.get_filename()
    suffix = Path(filename).suffix.casefold() if filename else ""
    review_reasons: list[str] = []
    if suffix in HIGH_RISK_ATTACHMENT_EXTENSIONS:
        review_reasons.append("executable_or_script_extension")
    if suffix in MACRO_ATTACHMENT_EXTENSIONS:
        review_reasons.append("macro_enabled_office_extension")
    if suffix in ARCHIVE_ATTACHMENT_EXTENSIONS:
        review_reasons.append("archive_requires_nested_content_review")
    if part.get_content_type() == "application/octet-stream":
        review_reasons.append("generic_binary_content_type")
    return {
        "filename": filename,
        "content_type": part.get_content_type(),
        "content_disposition": part.get_content_disposition(),
        "content_id": str(part.get("Content-ID", "")) or None,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "review_reasons": review_reasons,
        "malicious": None,
    }


def authentication_results_evidence(
    value: str,
    trusted_authserv_ids: set[str],
) -> dict[str, object]:
    authserv_fragment = value.split(";", 1)[0].strip()
    authserv_id = authserv_fragment.split()[0].casefold() if authserv_fragment else None
    return {
        "authserv_id": authserv_id,
        "trust_status": (
            "trusted_by_user"
            if authserv_id and authserv_id in trusted_authserv_ids
            else "unverified_boundary"
        ),
        "value": value,
    }


class EvidenceHTMLParser(HTMLParser):
    """Collect visible-text, link, image, language, and active-content facts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active_tags: set[str] = set()
        self.base_href: str | None = None
        self.document_direction: str | None = None
        self.heading_counts: Counter[str] = Counter()
        self.html_language: str | None = None
        self.image_count = 0
        self.image_details: list[dict[str, object]] = []
        self.images_empty_alt = 0
        self.images_missing_alt = 0
        self.linked_stylesheets = 0
        self.links: list[dict[str, str]] = []
        self.meta_viewport = False
        self.hidden_content_candidates: list[dict[str, str]] = []
        self.table_count = 0
        self.layout_tables_missing_presentation_role = 0
        self.text_parts: list[str] = []
        self._ignored_depth = 0
        self._link_stack: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        attributes = {key.casefold(): value or "" for key, value in attrs}
        compact_style = re.sub(r"\s+", "", attributes.get("style", "").casefold())
        if lowered in ACTIVE_TAGS:
            self.active_tags.add(lowered)
        if any(key.startswith("on") for key in attributes):
            self.active_tags.add("event-handler")
        hidden_reasons = [
            pattern
            for pattern in HIDDEN_STYLE_PATTERNS
            if pattern in compact_style
        ]
        if "hidden" in attributes:
            hidden_reasons.append("hidden-attribute")
        if hidden_reasons:
            self.hidden_content_candidates.append(
                {"tag": lowered, "reasons": ", ".join(hidden_reasons)}
            )
        if lowered in {"script", "style", "head"}:
            self._ignored_depth += 1
        if lowered == "html":
            if attributes.get("lang"):
                self.html_language = attributes["lang"].strip()
            if attributes.get("dir"):
                self.document_direction = attributes["dir"].strip().casefold()
        if lowered == "base" and attributes.get("href"):
            self.base_href = attributes["href"].strip()
        if (
            lowered == "meta"
            and attributes.get("name", "").casefold() == "viewport"
            and attributes.get("content")
        ):
            self.meta_viewport = True
        if (
            lowered == "link"
            and "stylesheet" in attributes.get("rel", "").casefold().split()
        ):
            self.linked_stylesheets += 1
        if lowered in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_counts[lowered] += 1
        if lowered == "table":
            self.table_count += 1
            if attributes.get("role", "").casefold() not in {"presentation", "none"}:
                self.layout_tables_missing_presentation_role += 1
        if lowered == "img":
            self.image_count += 1
            if "alt" not in attributes:
                self.images_missing_alt += 1
            elif not attributes["alt"].strip():
                self.images_empty_alt += 1
            width = parse_dimension(attributes.get("width", ""))
            height = parse_dimension(attributes.get("height", ""))
            tracking_candidate = bool(
                (width is not None and width <= 1 and height is not None and height <= 1)
                or "width:1px" in compact_style
                and "height:1px" in compact_style
            )
            self.image_details.append(
                {
                    "source": compact_destination(attributes.get("src", "")),
                    "alt_present": "alt" in attributes,
                    "alt_empty": "alt" in attributes and not attributes["alt"].strip(),
                    "width": width,
                    "height": height,
                    "tracking_pixel_candidate": tracking_candidate,
                }
            )
        if lowered == "a" and attributes.get("href"):
            self.links.append(
                {
                    "href": attributes["href"].strip(),
                    "text": "",
                    "title": attributes.get("title", "").strip(),
                }
            )
            self._link_stack.append(len(self.links) - 1)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in {"script", "style", "head"} and self._ignored_depth:
            self._ignored_depth -= 1
        if lowered == "a" and self._link_stack:
            self._link_stack.pop()

    def handle_data(self, data: str) -> None:
        normalized = " ".join(data.split())
        if not normalized or self._ignored_depth:
            return
        self.text_parts.append(normalized)
        if self._link_stack:
            index = self._link_stack[-1]
            current = self.links[index]["text"]
            self.links[index]["text"] = f"{current} {normalized}".strip()


def decode_parts(message: Message) -> tuple[list[str], list[str], list[dict[str, object]]]:
    plain: list[str] = []
    html: list[str] = []
    attachments: list[dict[str, object]] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        if part.get_content_disposition() == "attachment" or (
            part.get_filename() and part.get_content_disposition() != "inline"
        ):
            attachments.append(attachment_evidence(part))
            continue
        content_type = part.get_content_type()
        if content_type not in {"text/plain", "text/html"}:
            if part.get_content_disposition() == "inline" and part.get_filename():
                attachments.append(attachment_evidence(part))
            continue
        try:
            content = part.get_content()
        except (LookupError, UnicodeError):
            payload = part.get_payload(decode=True) or b""
            content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if isinstance(content, str):
            (plain if content_type == "text/plain" else html).append(content)
    return plain, html, attachments


def detect_type(path_value: str, requested: str, raw: bytes) -> str:
    if requested != "auto":
        return requested
    if path_value != "-":
        suffix = Path(path_value).suffix.casefold()
        if suffix == ".eml":
            return "eml"
        if suffix in {".html", ".htm"}:
            return "html"
        if suffix in {".txt", ".md"}:
            return "text"
    leading = raw.lstrip()[:512].casefold()
    header_sample = raw[:4096].decode("ascii", errors="ignore")
    common_headers = re.findall(
        r"(?im)^(?:from|to|subject|date|message-id|mime-version|content-type|received):",
        header_sample,
    )
    if len(common_headers) >= 2 and re.search(r"\r?\n\r?\n", header_sample):
        return "eml"
    if b"<html" in leading or b"<!doctype html" in leading:
        return "html"
    return "text"


def parse_html(chunks: list[str]) -> tuple[list[EvidenceHTMLParser], list[str]]:
    parsers: list[EvidenceHTMLParser] = []
    defects: list[str] = []
    for html in chunks:
        parser = EvidenceHTMLParser()
        try:
            parser.feed(html)
            parser.close()
        except Exception as exc:
            defects.append(f"HTML parser error: {exc}")
        parsers.append(parser)
    return parsers, defects


def inspect_bytes(
    raw: bytes,
    artifact_type: str,
    subject_override: str | None = None,
    preview_override: str | None = None,
    trusted_authserv_ids: set[str] | None = None,
) -> dict[str, object]:
    headers: dict[str, object] = {}
    identity_hints: dict[str, object] = {}
    mime_defects: list[str] = []
    attachment_items: list[dict[str, object]] = []
    trusted_ids = {value.casefold() for value in (trusted_authserv_ids or set())}
    message_header_gaps: list[str] = []
    one_click: dict[str, object] = {}

    if artifact_type == "eml":
        message = BytesParser(policy=policy.default).parsebytes(raw)
        plain_parts, html_parts, attachment_items = decode_parts(message)
        authentication_results = [
            authentication_results_evidence(str(value), trusted_ids)
            for value in message.get_all("Authentication-Results", [])
        ]
        received_spf = [str(value) for value in message.get_all("Received-SPF", [])]
        dkim_signatures = [
            summarize_dkim_signature(str(value))
            for value in message.get_all("DKIM-Signature", [])
        ]
        from_addresses = getaddresses(message.get_all("From", []))
        from_domains = sorted(
            {
                domain
                for _, address in from_addresses
                if (domain := address_domain(address))
            }
        )
        return_path = str(message.get("Return-Path", ""))
        list_unsubscribe_values = [
            str(value) for value in message.get_all("List-Unsubscribe", [])
        ]
        list_unsubscribe_post_values = [
            str(value) for value in message.get_all("List-Unsubscribe-Post", [])
        ]
        unsubscribe_uris = [
            uri.strip()
            for value in list_unsubscribe_values
            for uri in re.findall(r"<([^<>]+)>", value)
        ]
        one_click_https_uris: list[str] = []
        for uri in unsubscribe_uris:
            try:
                if urlsplit(uri).scheme.casefold() == "https":
                    one_click_https_uris.append(uri)
            except ValueError:
                continue
        post_exact = (
            len(list_unsubscribe_post_values) == 1
            and list_unsubscribe_post_values[0].strip() == "List-Unsubscribe=One-Click"
        )
        claimed_dkim_coverage = any(
            {
                header.strip().casefold()
                for header in signature["signed_headers"]
            }
            >= {"list-unsubscribe", "list-unsubscribe-post"}
            for signature in dkim_signatures
        )
        one_click = {
            "list_unsubscribe_header_count": len(list_unsubscribe_values),
            "list_unsubscribe_post_header_count": len(list_unsubscribe_post_values),
            "uris": unsubscribe_uris,
            "https_uris": one_click_https_uris,
            "post_value_exact": post_exact,
            "claimed_dkim_header_coverage": claimed_dkim_coverage,
            "structurally_ready": bool(
                len(list_unsubscribe_values) == 1
                and len(list_unsubscribe_post_values) == 1
                and one_click_https_uris
                and post_exact
                and claimed_dkim_coverage
            ),
            "verified_operational": None,
        }
        for header_name in ("From", "Date"):
            if not message.get_all(header_name, []):
                message_header_gaps.append(header_name)
        if not message.get_all("Message-ID", []):
            message_header_gaps.append("Message-ID (recommended)")
        if (
            (message.is_multipart() or message.get_content_type() != "text/plain")
            and not message.get_all("MIME-Version", [])
        ):
            message_header_gaps.append("MIME-Version")
        headers = {
            "from": str(message.get("From", "")) or None,
            "from_address_count": len(from_addresses),
            "to": str(message.get("To", "")) or None,
            "return_path": return_path or None,
            "reply_to": str(message.get("Reply-To", "")) or None,
            "date": str(message.get("Date", "")) or None,
            "message_id": str(message.get("Message-ID", "")) or None,
            "mime_version": str(message.get("MIME-Version", "")) or None,
            "content_type": str(message.get("Content-Type", "")) or None,
            "list_id": str(message.get("List-ID", "")) or None,
            "list_unsubscribe": list_unsubscribe_values,
            "list_unsubscribe_post": list_unsubscribe_post_values,
            "feedback_id": [str(value) for value in message.get_all("Feedback-ID", [])],
            "complaints_to": [str(value) for value in message.get_all("Complaints-To", [])],
            "auto_submitted": str(message.get("Auto-Submitted", "")) or None,
            "precedence": str(message.get("Precedence", "")) or None,
            "received_count": len(message.get_all("Received", [])),
            "authentication_results": authentication_results,
            "received_spf": received_spf,
            "dkim_signatures": dkim_signatures,
            "arc_authentication_results": [
                str(value) for value in message.get_all("ARC-Authentication-Results", [])
            ],
            "arc_seal_count": len(message.get_all("ARC-Seal", [])),
            "arc_message_signature_count": len(message.get_all("ARC-Message-Signature", [])),
            "missing_or_recommended_headers": message_header_gaps,
        }
        identity_hints = {
            "header_from_domains": from_domains,
            "mail_from_domain": address_domain(return_path),
            "reply_to_domain": address_domain(str(message.get("Reply-To", ""))),
            "dkim_selector_domains": [
                {
                    "selector": signature["selector"],
                    "domain": signature["domain"],
                }
                for signature in dkim_signatures
                if signature["selector"] and signature["domain"]
            ],
        }
        subject = subject_override if subject_override is not None else str(message.get("Subject", ""))
        mime_defects = [f"{type(defect).__name__}: {defect}" for defect in message.defects]
    else:
        decoded = raw.decode("utf-8", errors="replace")
        plain_parts = [decoded] if artifact_type == "text" else []
        html_parts = [decoded] if artifact_type == "html" else []
        subject = subject_override or ""

    parsers, html_defects = parse_html(html_parts)
    visible_html = " ".join(text for parser in parsers for text in parser.text_parts)
    plain_text = "\n".join(plain_parts)
    visible_text = "\n".join(part for part in (plain_text, visible_html) if part)
    words = WORD.findall(visible_text)
    sentences = SENTENCE.findall(visible_text)

    links = [link for parser in parsers for link in parser.links]
    link_facts: list[dict[str, object]] = []
    domains: Counter[str] = Counter()
    anchor_destination_mismatches = 0
    bare_ip_links = 0
    insecure_links = 0
    mailto_links = 0
    punycode_links = 0
    relative_links = 0
    shortened_links = 0
    userinfo_links = 0
    unsafe_schemes = 0
    for link in links:
        malformed = False
        try:
            parsed = urlsplit(link["href"])
            scheme = parsed.scheme.casefold()
            domain = (parsed.hostname or "").casefold()
        except ValueError:
            scheme = "malformed"
            domain = ""
            parsed = None
            malformed = True
        if domain:
            domains[domain] += 1
        if scheme == "http":
            insecure_links += 1
        if scheme == "mailto":
            mailto_links += 1
        if domain in SHORTENERS:
            shortened_links += 1
        if domain and any(label.startswith("xn--") for label in domain.split(".")):
            punycode_links += 1
        bare_ip = False
        if domain:
            try:
                ipaddress.ip_address(domain)
            except ValueError:
                pass
            else:
                bare_ip_links += 1
                bare_ip = True
        if parsed and parsed.username:
            userinfo_links += 1
        if not scheme and not domain and link["href"].strip():
            relative_links += 1
        if malformed or scheme and scheme not in {"http", "https", "mailto"}:
            unsafe_schemes += 1

        displayed_domain: str | None = None
        text_candidate = (link["text"] or "").strip()
        if text_candidate and (
            re.match(r"(?i)^https?://", text_candidate)
            or re.fullmatch(r"(?i)(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/.*)?", text_candidate)
        ):
            display_url = (
                text_candidate
                if re.match(r"(?i)^https?://", text_candidate)
                else f"https://{text_candidate}"
            )
            try:
                displayed_domain = (urlsplit(display_url).hostname or "").casefold() or None
            except ValueError:
                displayed_domain = None
        mismatch = bool(displayed_domain and domain and displayed_domain != domain)
        if mismatch:
            anchor_destination_mismatches += 1
        link_facts.append(
            {
                "text": link["text"] or None,
                "title": link.get("title") or None,
                "destination": compact_destination(link["href"]),
                "scheme": scheme or None,
                "domain": domain or None,
                "displayed_domain": displayed_domain,
                "display_destination_mismatch": mismatch,
                "userinfo_present": bool(parsed and parsed.username),
                "bare_ip_destination": bare_ip,
            }
        )

    active_tags = sorted({tag for parser in parsers for tag in parser.active_tags})
    image_count = sum(parser.image_count for parser in parsers)
    image_details = [detail for parser in parsers for detail in parser.image_details]
    empty_alt = sum(parser.images_empty_alt for parser in parsers)
    missing_alt = sum(parser.images_missing_alt for parser in parsers)
    tracking_pixel_candidates = sum(
        bool(detail["tracking_pixel_candidate"]) for detail in image_details
    )
    hidden_candidates = [
        detail for parser in parsers for detail in parser.hidden_content_candidates
    ]
    linked_stylesheets = sum(parser.linked_stylesheets for parser in parsers)
    tables = sum(parser.table_count for parser in parsers)
    tables_without_presentation_role = sum(
        parser.layout_tables_missing_presentation_role for parser in parsers
    )
    viewport_present = any(parser.meta_viewport for parser in parsers)
    heading_counts: Counter[str] = Counter()
    for parser in parsers:
        heading_counts.update(parser.heading_counts)
    languages = sorted({parser.html_language for parser in parsers if parser.html_language})
    directions = sorted(
        {parser.document_direction for parser in parsers if parser.document_direction}
    )

    personalization_tokens = sorted(set(PERSONALIZATION.findall(subject + "\n" + visible_text)))
    unsubscribe_mentions = len(re.findall(r"(?i)\bunsubscribe\b", visible_text))
    secondary_links = sum((link["text"] or "").strip().casefold() in SECONDARY_LINK_TEXT for link in links)
    primary_link_candidates = max(0, len(links) - secondary_links)
    preview = preview_override or ""
    unicode_controls = {
        "subject": unicode_control_summary(subject),
        "preview": unicode_control_summary(preview),
        "from_header": unicode_control_summary(str(headers.get("from") or "")),
        "rendered_text": unicode_control_summary(visible_text),
        "link_text": unicode_control_summary(
            "\n".join(str(link.get("text") or "") for link in links)
        ),
    }
    unicode_control_count = sum(
        int(item["count"]) for item in unicode_controls.values()
    )
    from_domain_set = set(identity_hints.get("header_from_domains", []))
    reply_to_domain = identity_hints.get("reply_to_domain")
    reply_to_differs = bool(
        artifact_type == "eml"
        and len(from_domain_set) == 1
        and reply_to_domain
        and reply_to_domain not in from_domain_set
    )
    linked_domain_set = set(domains)
    external_link_domains = sorted(linked_domain_set - from_domain_set)
    attachment_review_count = sum(
        bool(item["review_reasons"]) for item in attachment_items
    )
    html_part_bytes = [len(value.encode("utf-8")) for value in html_parts]

    flags: list[str] = []
    if html_parts and artifact_type == "eml" and not plain_parts:
        flags.append("HTML message has no text/plain alternative.")
    if html_parts and not languages:
        flags.append("HTML omits a document language.")
    if html_parts and not viewport_present:
        flags.append("HTML has no viewport meta declaration; test narrow-screen rendering.")
    if active_tags:
        flags.append("Active or unsupported HTML: " + ", ".join(active_tags) + ".")
    if linked_stylesheets:
        flags.append(
            f"{linked_stylesheets} external stylesheet link(s) require client-compatibility testing."
        )
    if hidden_candidates:
        flags.append(
            f"{len(hidden_candidates)} hidden-content CSS/attribute candidate(s) require intent review."
        )
    if missing_alt:
        flags.append(f"{missing_alt} image(s) omit the alt attribute.")
    if tracking_pixel_candidates:
        flags.append(
            f"{tracking_pixel_candidates} one-pixel image candidate(s) may be tracking or decorative assets."
        )
    if tables_without_presentation_role:
        flags.append(
            f"{tables_without_presentation_role} table(s) omit role=presentation/none; distinguish layout from data tables."
        )
    if insecure_links:
        flags.append(f"{insecure_links} link(s) use HTTP instead of HTTPS.")
    if shortened_links:
        flags.append(f"{shortened_links} link(s) use a URL shortener.")
    if unsafe_schemes:
        flags.append(f"{unsafe_schemes} link(s) use malformed or unsupported schemes.")
    if anchor_destination_mismatches:
        flags.append(
            f"{anchor_destination_mismatches} URL-like link label(s) name a different destination domain."
        )
    if bare_ip_links:
        flags.append(f"{bare_ip_links} link(s) use a bare IP address as the destination.")
    if userinfo_links:
        flags.append(f"{userinfo_links} link(s) contain URL userinfo before the destination host.")
    if punycode_links:
        flags.append(f"{punycode_links} link(s) use an internationalized/punycode hostname.")
    if relative_links:
        flags.append(f"{relative_links} relative link(s) need a verified base URL after rendering.")
    if subject and preview and subject.strip().casefold() == preview.strip().casefold():
        flags.append("Preview text exactly repeats the subject.")
    if artifact_type == "eml" and message_header_gaps:
        flags.append(
            "Missing required or recommended message headers: "
            + ", ".join(message_header_gaps)
            + "."
        )
    if artifact_type == "eml" and int(headers.get("from_address_count") or 0) != 1:
        flags.append(
            "Header From does not contain exactly one parsed mailbox; DMARC evaluation may be impossible or receiver-specific."
        )
    if artifact_type == "eml" and (
        one_click["list_unsubscribe_header_count"]
        or one_click["list_unsubscribe_post_header_count"]
    ) and not one_click["structurally_ready"]:
        flags.append(
            "One-click unsubscribe headers do not satisfy all inspectable RFC 8058 structural requirements."
        )
    if reply_to_differs:
        flags.append(
            "Reply-To uses a different domain from the single Header From domain; verify that the handoff is expected."
        )
    if unicode_control_count:
        flags.append(
            f"{unicode_control_count} invisible or bidirectional Unicode control character(s) require intent review."
        )
    if attachment_review_count:
        flags.append(
            f"{attachment_review_count} attachment(s) have extensions or types requiring security review."
        )
    if (
        artifact_type == "eml"
        and headers.get("authentication_results")
        and not any(
            item["trust_status"] == "trusted_by_user"
            for item in headers["authentication_results"]
        )
    ):
        flags.append(
            "Authentication-Results headers are present, but no matching trusted authserv-id was supplied."
        )
    if mime_defects:
        flags.append("The message parser reported MIME defects.")

    return {
        "schema_version": "2.0",
        "artifact_type": artifact_type,
        "bytes": len(raw),
        "subject": {
            "text": subject or None,
            "characters": len(subject),
            "unicode_controls": unicode_controls["subject"],
        },
        "preview": {
            "text": preview or None,
            "characters": len(preview),
            "unicode_controls": unicode_controls["preview"],
        },
        "headers": headers,
        "identity_hints": {
            **identity_hints,
            "reply_to_differs_from_header_from": reply_to_differs,
        },
        "one_click_unsubscribe": one_click,
        "body": {
            "plain_parts": len(plain_parts),
            "html_parts": len(html_parts),
            "visible_words": len(words),
            "sentences": len(sentences),
            "average_words_per_sentence": round(len(words) / len(sentences), 1) if sentences else None,
            "estimated_reading_minutes": round(len(words) / 200, 2) if words else 0,
            "unsubscribe_mentions": unsubscribe_mentions,
            "personalization_tokens": personalization_tokens,
            "unicode_controls": unicode_controls["rendered_text"],
        },
        "html": {
            "languages": languages,
            "directions": directions,
            "viewport_meta_present": viewport_present,
            "part_bytes": html_part_bytes,
            "base_hrefs": sorted(
                {parser.base_href for parser in parsers if parser.base_href}
            ),
            "headings": dict(sorted(heading_counts.items())),
            "images": image_count,
            "images_missing_alt": missing_alt,
            "images_empty_alt": empty_alt,
            "image_details": image_details,
            "tracking_pixel_candidates": tracking_pixel_candidates,
            "tables": tables,
            "tables_without_presentation_role": tables_without_presentation_role,
            "linked_stylesheets": linked_stylesheets,
            "hidden_content_candidates": hidden_candidates,
            "active_or_unsupported_tags": active_tags,
        },
        "links": {
            "total": len(links),
            "primary_candidates": primary_link_candidates,
            "secondary_or_preference": secondary_links,
            "domains": dict(sorted(domains.items())),
            "domains_outside_header_from": external_link_domains,
            "insecure": insecure_links,
            "mailto": mailto_links,
            "shortened": shortened_links,
            "relative": relative_links,
            "punycode": punycode_links,
            "bare_ip": bare_ip_links,
            "userinfo": userinfo_links,
            "display_destination_mismatches": anchor_destination_mismatches,
            "unsafe_or_malformed": unsafe_schemes,
            "items": link_facts,
        },
        "attachments": len(attachment_items),
        "attachment_details": {
            "count": len(attachment_items),
            "review_required": attachment_review_count,
            "items": attachment_items,
        },
        "unicode_controls": unicode_controls,
        "parser_defects": mime_defects + html_defects,
        "structural_flags": flags,
        "limitations": [
            "No strategic, consent, legal, authentication, inbox-placement, or performance conclusion is inferred.",
            "CTA candidates are link-count heuristics and require human review.",
            (
                "Authentication-Results are treated as trusted only when their authserv-id exactly matches "
                "a user-supplied trusted boundary; ARC still requires chain validation."
            ),
            "DKIM identity hints show claimed signatures; they do not prove signature verification.",
            "One-click unsubscribe readiness does not test the HTTPS POST endpoint or prove a valid covering DKIM signature.",
            "Hidden content, one-pixel images, link-domain differences, and attachment types are review signals, not proof of abuse.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to .eml, .html/.htm, or text; use - for stdin.")
    parser.add_argument(
        "--type",
        choices=("auto", "eml", "html", "text"),
        default="auto",
        help="Artifact type. Default: infer from extension/content.",
    )
    parser.add_argument("--subject", help="Subject override for HTML/text or comparison.")
    parser.add_argument("--preview", help="Preview/preheader text supplied separately.")
    parser.add_argument(
        "--trusted-authserv-id",
        action="append",
        default=[],
        metavar="DOMAIN",
        help=(
            "Authentication-Results authserv-id trusted by the operator of the receiving boundary. "
            "Repeat as needed; no value is trusted by default."
        ),
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=10 * 1024 * 1024,
        help="Refuse artifacts larger than this many bytes. Default: 10485760.",
    )
    return parser.parse_args()


def read_input(value: str, max_bytes: int) -> bytes:
    if max_bytes <= 0:
        raise ValueError("--max-bytes must be positive")
    if value == "-":
        raw = sys.stdin.buffer.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError(f"stdin exceeds --max-bytes ({max_bytes})")
        return raw
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(f"input is not a file: {path}")
    if path.stat().st_size > max_bytes:
        raise ValueError(f"input exceeds --max-bytes ({max_bytes}): {path}")
    return path.read_bytes()


def render_text(report: dict[str, object]) -> str:
    subject = report["subject"]
    body = report["body"]
    html = report["html"]
    links = report["links"]
    lines = [
        f"Artifact: {report['artifact_type']} ({report['bytes']} bytes)",
        f"Subject: {subject['characters']} characters",
        (
            f"Body: {body['visible_words']} visible words, "
            f"{body['estimated_reading_minutes']} estimated reading minutes"
        ),
        (
            f"HTML: {body['html_parts']} part(s), {html['images']} image(s), "
            f"{html['images_missing_alt']} missing alt"
        ),
        (
            f"Links: {links['total']} total across {len(links['domains'])} domain(s), "
            f"{links['primary_candidates']} primary candidate(s)"
        ),
    ]
    flags = report["structural_flags"]
    if flags:
        lines.append("Structural flags:")
        lines.extend(f"- {flag}" for flag in flags)
    else:
        lines.append("Structural flags: none detected")
    lines.append("Note: structural evidence only; strategic and performance analysis still requires context.")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        raw = read_input(args.input, args.max_bytes)
        artifact_type = detect_type(args.input, args.type, raw)
        report = inspect_bytes(
            raw,
            artifact_type,
            args.subject,
            args.preview,
            {value.casefold() for value in args.trusted_authserv_id},
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
