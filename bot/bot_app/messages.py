import logging
from datetime import datetime

from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.ui.keyboards import build_main_menu, build_counselor_menu
from .utils import get_firebase_service, build_case_tag
from .state import counselor_active_case_selection
from . import commands as cmd
from . import admin_features as adm


logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages - forward to counselor if user has active case."""
    if not update.message or not update.message.text:
        return

    text = (update.message.text or '').strip()
    user = update.effective_user
    service = get_firebase_service()
    user_data = service.get_user(user.id)

    # Defensive: route common slash commands in case CommandHandlers miss them
    if text.startswith('/switch'):
        parts = text.split(maxsplit=1)
        context.args = parts[1:].pop(0).split() if len(parts) > 1 else []
        await cmd.switch_command(update, context)
        return
    if text.startswith('/cases'):
        context.args = []
        await cmd.cases_command(update, context)
        return
    if text.startswith('/menu'):
        await cmd.menu_command(update, context)
        return
    if text.startswith('/end'):
        await cmd.end_command(update, context)
        return
    if text.startswith('/setname'):
        parts = text.split(maxsplit=1)
        context.args = parts[1:].pop(0).split() if len(parts) > 1 else []
        await cmd.setname_command(update, context)
        return
    if text.startswith('/rename'):
        parts = text.split(maxsplit=1)
        context.args = parts[1:].pop(0).split() if len(parts) > 1 else []
        await cmd.rename_command(update, context)
        return
    if text.startswith('/clearname'):
        parts = text.split(maxsplit=1)
        context.args = parts[1:].pop(0).split() if len(parts) > 1 else []
        await cmd.clearname_command(update, context)
        return

    # Button: New problem -> prompt for text
    if text == "🆕 New problem":
        context.user_data['awaiting_problem_text'] = True
        await update.message.reply_text(
            "Please describe your problem in one message.", reply_markup=ReplyKeyboardRemove()
        )
        return

    # If awaiting problem description, create the case
    if context.user_data.get('awaiting_problem_text'):
        problem_text = text
        context.user_data.pop('awaiting_problem_text', None)
        try:
            # Reuse logic from /problem without needing args
            user_cases = service.get_user_cases(user.id)
            active_cases = [c for c in user_cases if c.get('status') in ['pending', 'assigned', 'active']]
            existing_case = active_cases[0] if active_cases else None
            if existing_case:
                await update.message.reply_text(
                    "You already have an active case!\n\nTo view your case, tap '📋 My cases'.",
                )
            else:
                case_id = service.create_case({
                    'user_telegram_id': user.id,
                    'problem': problem_text
                })
                # Notify admins/leaders
                try:
                    admins = service.get_all_users_by_role('leader') or []
                    if not admins:
                        admins = service.get_all_users_by_role('admin') or []
                    for admin in admins:
                        try:
                            kb = InlineKeyboardMarkup(
                                [[InlineKeyboardButton("Assign", callback_data=f"adm_assign:{case_id}")]]
                            )
                            await context.bot.send_message(
                                chat_id=admin['telegram_id'],
                                text=(
                                    f"🆕 New Case `{case_id[:8]}`\n\n{problem_text}\n\n"
                                    f"Tap Assign to choose a counselor."
                                ),
                                parse_mode='Markdown',
                                reply_markup=kb,
                            )
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Error notifying admins: {e}")
                await update.message.reply_text(
                    f"Case created!\n\nID: `{case_id[:12]}`\n\nNow just send regular messages - they'll go to your counselor once assigned.",
                    parse_mode='Markdown',
                    reply_markup=build_main_menu()
                )
        except Exception as e:
            logger.error(f"Error creating case from button: {e}")
            await update.message.reply_text("Error creating your case. Please try again.", reply_markup=build_main_menu())
        return

    # Button: My cases
    if text == "📋 My cases":
        context.args = []
        await cmd.cases_command(update, context)
        return

    # Button: Switch case
    if text == "🔀 Switch case":
        context.args = []
        await cmd.switch_command(update, context)
        return

    # Admin-only buttons
    if text == "📊 All cases":
        await cmd.admin_list_all_cases_command(update, context)
        return
    if text == "🕓 Pending":
        await adm.pending_cases_command(update, context)
        return

    # Button: Done
    if text == "✅ Done":
        await cmd.done_case_command(update, context)
        return

    # Button: End chat
    if text == "🔒 End chat":
        await cmd.end_command(update, context)
        return

    # Button: Help
    if text == "❓ Help":
        await cmd.help_command(update, context)
        return

    # Button: Set name (counselors)
    if text == "📝 Set name":
        context.user_data['awaiting_alias'] = True
        await update.message.reply_text("Send the new alias for the current case (or use /setname <case_id> <alias>).", reply_markup=ReplyKeyboardRemove())
        return

    # If the sender is a counselor/leader, forward to the selected user's chat (no auto-fallback)
    role = user_data.get('role') if user_data else None
    if role in ['counselor', 'leader']:
        try:
            target_case = None
            selected_case_id = counselor_active_case_selection.get(user.id)
            if selected_case_id:
                fetched_case = service.get_case(selected_case_id)
                if fetched_case and str(fetched_case.get('assigned_counselor_id')) == str(user.id) and fetched_case.get('status') in ['assigned', 'active']:
                    target_case = fetched_case
                else:
                    counselor_active_case_selection.pop(user.id, None)

            if target_case is None:
                # Show counselor menu (avoid 'New problem' for counselors)
                await update.message.reply_text(
                    "You have no current case selected. Use /switch to choose one.",
                    reply_markup=build_counselor_menu()
                )
                return
            message_text = update.message.text

            # Save message
            try:
                service.add_message_to_case(target_case['id'], {
                    'sender_role': 'counselor',
                    'sender_telegram_id': user.id,
                    'message': message_text
                })
            except Exception as e:
                logger.error(f"Error saving counselor message: {e}")

            # Forward to the user
            try:
                # Send clean message to the user (no case tag)
                await context.bot.send_message(
                    chat_id=int(target_case['user_telegram_id']),
                    text=f"👥 Counselor: {message_text}"
                )
                # Add a small inline-style tag right under counselor's own message
                try:
                    await update.message.reply_text(
                        f"_{build_case_tag(service, user.id, target_case)}_",
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error forwarding to user: {e}")
                await update.message.reply_text("Error sending message to user.")
            return
        except Exception as e:
            logger.error(f"Counselor reply flow error: {e}")
            await update.message.reply_text("Error handling your message. Please try again.")
            return

    # If counselor sent a message while waiting for alias, treat text as alias
    if context.user_data.get('awaiting_alias'):
        context.user_data.pop('awaiting_alias', None)
        # Apply alias to current selected case
        selected_case_id = counselor_active_case_selection.get(user.id)
        if not selected_case_id:
            await update.message.reply_text("No current case selected. Use /switch or /setname <case_id> <alias>.", reply_markup=build_counselor_menu() if (user_data and user_data.get('role') in ['counselor','leader']) else build_main_menu())
            return
        service.db.collection('cases').document(selected_case_id).update({
            'alias': text,
            'updated_at': datetime.now().isoformat()
        })
        await update.message.reply_text(f"Alias set for case {selected_case_id[:8]}: [{text}]", reply_markup=build_counselor_menu())
        return

    # Check if user has an active case
    user_cases = service.get_user_cases(user.id)
    case = user_cases[0] if user_cases and any(c.get('status') in ['pending', 'assigned', 'active'] for c in user_cases) else None

    if not case:
        # No case - suggest button
        await update.message.reply_text(
            "Tap '🆕 New problem' below to submit your issue, or use `/problem <your issue>`.",
            parse_mode='Markdown',
            reply_markup=build_main_menu()
        )
        return

    # Check if case has a counselor assigned
    counselor_id = case.get('assigned_counselor_id')

    if not counselor_id:
        # No counselor assigned yet
        await update.message.reply_text(
            "Your case is waiting for a counselor to be assigned. Please wait.",
            parse_mode='Markdown',
            reply_markup=build_main_menu()
        )
        return

    # Save message to case
    message_text = update.message.text

    try:
        service.add_message_to_case(case['id'], {
            'sender_role': 'user',
            'sender_telegram_id': user.id,
            'message': message_text
        })
    except Exception as e:
        logger.error(f"Error saving message: {e}")

    # Forward to counselor
    try:
        await context.bot.send_message(
            chat_id=int(counselor_id),
            text=(
                f"📩 Message from user {user.first_name or ''} ({user.id}):\n\n{message_text}\n\n_{build_case_tag(service, counselor_id, case)}_"
            ),
            parse_mode='Markdown'
        )
        # Suppress per-message confirmation to the user
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
        await update.message.reply_text("Error sending message. Please try again.")


