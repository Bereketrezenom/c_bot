"""
Telegram bot handlers for counseling service.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from django.conf import settings
from .firebase_service import firebase_service
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class CounselingBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler."""
        user = update.effective_user
        user_data = {
            'telegram_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
        }
        
        # Check if user exists
        existing_user = firebase_service.get_user(user.id)
        if not existing_user:
            firebase_service.create_user(user_data)
        
        # Check user role
        if existing_user:
            role = existing_user.get('role', 'user')
            if role == 'admin' or role == 'leader':
                await self.show_admin_menu(update)
                return
            elif role == 'counselor':
                await self.show_counselor_menu(update)
                return
        
        # Regular user menu
        keyboard = [
            [InlineKeyboardButton("📝 Send a Problem", callback_data='send_problem')],
            [InlineKeyboardButton("📋 My Cases", callback_data='my_cases')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = (
            f"Hello {user.first_name}! 👋\n\n"
            "Welcome to the Anonymous Counseling Bot.\n\n"
            "How it works:\n"
            "1. Send your problem\n"
            "2. A counselor will be assigned\n"
            "3. Chat anonymously with them\n\n"
            "Your privacy is protected! 🔒"
        )
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    
    async def show_admin_menu(self, update: Update):
        """Show admin menu with commands."""
        keyboard = [
            [InlineKeyboardButton("📊 View Pending Cases", callback_data='admin_pending')],
            [InlineKeyboardButton("📋 View All Cases", callback_data='admin_all_cases')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='admin_help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_menu = (
            "👨‍💼 **Admin Panel**\n\n"
            "Available Commands:\n"
            "`/assign <case_id> <counselor_id>` - Assign case to counselor\n"
            "`/cases` - View all cases\n"
            "`/close <case_id>` - Close a case\n"
            "`/help` - Show commands"
        )
        
        await update.message.reply_text(admin_menu, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_counselor_menu(self, update: Update):
        """Show counselor menu."""
        keyboard = [
            [InlineKeyboardButton("📋 My Cases", callback_data='counselor_cases')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        counselor_menu = (
            "👨‍⚕️ **Counselor Panel**\n\n"
            "Available Commands:\n"
            "`/cases` - View your assigned cases\n"
            "`/accept <case_id>` - Accept a case\n"
            "`/close <case_id>` - Close a case"
        )
        
        await update.message.reply_text(counselor_menu, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        user = query.from_user
        
        if callback_data == 'send_problem':
            await query.message.reply_text(
                "Please describe your problem or concern. We'll assign a counselor to help you.\n\n"
                "Type your message below:"
            )
            context.user_data['awaiting_problem'] = True
        
        elif callback_data == 'my_cases':
            await self.show_user_cases(query, user.id)
        
        elif callback_data == 'about':
            await query.message.reply_text(
                "🤖 Anonymous Counseling Bot\n\n"
                "This bot provides anonymous counseling services. Your privacy is our priority.\n\n"
                "• All conversations are anonymous\n"
                "• Cases are assigned by counseling leaders\n"
                "• Messages are securely stored\n"
                "• Your identity is protected\n\n"
                "Need help? Send a problem to get started!"
            )
        
        elif callback_data.startswith('case_'):
            case_id = callback_data.split('_')[1]
            await self.view_case_details(query, case_id)
        
        elif callback_data.startswith('assign_'):
            parts = callback_data.split('_')
            case_id = parts[1]
            if len(parts) > 2:
                counselor_id = parts[2]
                await self.assign_case(case_id, counselor_id, query.from_user.id)
                await query.edit_message_text(f"✅ Case assigned successfully!")
            else:
                await self.show_assignment_options(query, case_id)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages."""
        user = update.effective_user
        message_text = update.message.text
        
        # Check if user is awaiting problem submission
        if context.user_data.get('awaiting_problem'):
            case_id = await self.create_new_case(user.id, message_text)
            await update.message.reply_text(
                f"✅ Your case has been submitted!\n\n"
                f"Case ID: {case_id[:8]}\n\n"
                "A counseling leader will assign a counselor to your case. "
                "You'll be notified when someone responds.\n\n"
                "Use /start to return to the menu."
            )
            context.user_data['awaiting_problem'] = False
            
            # Notify leaders about new case
            await self.notify_leaders_about_new_case(case_id, message_text)
        
        # Check if user has active cases
        else:
            user_cases = firebase_service.get_user_cases(user.id)
            active_cases = [c for c in user_cases if c['status'] == 'active']
            
            if active_cases:
                # Forward message to counselor
                for case in active_cases:
                    if case['assigned_counselor_id']:
                        await self.send_message_to_counselor(case, user, message_text)
            else:
                await update.message.reply_text(
                    "Please use /start to begin a new conversation or select an option from the menu."
                )
    
    async def create_new_case(self, user_id, problem):
        """Create a new counseling case."""
        case_data = {
            'user_telegram_id': user_id,
            'problem': problem
        }
        case_id = firebase_service.create_case(case_data)
        return case_id
    
    async def show_user_cases(self, query, user_id):
        """Show user's cases."""
        cases = firebase_service.get_user_cases(user_id)
        
        if not cases:
            await query.message.reply_text("You don't have any cases yet.")
            return
        
        message = "📋 Your Cases:\n\n"
        for case in cases[:5]:  # Show last 5 cases
            status_emoji = {
                'pending': '⏳',
                'assigned': '👤',
                'active': '💬',
                'closed': '✅'
            }
            message += (
                f"{status_emoji.get(case['status'], '📄')} "
                f"Case ID: {case['id'][:8]}\n"
                f"Status: {case['status'].capitalize()}\n"
                f"Problem: {case['problem'][:50]}...\n\n"
            )
        
        await query.message.reply_text(message)
    
    async def view_case_details(self, query, case_id):
        """View details of a specific case."""
        case = firebase_service.get_case(case_id)
        if not case:
            await query.message.reply_text("Case not found.")
            return
        
        message = f"Case Details:\n\n"
        message += f"Status: {case['status']}\n"
        message += f"Problem: {case['problem']}\n\n"
        message += f"Messages: {len(case.get('messages', []))}\n"
        
        await query.message.reply_text(message)
    
    async def notify_leaders_about_new_case(self, case_id, problem):
        """Notify counseling leaders about a new case."""
        leaders = firebase_service.get_all_users_by_role('leader')
        
        for leader in leaders:
            try:
                keyboard = [[InlineKeyboardButton(
                    f"Assign Counselor - Case {case_id[:8]}",
                    callback_data=f'assign_{case_id}'
                )]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = (
                    f"🆕 New Counseling Case!\n\n"
                    f"Case ID: {case_id[:8]}\n"
                    f"Problem: {problem[:100]}...\n\n"
                    "Please assign a counselor."
                )
                
                await self.application.bot.send_message(
                    chat_id=leader['telegram_id'],
                    text=message,
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Error notifying leader {leader['telegram_id']}: {e}")
    
    async def show_assignment_options(self, query, case_id):
        """Show available counselors for assignment."""
        counselors = firebase_service.get_all_users_by_role('counselor')
        
        if not counselors:
            await query.message.reply_text("No counselors available.")
            return
        
        keyboard = []
        for counselor in counselors:
            keyboard.append([InlineKeyboardButton(
                f"👤 {counselor.get('first_name', 'Counselor')}",
                callback_data=f'assign_{case_id}_{counselor["telegram_id"]}'
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "Select a counselor to assign:",
            reply_markup=reply_markup
        )
    
    async def assign_case(self, case_id, counselor_id, leader_id):
        """Assign a case to a counselor."""
        firebase_service.assign_case(case_id, counselor_id, leader_id)
        
        # Notify counselor
        counselor = firebase_service.get_user(counselor_id)
        case = firebase_service.get_case(case_id)
        
        try:
            await self.application.bot.send_message(
                chat_id=counselor_id,
                text=(
                    f"📋 New Case Assigned!\n\n"
                    f"Case ID: {case_id[:8]}\n"
                    f"Problem: {case['problem']}\n\n"
                    f"Please start the conversation."
                )
            )
        except Exception as e:
            logger.error(f"Error notifying counselor {counselor_id}: {e}")
    
    async def send_message_to_counselor(self, case, user, message_text):
        """Send user message to assigned counselor."""
        counselor_id = case['assigned_counselor_id']
        
        # Add message to case in Firestore
        firebase_service.add_message_to_case(case['id'], {
            'sender_role': 'user',
            'sender_telegram_id': user.id,
            'message': message_text
        })
        
        try:
            await self.application.bot.send_message(
                chat_id=counselor_id,
                text=(
                    f"💬 New message from User (Anonymous)\n"
                    f"Case ID: {case['id'][:8]}\n\n"
                    f"{message_text}"
                )
            )
        except Exception as e:
            logger.error(f"Error sending message to counselor {counselor_id}: {e}")
    
    async def assign_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command: /assign <case_id> <counselor_id>"""
        user = update.effective_user
        user_data = firebase_service.get_user(user.id)
        
        if not user_data or user_data.get('role') not in ['admin', 'leader']:
            await update.message.reply_text("❌ Only admins can assign cases.")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: `/assign <case_id> <counselor_id>`\n"
                "Example: `/assign 123 456789`",
                parse_mode='Markdown'
            )
            return
        
        case_id = context.args[0]
        counselor_id = context.args[1]
        
        try:
            case = firebase_service.get_case(case_id)
            if not case:
                await update.message.reply_text(f"❌ Case {case_id} not found.")
                return
            
            # Assign case
            firebase_service.assign_case(case_id, counselor_id, user.id)
            
            # Notify counselor
            await self.application.bot.send_message(
                chat_id=int(counselor_id),
                text=(
                    f"📋 **New Case Assigned!**\n\n"
                    f"Case ID: {case_id[:8]}\n"
                    f"Problem: {case['problem'][:100]}...\n\n"
                    f"Start chatting with `/chat {case_id}`"
                ),
                parse_mode='Markdown'
            )
            
            await update.message.reply_text(f"✅ Case {case_id} assigned to counselor!")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cases_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View cases command."""
        user = update.effective_user
        user_data = firebase_service.get_user(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ User not found.")
            return
        
        role = user_data.get('role', 'user')
        
        if role == 'user':
            cases = firebase_service.get_user_cases(user.id)
            message = "📋 **Your Cases:**\n\n"
            for case in cases[:5]:
                status = case.get('status', 'pending')
                message += f"{status_emoji(status)} Case {case['id'][:8]}\nStatus: {status}\n\n"
            
        elif role in ['admin', 'leader']:
            cases = []
            for doc in firebase_service.db.collection('cases').stream():
                case_data = doc.to_dict()
                case_data['id'] = doc.id
                cases.append(case_data)
            
            pending = [c for c in cases if c.get('status') == 'pending']
            message = f"📊 **All Cases ({len(cases)} total)**\n"
            message += f"Pending: {len(pending)}\n\n"
            
            for case in pending[:5]:
                message += f"`{case['id'][:8]}` - {case['problem'][:50]}...\n"
        
        else:  # counselor
            cases = firebase_service.get_counselor_cases(user.id)
            message = "📋 **Your Assigned Cases:**\n\n"
            for case in cases[:5]:
                message += f"`{case['id'][:8]}` - {case['problem'][:50]}...\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    def status_emoji(status):
        emojis = {'pending': '⏳', 'assigned': '👤', 'active': '💬', 'closed': '✅'}
        return emojis.get(status, '📄')
    
    def setup_handlers(self):
        """Setup all bot handlers."""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("assign", self.assign_command))
        self.application.add_handler(CommandHandler("cases", self.cases_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def run(self):
        """Run the bot."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set in environment variables!")
            return
        
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        logger.info("Bot is running...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

