# Setup Guide

## Quick Start

### 1. Environment Variables

Create a `.env` file in the project root with:

```
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
TELEGRAM_BOT_TOKEN=your-bot-token-here
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Start the Bot

```bash
python manage.py run_bot
```

## Firebase Setup

1. Create a Firebase project at https://console.firebase.google.com/
2. Enable Firestore Database
3. Go to Project Settings > Service Accounts
4. Click "Generate New Private Key"
5. Save as `serviceAccountKey.json` in project root

## Creating Your Bot

1. Open Telegram
2. Search for @BotFather
3. Send `/newbot`
4. Follow instructions
5. Copy the bot token to `.env` file

