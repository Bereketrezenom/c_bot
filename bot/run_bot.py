"""
Simple standalone bot runner.
"""
import os
import asyncio
import re
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from django.conf import settings

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# Temporary compatibility patch for python-telegram-bot on Python 3.13
def _patch_ptb_slots_for_py313():
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
    except Exception as e:
        logger.warning(f"Skipping PTB compatibility patch: {e}")


_patch_ptb_slots_for_py313()

# Firebase lazy import
firebase_service = None
"""In-memory selection of active case per counselor (telegram_id -> case_id)."""
counselor_active_case_selection = {}

# Simple main menu keyboard
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🆕 New problem"), KeyboardButton("📋 My cases")],
        [KeyboardButton("🔀 Switch case"), KeyboardButton("🔒 End chat")],
        [KeyboardButton("❓ Help")],
    ],
    resize_keyboard=True
)

# Helpers
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
    """Return a compact, stable hashtag. Always includes a short id suffix to avoid ambiguity.
    Example: '#case1-abc' or '#case-abc' if index can't be determined.
    """
    short = (case_dict.get('id', '')[:3] or '').lower()
    try:
        cases = service.get_counselor_cases(str(counselor_id)) or []
        active = [c for c in cases if c.get('status') in ['assigned', 'active']]
        # Use created_at primarily for stability; fallback to updated_at
        active.sort(key=lambda c: (c.get('created_at') or c.get('updated_at') or ''), reverse=True)
        idx = next((i for i, c in enumerate(active) if c.get('id') == case_dict.get('id')), None)
        if idx is not None:
            return f"#case{idx + 1}-{short}"
    except Exception:
        pass
    return f"#case-{short}"


def build_switch_keyboard(service, counselor_id, case_dict):
    """If counselor has exactly 2 active cases, suggest switching to the OTHER one.
    Returns an InlineKeyboardMarkup or None.
    """
    try:
        cases = service.get_counselor_cases(str(counselor_id)) or []
        active = [c for c in cases if c.get('status') in ['assigned', 'active']]
        active.sort(
            key=lambda c: (c.get('created_at') or c.get('updated_at') or ''),
            reverse=True,
        )
        if len(active) == 2:
            other = active[0] if active[1].get('id') == case_dict.get('id') else active[1]
            tag = build_case_tag(service, counselor_id, other)
            return InlineKeyboardMarkup(
                [[InlineKeyboardButton(text=f"Switch to {tag}", callback_data=f"switch:{other.get('id')}")]]
            )
    except Exception:
        pass
    return None

# Counselor-only keyboard
COUNSELOR_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔀 Switch case"), KeyboardButton("📋 My cases")],
        [KeyboardButton("📝 Set name"), KeyboardButton("🔒 End chat")],
        [KeyboardButton("❓ Help")],
    ],
    resize_keyboard=True
)
def get_firebase_service():
    global firebase_service
    if firebase_service is None:
        try:
            from bot.firebase_service import get_firebase_service as get_fb_service
            firebase_service = get_fb_service()
        except Exception as e:
            logger.error(f"Firebase initialization error: {e}")
            import traceback
            traceback.print_exc()
            return None
    return firebase_service


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
    role_kb = MAIN_MENU
    try:
        existing = service.get_user(user.id)
        if existing and existing.get('role') in ['counselor', 'leader']:
            role_kb = COUNSELOR_MENU
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
    existing_case = user_cases[0] if user_cases and any(c.get('status') in ['pending', 'assigned', 'active'] for c in user_cases) else None
    
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
                    await context.bot.send_message(
                        chat_id=admin['telegram_id'],
                        text=f"New Case: {case_id[:8]}\n\n{problem_text}\n\nUse `/assign {case_id} <counselor_id>`"
                    )
                except:
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
            message += f"`{case['id'][:12]}` - {case['problem'][:50]}...\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    else:
        cases = service.get_user_cases(user.id)
        if not cases:
            await update.message.reply_text("No cases yet. Use `/problem <text>` to create one.", parse_mode='Markdown')
            return
        
        message = f"📋 Your Cases ({len(cases)})\n\n"
        for case in cases[:5]:
            message += f"`{case['id'][:12]}` - {case['status']}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')


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
    # Stable order: newest first
    active_cases.sort(key=lambda c: (c.get('updated_at') or c.get('created_at') or ''), reverse=True)

    if not context.args:
        if not active_cases:
            await update.message.reply_text("You have no assigned/active cases.")
            return
        current = counselor_active_case_selection.get(user.id)
        lines = ["Your assigned cases (newest first):\n"]
        for idx, c in enumerate(active_cases, start=1):
            marker = " (current)" if current and current == c.get('id') else ""
            user_info = f"{c.get('user_telegram_id')}"
            alias = c.get('alias')
            alias_lbl = f"[{alias}] " if alias else ""
            problem = (c.get('problem') or '')[:40]
            lines.append(f"{idx}. `{c.get('id','')[:12]}` - {alias_lbl}{problem}{marker}")
        lines.append("\nReply with `/switch <index>` or `/switch <case_id>`. ")
        await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
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
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "**Counseling Bot Help**\n\n"
        "**Commands:**\n"
        "`/start` - Start the bot\n"
        "`/problem <text>` - Submit a counseling request\n"
        "`/cases` - View your cases\n"
        "`/register_counselor <passcode>` - Register as counselor\n"
        "`/assign <case_id> <counselor_id>` - Assign case (admin)\n"
        "`/close <case_id>` - Close case\n"
        "`/switch [index|case_id]` - Counselors: choose which user to reply to\n"
        "`/setname [case_id] <alias>` - Counselors: label a case with a name\n"
        "`/rename [case_id] <alias>` - Same as /setname (rename alias)\n"
        "`/clearname [case_id]` - Remove alias from a case\n"
        "`/end` - Counselors: clear current case selection\n"
        "`/help` - Show this help"
    )
    # Show role-aware keyboard
    service = get_firebase_service()
    user = update.effective_user
    kb = MAIN_MENU
    try:
        existing = service.get_user(user.id)
        if existing and existing.get('role') in ['counselor', 'leader']:
            kb = COUNSELOR_MENU
    except Exception:
        pass
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=kb)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu keyboard again."""
    service = get_firebase_service()
    user = update.effective_user
    kb = MAIN_MENU
    try:
        existing = service.get_user(user.id)
        if existing and existing.get('role') in ['counselor', 'leader']:
            kb = COUNSELOR_MENU
    except Exception:
        pass
    await update.message.reply_text("Main menu:", reply_markup=kb)


async def switch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline 'Switch to #case' buttons."""
    query = update.callback_query
    if not query or not query.data or not query.data.startswith('switch:'):
        return
    case_id = query.data.split(':', 1)[1]
    await query.answer()
    service = get_firebase_service()
    user = update.effective_user
    try:
        user_data = service.get_user(user.id)
        if not user_data or user_data.get('role') not in ['counselor', 'leader']:
            await query.message.reply_text("Only counselors can switch cases.")
            return
        case = service.get_case(case_id)
        if not case or str(case.get('assigned_counselor_id')) != str(user.id):
            await query.message.reply_text("Case not found in your assignments.")
            return
        counselor_active_case_selection[user.id] = case_id
        await query.message.reply_text(
            f"Switched to {build_case_label(service, user.id, case)}. Your replies will go to the user.",
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.message.reply_text(f"Error switching: {e}")


async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear counselor's current case selection."""
    user = update.effective_user
    counselor_active_case_selection.pop(user.id, None)
    await update.message.reply_text("Ended chat session. Use /switch to choose a case.", reply_markup=MAIN_MENU)


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
        await update.message.reply_text(f"Alias set for case {case_id[:8]}: [{alias}]", reply_markup=MAIN_MENU)
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
        await update.message.reply_text(f"Alias removed for case {case_id[:8]}", reply_markup=MAIN_MENU)
    except Exception as e:
        await update.message.reply_text(f"Error removing alias: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages - forward to counselor if user has active case."""
    if not update.message or not update.message.text:
        return
    
    text = (update.message.text or '').strip()
    user = update.effective_user
    service = get_firebase_service()
    user_data = service.get_user(user.id)

    # Defensive: handle common slash commands here in case CommandHandlers miss them
    if text.startswith('/switch'):
        parts = text.split(maxsplit=1)
        context.args = parts[1:].pop(0).split() if len(parts) > 1 else []
        await switch_command(update, context)
        return
    if text.startswith('/cases'):
        context.args = []
        await cases_command(update, context)
        return
    if text.startswith('/menu'):
        await menu_command(update, context)
        return
    if text.startswith('/end'):
        await end_command(update, context)
        return
    # Quick command: /case1 or /case2-xxx → switch by index
    m = re.match(r"^/case(\d+)(?:-[A-Za-z0-9]+)?$", text)
    if m:
        index = int(m.group(1)) - 1
        cases = service.get_counselor_cases(str(user.id)) or []
        active = [c for c in cases if c.get('status') in ['assigned', 'active']]
        active.sort(key=lambda c: (c.get('created_at') or c.get('updated_at') or ''), reverse=True)
        if 0 <= index < len(active):
            chosen = active[index]
            counselor_active_case_selection[user.id] = chosen['id']
            await update.message.reply_text(
                f"Switched to {build_case_label(service, user.id, chosen)}. Your replies will go to the user.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("Index out of range.")
        return
    if text.startswith('/setname'):
        # Let the defensive router handle it
        parts = text.split(maxsplit=1)
        context.args = parts[1:].pop(0).split() if len(parts) > 1 else []
        await setname_command(update, context)
        return
    if text.startswith('/rename'):
        parts = text.split(maxsplit=1)
        context.args = parts[1:].pop(0).split() if len(parts) > 1 else []
        await rename_command(update, context)
        return
    if text.startswith('/clearname'):
        parts = text.split(maxsplit=1)
        context.args = parts[1:].pop(0).split() if len(parts) > 1 else []
        await clearname_command(update, context)
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
            existing_case = user_cases[0] if user_cases and any(c.get('status') in ['pending', 'assigned', 'active'] for c in user_cases) else None
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
                            await context.bot.send_message(
                                chat_id=admin['telegram_id'],
                                text=f"New Case: {case_id[:8]}\n\n{problem_text}\n\nUse `/assign {case_id} <counselor_id>`"
                            )
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Error notifying admins: {e}")
                await update.message.reply_text(
                    f"Case created!\n\nID: `{case_id[:12]}`\n\nNow just send regular messages - they'll go to your counselor once assigned.",
                    parse_mode='Markdown',
                    reply_markup=MAIN_MENU
                )
        except Exception as e:
            logger.error(f"Error creating case from button: {e}")
            await update.message.reply_text("Error creating your case. Please try again.", reply_markup=MAIN_MENU)
        return

    # Button: My cases
    if text == "📋 My cases":
        context.args = []
        await cases_command(update, context)
        return

    # Button: Switch case
    if text == "🔀 Switch case":
        context.args = []
        await switch_command(update, context)
        return

    # Button: End chat
    if text == "🔒 End chat":
        await end_command(update, context)
        return

    # Button: Help
    if text == "❓ Help":
        await help_command(update, context)
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
                await update.message.reply_text(
                    "You have no current case selected. Use /switch to choose one.",
                    reply_markup=MAIN_MENU
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
                    kb = build_switch_keyboard(service, user.id, target_case)
                    if kb:
                        await update.message.reply_text(
                            f"_{build_case_tag(service, user.id, target_case)}_",
                            parse_mode='Markdown',
                            reply_markup=kb
                        )
                    else:
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
            await update.message.reply_text("No current case selected. Use /switch or /setname <case_id> <alias>.", reply_markup=COUNSELOR_MENU if (user_data and user_data.get('role') in ['counselor','leader']) else MAIN_MENU)
            return
        service.db.collection('cases').document(selected_case_id).update({
            'alias': text,
            'updated_at': datetime.now().isoformat()
        })
        await update.message.reply_text(f"Alias set for case {selected_case_id[:8]}: [{text}]", reply_markup=COUNSELOR_MENU)
        return

    # Check if user has an active case
    user_cases = service.get_user_cases(user.id)
    case = user_cases[0] if user_cases and any(c.get('status') in ['pending', 'assigned', 'active'] for c in user_cases) else None
    
    if not case:
        # No case - suggest button
        await update.message.reply_text(
            "Tap '🆕 New problem' below to submit your issue, or use `/problem <your issue>`.",
            parse_mode='Markdown',
            reply_markup=MAIN_MENU
        )
        return
    
    # Check if case has a counselor assigned
    counselor_id = case.get('assigned_counselor_id')
    
    if not counselor_id:
        # No counselor assigned yet
        await update.message.reply_text(
            "Your case is waiting for a counselor to be assigned. Please wait.",
            parse_mode='Markdown',
            reply_markup=MAIN_MENU
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
        kb = build_switch_keyboard(service, counselor_id, case)
        if kb:
            await context.bot.send_message(
                chat_id=int(counselor_id),
                text=(
                    f"📩 Message from user {user.first_name or ''} ({user.id}):\n\n{message_text}\n\n_{build_case_tag(service, counselor_id, case)}_"
                ),
                parse_mode='Markdown',
                reply_markup=kb
            )
        else:
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


def main():
    """Main function to run the bot."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    logger.info("Creating application...")
    application = Application.builder().token(token).build()
    
    # Add handlers
    logger.info("Adding handlers...")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("end", end_command))
    application.add_handler(CommandHandler("setname", setname_command))
    application.add_handler(CommandHandler("rename", rename_command))
    application.add_handler(CommandHandler("clearname", clearname_command))
    application.add_handler(CommandHandler("problem", problem_command))
    application.add_handler(CommandHandler("assign", assign_command))
    application.add_handler(CommandHandler("cases", cases_command))
    application.add_handler(CommandHandler("switch", switch_command))
    application.add_handler(CommandHandler("register_counselor", register_counselor_command))
    application.add_handler(CommandHandler("help", help_command))
    # Inline switch button
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(switch_callback, pattern=r'^switch:'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == '__main__':
    main()

