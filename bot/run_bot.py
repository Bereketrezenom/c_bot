"""
Simple standalone bot runner.
"""
import os
import asyncio
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from django.conf import settings

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# Firebase lazy import
firebase_service = None
"""In-memory selection of active case per counselor (telegram_id -> case_id)."""
counselor_active_case_selection = {}

# Simple main menu keyboard
MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🆕 New problem"), KeyboardButton("📋 My cases")],
        [KeyboardButton("🔀 Switch case"), KeyboardButton("❓ Help")],
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
    
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        f"Welcome to Counseling Bot!\n\n"
        f"Use the buttons below or commands:\n"
        f"`/problem <text>` - Submit a counseling request\n"
        f"`/cases` - View your cases\n"
        f"`/help` - Show help",
        parse_mode='Markdown',
        reply_markup=MAIN_MENU
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
            problem = (c.get('problem') or '')[:40]
            lines.append(f"{idx}. `{c.get('id','')[:12]}` - {problem}{marker}")
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
    user_label = f"{chosen.get('user_telegram_id')}"
    await update.message.reply_text(
        f"Switched to case `{chosen['id'][:12]}`. Your replies will go to the user.",
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
        "`/help` - Show this help"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=MAIN_MENU)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu keyboard again."""
    await update.message.reply_text("Main menu:", reply_markup=MAIN_MENU)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages - forward to counselor if user has active case."""
    if not update.message or not update.message.text:
        return
    
    text = (update.message.text or '').strip()
    user = update.effective_user
    service = get_firebase_service()
    user_data = service.get_user(user.id)

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

    # Button: Help
    if text == "❓ Help":
        await help_command(update, context)
        return

    # If the sender is a counselor/leader, forward to the selected/active user's chat
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
                counselor_cases = service.get_counselor_cases(str(user.id))
                active_cases = [c for c in (counselor_cases or []) if c.get('status') in ['assigned', 'active']]
                if not active_cases:
                    await update.message.reply_text("No active/assigned case to reply to.")
                    return
                # Pick the most recently updated/created case (ISO strings sort correctly)
                active_cases.sort(key=lambda c: (c.get('updated_at') or c.get('created_at') or ''), reverse=True)
                target_case = active_cases[0]
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
                await context.bot.send_message(
                    chat_id=int(target_case['user_telegram_id']),
                    text=f"👥 Counselor: {message_text}"
                )
                await update.message.reply_text("Message sent to the user.")
            except Exception as e:
                logger.error(f"Error forwarding to user: {e}")
                await update.message.reply_text("Error sending message to user.")
            return
        except Exception as e:
            logger.error(f"Counselor reply flow error: {e}")
            await update.message.reply_text("Error handling your message. Please try again.")
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
        await context.bot.send_message(
            chat_id=int(counselor_id),
            text=f"📩 Message from user:\n\n{message_text}\n\n---\nReply to this message to respond."
        )
        
        await update.message.reply_text(
            "Message sent to your counselor!",
            parse_mode='Markdown',
            reply_markup=MAIN_MENU
        )
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
    application.add_handler(CommandHandler("problem", problem_command))
    application.add_handler(CommandHandler("assign", assign_command))
    application.add_handler(CommandHandler("cases", cases_command))
    application.add_handler(CommandHandler("switch", switch_command))
    application.add_handler(CommandHandler("register_counselor", register_counselor_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == '__main__':
    main()

