"""
week8_final_projects/project_helpers.py
=========================================
Shared utilities for all 4 final project options.
"""

import json
import datetime
from pathlib import Path
from typing import Any


def save_json(data: Any, filename: str, folder: str = ".") -> str:
    """Save data (dict/list/Pydantic model) to a JSON file."""
    path = Path(folder) / filename
    if hasattr(data, "model_dump"):
        content = data.model_dump()
    else:
        content = data
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, default=str))
    return str(path)


def load_json(filename: str, folder: str = ".") -> dict | list:
    path = Path(folder) / filename
    return json.loads(path.read_text())


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def truncate(text: str, max_len: int = 100) -> str:
    return text[:max_len] + ("..." if len(text) > max_len else "")


# ── Mock document store (for document analysis project) ───────────────────

MOCK_DOCUMENTS = [
    {
        "id": "doc_001",
        "title": "Q3 Sales Report",
        "content": (
            "Q3 revenue reached $4.2M, up 18% YoY. "
            "Key drivers: enterprise contracts (+35%), new SaaS tier (+22%). "
            "Churn rate decreased from 8% to 5.5%. "
            "EMEA expansion contributed $600K. "
            "Outlook for Q4: cautiously optimistic given macro headwinds."
        ),
        "type": "report",
    },
    {
        "id": "doc_002",
        "title": "Customer Feedback - October",
        "content": (
            "Positive feedback: UI improvements praised by 78% of users. "
            "Support response times improved. "
            "Negative: API rate limits too low for enterprise customers. "
            "Feature request: bulk export functionality. "
            "NPS score: 42 (up from 35 last month)."
        ),
        "type": "feedback",
    },
    {
        "id": "doc_003",
        "title": "Technical Incident Report - Oct 15",
        "content": (
            "Duration: 47 minutes. Impact: 12% of users experienced 5xx errors. "
            "Root cause: database connection pool exhausted due to slow query in reporting module. "
            "Resolution: added connection pool limit + query index. "
            "Action items: add monitoring alert for pool utilisation > 80%."
        ),
        "type": "incident",
    },
]


# ── Mock customer support tickets ─────────────────────────────────────────

MOCK_TICKETS = [
    {"id": "T001", "user": "alice@example.com", "message": "I can't log in to my account. Password reset email never arrives.", "priority": None},
    {"id": "T002", "user": "bob@company.com",   "message": "Billing charged me twice this month. Invoice #INV-4421.", "priority": None},
    {"id": "T003", "user": "carol@startup.io",  "message": "The API keeps returning 429 errors even though I'm on the Pro plan.", "priority": None},
    {"id": "T004", "user": "david@corp.com",    "message": "How do I export data to CSV? I can't find the option.", "priority": None},
    {"id": "T005", "user": "eve@agency.com",    "message": "App is completely down for our entire team since 2 hours ago.", "priority": None},
]
