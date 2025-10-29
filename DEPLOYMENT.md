# Deployment Guide

## Local Development

### Prerequisites
- Python 3.8+
- Firebase account
- Telegram bot token

### Steps

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**
   - Create `.env` file from template
   - Add your Firebase credentials
   - Add your Telegram bot token

3. **Initialize Django**
   ```bash
   python manage.py migrate
   ```

4. **Run the application**
   ```bash
   # Option 1: Run together
   python run.py
   
   # Option 2: Run separately
   python manage.py runserver  # Terminal 1
   python manage.py run_bot    # Terminal 2
   ```

## Production Deployment (Render)

### Frontend/API Service

1. Go to [Render](https://render.com)
2. Create new Web Service
3. Connect your GitHub repository
4. Configure:
   - **Name**: `counseling-bot-api`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python manage.py runserver`
   - **Environment Variables**:
     ```
     DJANGO_SECRET_KEY=your-secret-key
     DEBUG=False
     TELEGRAM_BOT_TOKEN=your-bot-token
     FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
     ```

### Bot Worker Service

1. Create new Background Worker
2. Configure:
   - **Name**: `counseling-bot-worker`
   - **Start Command**: `python manage.py run_bot`
   - **Environment Variables**: Same as API service

### Firebase Setup

1. **Upload credentials to Render**:
   - In Dashboard, go to Environment
   - Upload `serviceAccountKey.json` as Secret File
   - Or paste JSON content as environment variable

2. **Enable Firestore**:
   - Go to Firebase Console
   - Enable Firestore Database
   - Set rules for production

## Firebase Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users collection
    match /users/{userId} {
      allow read, write: if request.auth != null;
    }
    
    // Cases collection
    match /cases/{caseId} {
      allow read: if request.auth != null;
      allow create: if request.auth != null;
      allow update: if request.auth != null;
    }
  }
}
```

## Environment Variables

Create a `.env` file for local development:

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Firebase
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json
```

For production, set these in your hosting platform's environment variables.

## Monitoring

### Health Check
```bash
curl https://your-api.render.com/api/health/
```

### Get Statistics
```bash
curl https://your-api.render.com/api/stats/
```

### View Cases
```bash
curl https://your-api.render.com/api/cases/
```

## Troubleshooting

### Bot not responding
- Check bot token is correct
- Verify bot is running in worker service
- Check logs in Render dashboard

### Database errors
- Verify Firebase credentials are uploaded
- Check Firestore rules
- Ensure Firestore is enabled

### API not accessible
- Check `ALLOWED_HOSTS` in settings
- Verify environment variables
- Check service logs

## SSL/TLS

Render provides SSL automatically. No additional configuration needed.

## Scaling

- **API Service**: Automatically scales on Render
- **Bot Worker**: Runs as single instance (can duplicate if needed)
- **Firestore**: Scales automatically

## Backup and Recovery

Firestore automatically backs up data. No additional action needed.

