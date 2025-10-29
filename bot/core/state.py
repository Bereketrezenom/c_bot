"""In-memory shared state for counselor selections, etc."""

# Maps counselor telegram_id -> currently selected case_id
counselor_active_case_selection: dict[int, str] = {}


