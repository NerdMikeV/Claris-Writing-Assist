import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_pending_submissions() -> list[dict]:
    """Fetch all submissions with status 'pending_review', ordered by created_at DESC."""
    response = supabase.table("submissions") \
        .select("*") \
        .eq("status", "pending_review") \
        .order("created_at", desc=True) \
        .execute()
    return response.data


def get_submission_by_id(submission_id: str) -> Optional[dict]:
    """Fetch a single submission by its ID."""
    response = supabase.table("submissions") \
        .select("*") \
        .eq("id", submission_id) \
        .single() \
        .execute()
    return response.data


def create_submission(data: dict) -> dict:
    """
    Create a new submission in the database.

    Expected data fields:
    - author: str
    - raw_input: str
    - ai_draft: str (optional)
    - graphic_description: str (optional)
    - graphic_type: str (optional)
    - graphic_data: str (optional, base64)
    - data_sources: dict/list (optional, JSONB)
    - research_urls: dict/list (optional, JSONB)
    - status: str (default: 'pending_review')
    """
    submission_data = {
        "author": data["author"],
        "raw_input": data["raw_input"],
        "ai_draft": data.get("ai_draft"),
        "graphic_description": data.get("graphic_description"),
        "graphic_type": data.get("graphic_type"),
        "graphic_data": data.get("graphic_data"),
        "data_sources": data.get("data_sources"),
        "research_urls": data.get("research_urls"),
        "status": data.get("status", "pending_review"),
    }

    response = supabase.table("submissions") \
        .insert(submission_data) \
        .execute()

    return response.data[0] if response.data else None


def update_submission(submission_id: str, data: dict) -> dict:
    """
    Update an existing submission.

    Common update operations:
    - Approve: { "status": "approved", "ai_draft": edited_post, "reviewed_at": now }
    - Reject: { "status": "rejected", "reviewed_at": now }
    - Update graphic: { "graphic_data": new_base64_data }
    """
    response = supabase.table("submissions") \
        .update(data) \
        .eq("id", submission_id) \
        .execute()

    return response.data[0] if response.data else None


def delete_submission(submission_id: str) -> bool:
    """Delete a submission by ID."""
    response = supabase.table("submissions") \
        .delete() \
        .eq("id", submission_id) \
        .execute()

    return len(response.data) > 0
