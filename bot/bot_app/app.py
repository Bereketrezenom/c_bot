import logging

from django.conf import settings
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from . import commands
from . import messages
from .utils import apply_ptb_py313_patch


logger = logging.getLogger(__name__)


def _register_handlers(application: Application) -> None:
    logger.info("Adding handlers...")
    application.add_handler(CommandHandler("start", commands.start))
    application.add_handler(CommandHandler("menu", commands.menu_command))
    application.add_handler(CommandHandler("end", commands.end_command))
    application.add_handler(CommandHandler("setname", commands.setname_command))
    application.add_handler(CommandHandler("rename", commands.rename_command))
    application.add_handler(CommandHandler("clearname", commands.clearname_command))
    application.add_handler(CommandHandler("problem", commands.problem_command))
    application.add_handler(CommandHandler("assign", commands.assign_command))
    application.add_handler(CommandHandler("cases", commands.cases_command))
    application.add_handler(CommandHandler("switch", commands.switch_command))
    application.add_handler(CommandHandler("register_counselor", commands.register_counselor_command))
    application.add_handler(CommandHandler("help", commands.help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages.handle_message))


def run() -> None:
    """Create and run the Telegram application."""
    apply_ptb_py313_patch()

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    logger.info("Creating application...")
    application = Application.builder().token(token).build()
    _register_handlers(application)

    logger.info("Bot is running...")
    application.run_polling()


