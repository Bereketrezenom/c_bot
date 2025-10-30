import logging
import os
from pathlib import Path

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

    _ensure_firebase_creds_file()

    logger.info("Creating application...")
    application = Application.builder().token(token).build()
    _register_handlers(application)

    # Decide between webhook and polling. Use webhook if WEBHOOK_URL or WEBHOOK_BASE_URL is set.
    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        base = os.environ.get("WEBHOOK_BASE_URL")  # e.g., https://your-service.onrender.com
        if base:
            base = base.rstrip("/")
            webhook_url = f"{base}/{token}"

    if webhook_url:
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"Starting webhook server on 0.0.0.0:{port}")
        logger.info(f"Webhook URL set to {webhook_url}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=webhook_url,
        )
    else:
        logger.info("Starting in polling mode (no WEBHOOK_URL/WEBHOOK_BASE_URL detected)")
        application.run_polling()


def _ensure_firebase_creds_file() -> None:
    """If FIREBASE_CREDENTIALS_JSON is provided, write it to serviceAccountKey.json.

    This allows Render Secret (env var) based provisioning without committing the file.
    The Firebase service already defaults to reading settings.FIREBASE_CREDENTIALS_PATH
    which is 'serviceAccountKey.json' at the project base.
    """
    json_blob = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if not json_blob:
        return

    try:
        base_dir = Path(getattr(settings, 'BASE_DIR', '.'))
        target = base_dir / 'serviceAccountKey.json'
        if not target.exists():
            target.write_text(json_blob)
            logger.info(f"Wrote Firebase credentials to {target}")
    except Exception as e:
        logger.error(f"Failed to write Firebase credentials file: {e}")


