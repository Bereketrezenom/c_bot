"""Reply keyboards for Telegram chats."""

from telegram import ReplyKeyboardMarkup, KeyboardButton


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🆕 New problem"), KeyboardButton("📋 My cases")],
            [KeyboardButton("🔀 Switch case"), KeyboardButton("🔒 End chat")],
            [KeyboardButton("❓ Help")],
        ],
        resize_keyboard=True,
    )


def build_counselor_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🔀 Switch case"), KeyboardButton("📋 My cases")],
            [KeyboardButton("📝 Set name"), KeyboardButton("🔒 End chat")],
            [KeyboardButton("❓ Help")],
        ],
        resize_keyboard=True,
    )


