import logging

logger = logging.getLogger(__name__)


def apply_ptb_py313_patch() -> None:
    """Temporary compatibility patch for python-telegram-bot on Python 3.13.

    Adds a missing slot to Updater if needed to avoid AttributeError.
    """
    try:
        from telegram.ext import _updater as _ptb_updater  # type: ignore
        Updater = getattr(_ptb_updater, 'Updater', None)
        if Updater is not None and hasattr(Updater, '__slots__'):
            slots = list(Updater.__slots__)
            needed = ['_Updater__polling_cleanup_cb']
            changed = False
            for name in needed:
                if name not in slots:
                    slots.append(name)
                    changed = True
            if changed:
                Updater.__slots__ = tuple(slots)
                logger.warning("Applied PTB Updater __slots__ patch for Python 3.13 compatibility")

        # Also patch Application slots in some PTB versions on Python 3.13
        try:
            from telegram.ext import _application as _ptb_application  # type: ignore
            ApplicationCls = getattr(_ptb_application, 'Application', None)
            if ApplicationCls is not None and hasattr(ApplicationCls, '__slots__'):
                app_slots = list(ApplicationCls.__slots__)
                app_needed = ['_Application__stop_running_marker']
                app_changed = False
                for name in app_needed:
                    if name not in app_slots:
                        app_slots.append(name)
                        app_changed = True
                if app_changed:
                    ApplicationCls.__slots__ = tuple(app_slots)
                    logger.warning("Applied PTB Application __slots__ patch for Python 3.13 compatibility")
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Skipping PTB compatibility patch: {e}")


def get_firebase_service():
    """Lazy import to get the Firebase service singleton."""
    try:
        from bot.firebase_service import get_firebase_service as get_fb_service
        return get_fb_service()
    except Exception as e:
        logger.error(f"Firebase initialization error: {e}")
        import traceback
        traceback.print_exc()
        return None


def build_case_label(service, counselor_id, case_dict):
    """Return a stable, human-friendly label like 'Case #1 [Alias]' for a case.
    Index is computed from counselor's assigned/active cases, newest first.
    Falls back to short id if not found.
    """
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


def build_case_tag(service, counselor_id, case_dict):
    """Return a compact hashtag like '#case1' for subtle tagging."""
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


