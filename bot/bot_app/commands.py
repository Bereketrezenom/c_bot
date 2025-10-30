import logging
import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.ui.keyboards import build_main_menu, build_counselor_menu, build_admin_menu
from .utils import get_firebase_service, build_case_label
from .state import counselor_active_case_selection


logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    service = get_firebase_service()

    # Create user if needed
    if not service.get_user(user.id):
        service.create_user({
            'telegram_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'role': 'user'
        })

    # Pick keyboard per role
    role_kb = build_main_menu()
    try:
        existing = service.get_user(user.id)
        if existing:
            if existing.get('role') in ['admin', 'leader']:
                role_kb = build_admin_menu()
            elif existing.get('role') == 'counselor':
                role_kb = build_counselor_menu()
    except Exception:
        pass

    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        f"Welcome to Counseling Bot!\n\n"
        f"Use the buttons below or commands:\n"
        f"`/problem <text>` - Submit a counseling request\n"
        f"`/cases` - View your cases\n"
        f"`/help` - Show help",
        parse_mode='Markdown',
        reply_markup=role_kb
    )


async def problem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /problem command - creates case only if user doesn't have one."""
    if not context.args:
        await update.message.reply_text("Please describe your problem:\n`/problem I feel anxious`", parse_mode='Markdown')
        return

    user = update.effective_user
    service = get_firebase_service()
    problem_text = ' '.join(context.args)

    # Check if user already has a case
    user_cases = service.get_user_cases(user.id)
    active_cases = [c for c in user_cases if c.get('status') in ['pending', 'assigned', 'active']]
    existing_case = active_cases[0] if active_cases else None

    if existing_case:
        # User already has a case - just send them a message
        await update.message.reply_text(
            f"You already have an active case!\n\n"
            f"To chat with your counselor, just send regular messages.\n\n"
            f"To view your case: `/cases`",
            parse_mode='Markdown'
        )
    else:
        # Create new case
        case_id = service.create_case({
            'user_telegram_id': user.id,
            'problem': problem_text
        })

        # Notify admins
        try:
            admins = service.get_all_users_by_role('leader')
            if not admins:
                admins = service.get_all_users_by_role('admin')

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
            f"Case created!\n\n"
            f"ID: `{case_id[:12]}`\n\n"
            f"Now just send regular messages - they'll go to your counselor once assigned.",
            parse_mode='Markdown'
        )


async def assign_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /assign command (admin only)."""
    if len(context.args) != 2:
        await update.message.reply_text("Usage: `/assign <case_id> <counselor_id>`", parse_mode='Markdown')
        return

    user = update.effective_user
    service = get_firebase_service()
    user_data = service.get_user(user.id)

    if not user_data or user_data.get('role') not in ['admin', 'leader']:
        await update.message.reply_text("❌ Only admins can assign cases.")
        return

    case_id, counselor_id = context.args

    try:
        case = service.get_case(case_id)
        if not case:
            await update.message.reply_text("❌ Case not found.")
            return

        service.assign_case(case_id, counselor_id, user.id)

        # Notify counselor
        try:
            await context.bot.send_message(
                chat_id=int(counselor_id),
                text=f"📋 New Case Assigned!\n\nCase: {case_id[:8]}\nProblem: {case['problem'][:100]}"
            )
        except:
            pass

        await update.message.reply_text(f"✅ Case {case_id[:8]} assigned!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cases command."""
    user = update.effective_user
    service = get_firebase_service()
    user_data = service.get_user(user.id)
    role = user_data.get('role', 'user') if user_data else 'user'

    if role in ['admin', 'leader']:
        all_cases = []
        for doc in service.db.collection('cases').stream():
            case = doc.to_dict()
            case['id'] = doc.id
            all_cases.append(case)

        pending = [c for c in all_cases if c.get('status') == 'pending']
        message = f"📊 Cases: {len(all_cases)} total, {len(pending)} pending\n\n"
        for case in pending[:10]:
            message += f"`{case['id'][:12]}` - {case['problem'][:40]}...\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    elif role == 'counselor':
        cases = service.get_counselor_cases(str(user.id))
        if not cases:
            await update.message.reply_text("No cases assigned yet.")
            return

        message = f"📋 Your Cases ({len(cases)})\n\n"
        for case in cases:
            done_marker = " ✅" if case.get('done') else ""
            message += f"`{case['id'][:12]}` - {case['problem'][:50]}...{done_marker}\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    else:
        cases = service.get_user_cases(user.id)
        if not cases:
            await update.message.reply_text(
                "No cases yet. Use `/problem <text>` to create one.",
                parse_mode='Markdown',
                reply_markup=build_main_menu(),  # remove keyboard for normal users
            )
            return

        message = f"📋 Your Cases ({len(cases)})\n\n"
        for case in cases[:5]:
            status = case['status']
            if case.get('done'):
                status += " ✅"
            message += f"`{case['id'][:12]}` - {status}\n"

        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=build_main_menu())


async def admin_list_all_cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admins/leaders: list all cases with assigned counselor and user.

    Shows a compact list: ID, status, user first name, counselor first name (or Unassigned).
    """
    user = update.effective_user
    service = get_firebase_service()
    me = service.get_user(user.id)
    if not me or me.get('role') not in ['admin', 'leader']:
        await update.message.reply_text("❌ Only admins can view all cases.")
        return

    all_cases = []
    for doc in service.db.collection('cases').stream():
        c = doc.to_dict()
        c['id'] = doc.id
        all_cases.append(c)

    # Sort by created_at (oldest first for stable numbering)
    try:
        all_cases.sort(key=lambda c: (c.get('created_at') or c.get('updated_at') or ''))
    except Exception:
        pass

    lines = [f"📋 All Cases ({len(all_cases)})\n"]
    for c in all_cases[:50]:
        user_info = service.get_user(c.get('user_telegram_id')) or {}
        user_name = user_info.get('first_name') or str(c.get('user_telegram_id'))
        counselor_name = "Unassigned"
        if c.get('assigned_counselor_id'):
            counselor = service.get_user(c.get('assigned_counselor_id')) or {}
            counselor_name = counselor.get('first_name') or str(c.get('assigned_counselor_id'))
        status = c.get('status','?')
        if c.get('done'):
            status += " ✅"
        lines.append(
            f"`{c['id'][:10]}` - {status} | user: {user_name} | counselor: {counselor_name}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode='Markdown', reply_markup=build_admin_menu())


async def register_counselor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /register_counselor command with passcode."""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Please provide the passcode:\n`/register_counselor <passcode>`",
            parse_mode='Markdown'
        )
        return

    passcode = context.args[0]
    user = update.effective_user
    service = get_firebase_service()

    # Check passcode
    if passcode != "amucf123":
        await update.message.reply_text(
            "Invalid passcode. Access denied.",
            parse_mode='Markdown'
        )
        return

    # Register user as counselor
    try:
        # Check if user exists
        user_data = service.get_user(user.id)

        if user_data:
            # Update existing user to counselor
            service.db.collection('users').document(str(user.id)).update({
                'role': 'counselor',
                'updated_at': datetime.now().isoformat()
            })
        else:
            # Create new counselor
            service.create_user({
                'telegram_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'role': 'counselor'
            })

        await update.message.reply_text(
            f"Welcome {user.first_name}!\n\n"
            f"You are now registered as a COUNSELOR.\n\n"
            f"You will be notified when cases are assigned to you.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error registering counselor: {e}")
        await update.message.reply_text("Error during registration. Please try again.")


async def register_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register the current user as an admin using a passcode.
    Usage: /register_admin <passcode>
    The passcode can be set via env var ADMIN_PASSCODE (default: amucfadmin).
    """
    if not context.args:
        await update.message.reply_text(
            "Please provide the passcode:\n`/register_admin <passcode>`",
            parse_mode='Markdown'
        )
        return

    passcode = context.args[0]
    expected = os.environ.get('ADMIN_PASSCODE', 'amucfadmin')
    if passcode != expected:
        await update.message.reply_text("Invalid passcode. Access denied.")
        return

    service = get_firebase_service()
    user = update.effective_user
    try:
        user_doc = service.get_user(user.id)
        if user_doc:
            service.db.collection('users').document(str(user.id)).update({
                'role': 'admin',
                'updated_at': datetime.now().isoformat()
            })
        else:
            service.create_user({
                'telegram_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'role': 'admin'
            })
        await update.message.reply_text("✅ You are now registered as ADMIN. Use /pending or /assign.")
    except Exception as e:
        logger.error(f"Error registering admin: {e}")
        await update.message.reply_text("Error during admin registration. Please try again.")


async def switch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Counselors: list/select which user's case to chat with.
    Usage:
      /switch            -> list assigned/active cases
      /switch 1          -> pick by index from the list
      /switch <case_id>  -> pick by case id (or prefix)
    """
    user = update.effective_user
    service = get_firebase_service()
    user_data = service.get_user(user.id)
    if not user_data or user_data.get('role') not in ['counselor', 'leader']:
        await update.message.reply_text("Only counselors can use /switch.")
        return

    cases = service.get_counselor_cases(str(user.id)) or []
    active_cases = [c for c in cases if c.get('status') in ['assigned', 'active']]
    # Stable order: storage/creation order (oldest first)
    try:
        active_cases.sort(key=lambda c: (c.get('created_at') or c.get('updated_at') or ''))
    except Exception:
        pass

    if not context.args:
        if not active_cases:
            await update.message.reply_text("You have no assigned/active cases.")
            return
        # Ensure counselor keyboard is active (no user buttons)
        try:
            await update.message.reply_text("Switch case:", reply_markup=build_counselor_menu())
        except Exception:
            pass
        # Text list + inline buttons for all cases
        current = counselor_active_case_selection.get(user.id)
        lines = ["Your assigned cases (newest first):\n"]
        rows = []
        for idx, c in enumerate(active_cases, start=1):
            problem = (c.get('problem') or '')[:40]
            marker = " (current)" if current and current == c.get('id') else ""
            done_marker = " ✅" if c.get('done') else ""
            lines.append(f"{idx}. `{c.get('id','')[:12]}` - {problem}{done_marker}{marker}")
            btn_text = f"#{idx} {c.get('id','')[:8]}"
            rows.append([InlineKeyboardButton(btn_text, callback_data=f"sw_pick:{c['id']}")])
        await update.message.reply_text("\n".join(lines), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(rows[:50]))
        return

    # With argument -> select
    arg = context.args[0]
    chosen = None
    if arg.isdigit():
        i = int(arg) - 1
        if 0 <= i < len(active_cases):
            chosen = active_cases[i]
        else:
            await update.message.reply_text("Index out of range.")
            return
    else:
        # case id exact or prefix match
        for c in active_cases:
            cid = c.get('id', '')
            if cid == arg or cid.startswith(arg):
                chosen = c
                break
        if not chosen:
            await update.message.reply_text("Case not found for your assignments.")
            return

    counselor_active_case_selection[user.id] = chosen['id']
    case_label = build_case_label(service, user.id, chosen)
    await update.message.reply_text(
        f"Switched to {case_label}. Your replies will go to the user.",
        parse_mode='Markdown',
        reply_markup=build_counselor_menu()
    )


async def switch_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline callback: set current case for counselor."""
    query = update.callback_query
    await query.answer()
    data = query.data or ''
    if not data.startswith('sw_pick:'):
        return
    case_id = data.split(':', 1)[1]
    service = get_firebase_service()
    user = query.from_user
    # Validate case belongs to counselor
    c = service.get_case(case_id)
    if not c or str(c.get('assigned_counselor_id')) != str(user.id) or c.get('status') not in ['assigned','active']:
        await query.edit_message_text("Case not found in your assignments.")
        return
    counselor_active_case_selection[user.id] = case_id
    case_label = build_case_label(service, user.id, c)
    await query.edit_message_text(f"✅ Switched to {case_label}. Now your messages will reach the user.")
    # Also send a small message to refresh the reply keyboard
    try:
        await query.message.reply_text("Menu updated.", reply_markup=build_counselor_menu())
    except Exception:
        pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    service = get_firebase_service()
    user = update.effective_user
    role = 'user'
    try:
        existing = service.get_user(user.id)
        if existing:
            role = existing.get('role', 'user')
    except Exception:
        pass

    if role in ['admin', 'leader']:
        help_text = (
            "**Admin Help**\n\n"
            "`/cases` - View all cases\n"
            "`/assign <case_id> <counselor_id>` - Assign case\n"
            "`/cases_all` - List all cases with users and counselors\n"
            "`/pending` - List pending cases with Assign buttons\n"
            "`/register_admin <passcode>` - Become admin\n"
            "`/help` - Show this help"
        )
        kb = build_admin_menu()
    elif role == 'counselor':
        help_text = (
            "**Counselor Help**\n\n"
            "`/cases` - View your assigned cases\n"
            "`/switch [index|case_id]` - Choose which user to reply to\n"
            "`/setname [case_id] <alias>` / `/clearname [case_id]` - Manage case label\n"
            "`/end` - Close the current case\n"
            "`/help` - Show this help"
        )
        kb = build_counselor_menu()
    else:
        help_text = (
            "**Help**\n\n"
            "`/start` - Start the bot\n"
            "`/problem <text>` - Submit a counseling request\n"
            "`/cases` - View your cases\n"
            "`/help` - Show this help"
        )
        kb = build_main_menu()

    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=kb)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu keyboard again."""
    service = get_firebase_service()
    user = update.effective_user
    kb = build_main_menu()
    try:
        existing = service.get_user(user.id)
        if existing:
            if existing.get('role') in ['admin', 'leader']:
                kb = build_admin_menu()
            elif existing.get('role') == 'counselor':
                kb = build_counselor_menu()
    except Exception:
        pass
    await update.message.reply_text("Main menu:", reply_markup=kb)


async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Counselor ends a chat: close the current case and clear selection.

    - Only counselors/leaders can use it
    - Sets case.status = 'closed' and updated_at
    - Notifies the user that the case has been closed
    """
    user = update.effective_user
    service = get_firebase_service()
    u = service.get_user(user.id)
    if not u or u.get('role') not in ['counselor', 'leader']:
        await update.message.reply_text("This action is only for counselors.")
        return

    selected_case_id = counselor_active_case_selection.get(user.id)
    if not selected_case_id:
        await update.message.reply_text("No current case selected. Use /switch to choose one.", reply_markup=build_counselor_menu())
        return

    try:
        # Close case
        service.db.collection('cases').document(selected_case_id).update({
            'status': 'closed',
            'updated_at': datetime.now().isoformat()
        })
        case = service.get_case(selected_case_id)
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=int(case.get('user_telegram_id')),
                text=(
                    "Your counseling case has been closed. If you need more help, you can create a new case any time."
                )
            )
        except Exception:
            pass
    except Exception:
        pass

    counselor_active_case_selection.pop(user.id, None)
    await update.message.reply_text("✅ Case closed. Use /switch to choose another case.", reply_markup=build_counselor_menu())


async def done_case_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Counselor marks the current case as done (keeps conversation open)."""
    user = update.effective_user
    service = get_firebase_service()
    u = service.get_user(user.id)
    if not u or u.get('role') not in ['counselor', 'leader']:
        await update.message.reply_text("This action is only for counselors.")
        return

    selected_case_id = counselor_active_case_selection.get(user.id)
    if not selected_case_id:
        await update.message.reply_text("No current case selected. Use /switch to choose one.", reply_markup=build_counselor_menu())
        return

    try:
        service.db.collection('cases').document(selected_case_id).update({
            'done': True,
            'updated_at': datetime.now().isoformat()
        })
        await update.message.reply_text("✅ Marked as done. Conversation remains open.", reply_markup=build_counselor_menu())
    except Exception as e:
        await update.message.reply_text(f"Error marking done: {e}")


async def setname_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Counselors: set an alias/name for a case.
    Usage:
      /setname <alias>                 -> applies to currently selected case
      /setname <case_id> <alias>       -> applies to specified case (exact or prefix)
    """
    user = update.effective_user
    service = get_firebase_service()
    user_data = service.get_user(user.id)
    if not user_data or user_data.get('role') not in ['counselor', 'leader']:
        await update.message.reply_text("Only counselors can use /setname.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setname [case_id] <alias>")
        return

    case_id = None
    alias = None
    if len(context.args) == 1:
        alias = context.args[0]
        case_id = counselor_active_case_selection.get(user.id)
        if not case_id:
            await update.message.reply_text("No current case selected. Use /switch or pass a case id: /setname <case_id> <alias>.")
            return
    else:
        possible_id = context.args[0]
        alias = ' '.join(context.args[1:])
        # Resolve by exact/prefix among counselor's cases
        cases = service.get_counselor_cases(str(user.id)) or []
        target = None
        for c in cases:
            cid = c.get('id', '')
            if cid == possible_id or cid.startswith(possible_id):
                target = c
                break
        if not target:
            await update.message.reply_text("Case not found in your assignments.")
            return
        case_id = target['id']

    try:
        service.db.collection('cases').document(case_id).update({
            'alias': alias,
            'updated_at': datetime.now().isoformat()
        })
        await update.message.reply_text(f"Alias set for case {case_id[:8]}: [{alias}]", reply_markup=build_counselor_menu())
    except Exception as e:
        await update.message.reply_text(f"Error setting alias: {e}")


async def rename_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for /setname: rename the case alias using same rules."""
    await setname_command(update, context)


async def clearname_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove alias from a case. Usage:
      /clearname                 -> applies to current selected case
      /clearname <case_id>       -> applies to specified case (exact or prefix)
    """
    user = update.effective_user
    service = get_firebase_service()
    user_data = service.get_user(user.id)
    if not user_data or user_data.get('role') not in ['counselor', 'leader']:
        await update.message.reply_text("Only counselors can use /clearname.")
        return

    case_id = None
    if not context.args:
        case_id = counselor_active_case_selection.get(user.id)
        if not case_id:
            await update.message.reply_text("No current case selected. Use /switch or pass a case id: /clearname <case_id>.")
            return
    else:
        possible_id = context.args[0]
        cases = service.get_counselor_cases(str(user.id)) or []
        target = None
        for c in cases:
            cid = c.get('id', '')
            if cid == possible_id or cid.startswith(possible_id):
                target = c
                break
        if not target:
            await update.message.reply_text("Case not found in your assignments.")
            return
        case_id = target['id']

    try:
        service.db.collection('cases').document(case_id).update({
            'alias': None,
            'updated_at': datetime.now().isoformat()
        })
        await update.message.reply_text(f"Alias removed for case {case_id[:8]}", reply_markup=build_counselor_menu())
    except Exception as e:
        await update.message.reply_text(f"Error removing alias: {e}")


