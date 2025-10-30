import logging
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .utils import get_firebase_service


logger = logging.getLogger(__name__)


async def pending_cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admins/leaders: list pending cases with Assign buttons."""
    service = get_firebase_service()
    user = update.effective_user
    me = service.get_user(user.id)
    if not me or me.get('role') not in ['admin', 'leader']:
        await update.message.reply_text("❌ Only admins can view pending cases.")
        return

    # Fetch pending cases (latest 10)
    all_cases: List[dict] = []
    for doc in service.db.collection('cases').stream():
        d = doc.to_dict()
        d['id'] = doc.id
        if d.get('status') == 'pending':
            all_cases.append(d)
    all_cases.sort(key=lambda c: (c.get('created_at') or ''), reverse=True)
    pending = all_cases[:10]

    if not pending:
        await update.message.reply_text("✅ No pending cases.")
        return

    for case in pending:
        text = (
            f"🆕 Pending Case `{case['id'][:8]}`\n"
            f"{(case.get('problem') or '')[:140]}"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Assign", callback_data=f"adm_assign:{case['id']}")]]
        )
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin inline assignment callbacks.

    adm_assign:<case_id> -> show counselors
    adm_pick:<case_id>:<counselor_id> -> assign
    """
    query = update.callback_query
    await query.answer()
    data = query.data or ''
    service = get_firebase_service()
    user = query.from_user
    me = service.get_user(user.id)
    if not me or me.get('role') not in ['admin', 'leader']:
        await query.edit_message_text("❌ Only admins can assign cases.")
        return

    try:
        if data.startswith('adm_assign:'):
            case_id = data.split(':', 1)[1]
            counselors = service.get_all_users_by_role('counselor') or []
            if not counselors:
                await query.edit_message_text("No counselors available.")
                return
            rows = []
            for c in counselors[:30]:
                label = c.get('first_name') or str(c.get('telegram_id'))
                rows.append([InlineKeyboardButton(label, callback_data=f"adm_pick:{case_id}:{c['telegram_id']}")])
            await query.edit_message_text(
                f"Select a counselor for `{case_id[:8]}`:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(rows)
            )
            return

        if data.startswith('adm_pick:'):
            _, case_id, counselor_id = data.split(':', 2)
            service.assign_case(case_id, counselor_id, user.id)
            # Notify counselor
            try:
                await context.bot.send_message(
                    chat_id=int(counselor_id),
                    text=(
                        f"📋 New Case Assigned!\n\n"
                        f"Case: {case_id[:8]}"
                    )
                )
            except Exception as e:
                logger.warning(f"Notify counselor failed: {e}")
            await query.edit_message_text(f"✅ Assigned case `{case_id[:8]}` to {counselor_id}", parse_mode='Markdown')
            return
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        await query.edit_message_text(f"❌ Error: {e}")


