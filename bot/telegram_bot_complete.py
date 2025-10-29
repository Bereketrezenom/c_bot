"""
Complete Telegram bot with all commands for counseling system.
"""
from telegram import Update
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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class CounselingBotComplete:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - detects role and shows appropriate menu."""
        user = update.effective_user
        
        # Create or get user
        if not firebase_service.get_user(user.id):
            firebase_service.create_user({
                'telegram_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'role': 'user'
            })
        
        user_data = firebase_service.get_user(user.id)
        role = user_data.get('role', 'user')
        
        if role in ['admin', 'leader']:
            await update.message.reply_text(
                f"👨‍💼 **Admin Panel**\n\n"
                f"Commands:\n"
                f"`/cases` - View all cases\n"
                f"`/assign <case_id> <counselor_telegram_id>` - Assign case\n"
                f"`/close <case_id>` - Close case\n"
                f"`/help` - Show all commands",
                parse_mode='Markdown'
            )
        elif role == 'counselor':
            await update.message.reply_text(
                f"👨‍⚕️ **Counselor Panel**\n\n"
                f"Commands:\n"
                f"`/cases` - View your assigned cases\n"
                f"`/help` - Show commands",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"Hello {user.first_name}! 👋\n\n"
                f"**Counseling Bot** - Anonymous Support\n\n"
                f"Commands:\n"
                f"`/problem` - Send a counseling request\n"
                f"`/cases` - View your cases\n"
                f"`/help` - Show help",
                parse_mode='Markdown'
            )
    
    async def assign_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin only: /assign <case_id> <counselor_telegram_id>"""
        user = update.effective_user
        user_data = firebase_service.get_user(user.id)
        
        if not user_data or user_data.get('role') not in ['admin', 'leader']:
            await update.message.reply_text("❌ Only admins can assign cases.")
            return
        
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ Usage: `/assign <case_id> <counselor_telegram_id>`\n"
                "Example: `/assign abc123def 123456789`",
                parse_mode='Markdown'
            )
            return
        
        case_id, counselor_id = context.args
        
        try:
            # Get case
            case = firebase_service.get_case(case_id)
            if not case:
                await update.message.reply_text(f"❌ Case not found.")
                return
            
            # Assign
            firebase_service.assign_case(case_id, counselor_id, user.id)
            
            # Notify counselor
            try:
                await self.application.bot.send_message(
                    chat_id=int(counselor_id),
                    text=(
                        f"📋 **New Case Assigned!**\n\n"
                        f"Case ID: `{case_id[:8]}`\n"
                        f"Problem: {case['problem']}\n\n"
                        f"Use `/reply {case_id}` to start the conversation."
                    ),
                    parse_mode='Markdown'
                )
            except:
                pass
            
            await update.message.reply_text(f"✅ Case assigned successfully!")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cases_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View cases based on role."""
        user = update.effective_user
        user_data = firebase_service.get_user(user.id)
        role = user_data.get('role', 'user')
        
        if role in ['admin', 'leader']:
            # Admin sees all cases
            all_cases = []
            for doc in firebase_service.db.collection('cases').order_by('created_at', direction='DESCENDING').stream():
                case = doc.to_dict()
                case['id'] = doc.id
                all_cases.append(case)
            
            pending = [c for c in all_cases if c.get('status') == 'pending']
            
            message = f"📊 **All Cases** ({len(all_cases)} total, {len(pending)} pending)\n\n"
            
            for case in pending[:10]:
                message += f"`{case['id'][:12]}` - {case['problem'][:40]}...\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        
        elif role == 'counselor':
            # Counselor sees assigned cases
            cases = firebase_service.get_counselor_cases(user.id)
            
            if not cases:
                await update.message.reply_text("No cases assigned yet.")
                return
            
            message = f"📋 **Your Cases** ({len(cases)})\n\n"
            for case in cases:
                status_emoji = {'pending': '⏳', 'assigned': '👤', 'active': '💬', 'closed': '✅'}
                message += f"{status_emoji.get(case['status'], '📄')} `{case['id'][:12]}`\n"
                message += f"{case['problem'][:50]}...\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
        
        else:
            # User sees their cases
            cases = firebase_service.get_user_cases(user.id)
            
            if not cases:
                await update.message.reply_text("You don't have any cases yet. Use `/problem` to create one.", parse_mode='Markdown')
                return
            
            message = f"📋 **Your Cases** ({len(cases)})\n\n"
            for case in cases:
                status_emoji = {'pending': '⏳', 'assigned': '👤', 'active': '💬', 'closed': '✅'}
                message += f"{status_emoji.get(case['status'], '📄')} Case `{case['id'][:12]}`\n"
                message += f"Status: {case['status']}\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
    
    async def problem_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User creates a new case."""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "Please describe your problem:\n"
                "Example: `/problem I feel anxious about upcoming exams`",
                parse_mode='Markdown'
            )
            return
        
        problem_text = ' '.join(context.args)
        
        # Create case
        case_id = firebase_service.create_case({
            'user_telegram_id': user.id,
            'problem': problem_text
        })
        
        # Notify admins
        admins = firebase_service.get_all_users_by_role('leader')
        if not admins:
            admins = firebase_service.get_all_users_by_role('admin')
        
        for admin in admins:
            try:
                await self.application.bot.send_message(
                    chat_id=admin['telegram_id'],
                    text=(
                        f"🆕 **New Counseling Case**\n\n"
                        f"Case ID: `{case_id[:12]}`\n"
                        f"Problem: {problem_text}\n\n"
                        f"Use `/assign {case_id} <counselor_id>` to assign a counselor."
                    ),
                    parse_mode='Markdown'
                )
            except:
                pass
        
        await update.message.reply_text(
            f"✅ Your case has been submitted!\n\n"
            f"Case ID: `{case_id[:12]}`\n"
            f"A counselor will be assigned soon.",
            parse_mode='Markdown'
        )
    
    async def close_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Close a case."""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "Usage: `/close <case_id>`\nExample: `/close abc123def`",
                parse_mode='Markdown'
            )
            return
        
        case_id = context.args[0]
        user_data = firebase_service.get_user(user.id)
        
        # Check permissions
        case = firebase_service.get_case(case_id)
        if not case:
            await update.message.reply_text("❌ Case not found.")
            return
        
        role = user_data.get('role', 'user')
        
        if role not in ['admin', 'leader', 'counselor']:
            await update.message.reply_text("❌ Only admins or counselors can close cases.")
            return
        
        # Close case
        firebase_service.close_case(case_id)
        
        await update.message.reply_text(f"✅ Case {case_id[:12]} closed successfully!")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help based on user role."""
        user = update.effective_user
        user_data = firebase_service.get_user(user.id)
        role = user_data.get('role', 'user')
        
        if role in ['admin', 'leader']:
            message = (
                "👨‍💼 **Admin Commands:**\n\n"
                "`/cases` - View all cases\n"
                "`/assign <case_id> <counselor_id>` - Assign case to counselor\n"
                "`/close <case_id>` - Close a case\n"
                "`/help` - Show this help"
            )
        elif role == 'counselor':
            message = (
                "👨‍⚕️ **Counselor Commands:**\n\n"
                "`/cases` - View your assigned cases\n"
                "`/close <case_id>` - Close a case\n"
                "`/help` - Show this help"
            )
        else:
            message = (
                "👤 **User Commands:**\n\n"
                "`/problem <description>` - Submit a counseling request\n"
                "`/cases` - View your cases\n"
                "`/help` - Show this help\n\n"
                "**How it works:**\n"
                "1. Send your problem\n"
                "2. A counselor will be assigned\n"
                "3. Chat anonymously!"
            )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages (for active conversations)."""
        user = update.effective_user
        message_text = update.message.text
        
        # Check if user has active cases
        cases = firebase_service.get_user_cases(user.id)
        active_cases = [c for c in cases if c.get('status') == 'active']
        
        if active_cases:
            # Forward to counselor
            for case in active_cases:
                counselor_id = case.get('assigned_counselor_id')
                if counselor_id:
                    firebase_service.add_message_to_case(case['id'], {
                        'sender_role': 'user',
                        'sender_telegram_id': user.id,
                        'message': message_text
                    })
                    
                    try:
                        await self.application.bot.send_message(
                            chat_id=int(counselor_id),
                            text=f"💬 **Anonymous User** (Case `{case['id'][:12]}`)\n\n{message_text}",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
    
    def setup_handlers(self):
        """Setup all bot handlers."""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("assign", self.assign_command))
        self.application.add_handler(CommandHandler("cases", self.cases_command))
        self.application.add_handler(CommandHandler("problem", self.problem_command))
        self.application.add_handler(CommandHandler("close", self.close_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def run(self):
        """Run the bot."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set!")
            return
        
        try:
            from telegram.ext import Application
            import asyncio
            
            async def main():
                application = Application.builder().token(self.token).build()
                
                # Add handlers
                application.add_handler(CommandHandler("start", self.start))
                application.add_handler(CommandHandler("assign", self.assign_command))
                application.add_handler(CommandHandler("cases", self.cases_command))
                application.add_handler(CommandHandler("problem", self.problem_command))
                application.add_handler(CommandHandler("close", self.close_command))
                application.add_handler(CommandHandler("help", self.help_command))
                application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
                
                self.application = application
                
                logger.info("Bot is running...")
                await application.run_polling()
            
            asyncio.run(main())
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise

