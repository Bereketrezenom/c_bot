"""Case-related helper functions (labels and tags)."""

from typing import Any


def build_case_label(service: Any, counselor_id: int, case_dict: dict) -> str:
    try:
        cases = service.get_counselor_cases(str(counselor_id)) or []
        active = [c for c in cases if c.get('status') in ['assigned', 'active']]
        active.sort(key=lambda c: (c.get('updated_at') or c.get('created_at') or ''), reverse=True)
        idx = next((i for i, c in enumerate(active) if c.get('id') == case_dict.get('id')), None)
        base = f"Case #{idx + 1}" if idx is not None else f"Case {case_dict.get('id','')[:8]}"
        alias = case_dict.get('alias')
        return f"{base} [{alias}]" if alias else base
    except Exception:
        return f"Case {case_dict.get('id','')[:8]}"


def build_case_tag(service: Any, counselor_id: int, case_dict: dict) -> str:
    try:
        cases = service.get_counselor_cases(str(counselor_id)) or []
        active = [c for c in cases if c.get('status') in ['assigned', 'active']]
        active.sort(key=lambda c: (c.get('updated_at') or c.get('created_at') or ''), reverse=True)
        idx = next((i for i, c in enumerate(active) if c.get('id') == case_dict.get('id')), None)
        if idx is not None:
            return f"#case{idx + 1}"
    except Exception:
        pass
    return f"#case{(case_dict.get('id','')[:3] or '').lower()}"


