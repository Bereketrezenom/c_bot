"""Reply keyboards for Telegram chats."""

from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def build_main_menu():
    """For normal users: no persistent buttons (keyboard removed)."""
    return ReplyKeyboardRemove()


def build_counselor_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔀 Switch case"), KeyboardButton("📋 My cases")],
            [KeyboardButton("📝 Set name"), KeyboardButton("✅ Done")],
            [KeyboardButton("🚫 Block user"), KeyboardButton("❓ Help")],
        ],
        resize_keyboard=True,
    )


def build_admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔀 Switch case"), KeyboardButton("📋 My cases")],
            [KeyboardButton("📝 Set name"), KeyboardButton("✅ Done")],
            [KeyboardButton("🚫 Block user"), KeyboardButton("❓ Help")],
            [KeyboardButton("📊 All cases"), KeyboardButton("🕓 Pending")],
        ],
        resize_keyboard=True,
    )


