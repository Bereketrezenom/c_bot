"""
Custom admin site for the counseling bot.
"""
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json

# Initialize Firebase service lazily
firebase_service = None

def get_firebase_service():
    global firebase_service
    if firebase_service is None:
        try:
            # Use the lazy initializer from firebase_service.py
            from .firebase_service import get_firebase_service as _get_fb_service
            firebase_service = _get_fb_service()
        except Exception as e:
            print(f"Firebase not initialized: {e}")
            return None
    return firebase_service


# Customize admin site
admin.site.site_header = "Counseling Bot Administration"
admin.site.site_title = "Counseling Admin"
admin.site.index_title = "Welcome to Counseling Bot Admin"


# Add custom views
@login_required
def counseling_cases_view(request):
    """View for managing counseling cases."""
    return render(request, 'admin/counseling_cases.html', {
        'title': 'Counseling Cases',
        'has_permission': True,
        'is_popup': False,
    })


@login_required
def cases_api_view(request):
    """API endpoint for getting cases."""
    try:
        service = get_firebase_service()
        if not service:
            return JsonResponse({'error': 'Firebase not initialized'}, status=500)
        
        cases = []
        for doc in service.db.collection('cases').stream():
            case_data = doc.to_dict()
            case_data['id'] = doc.id
            
            # Get user info
            user = service.get_user(case_data.get('user_telegram_id'))
            if user:
                case_data['user_info'] = {
                    'first_name': user.get('first_name', 'Unknown'),
                    'username': user.get('username', 'N/A')
                }
            
            # Get counselor info if assigned
            if case_data.get('assigned_counselor_id'):
                counselor = service.get_user(case_data['assigned_counselor_id'])
                if counselor:
                    case_data['counselor_info'] = {
                        'first_name': counselor.get('first_name', 'Unknown'),
                        'username': counselor.get('username', 'N/A')
                    }
            
            cases.append(case_data)
        
        # Sort by created_at descending if available
        try:
            cases.sort(key=lambda c: c.get('created_at', ''), reverse=True)
        except Exception:
            pass
        return JsonResponse({'cases': cases})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
        


@login_required
def users_api_view(request):
    """API endpoint for getting users/counselors."""
    try:
        service = get_firebase_service()
        if not service:
            return JsonResponse({'error': 'Firebase not initialized'}, status=500)
        
        users = []
        for doc in service.db.collection('users').stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            
            # Only return counselors and leaders
            if user_data.get('role') in ['counselor', 'leader']:
                users.append({
                    'telegram_id': user_data.get('telegram_id'),
                    'first_name': user_data.get('first_name', 'Unknown'),
                    'username': user_data.get('username', 'N/A'),
                    'role': user_data.get('role', 'user')
                })
        
        return JsonResponse({'users': users})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def assign_case_view(request, case_id):
    """Assign a case to a counselor."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            counselor_id = data.get('counselor_id')
            
            if not counselor_id:
                return JsonResponse({'error': 'Counselor ID required'}, status=400)
            
            service = get_firebase_service()
            if not service:
                return JsonResponse({'error': 'Firebase not initialized'}, status=500)
            
            # Assign case
            service.assign_case(case_id, counselor_id, None)  # Leader ID can be None for now
            
            # Notify counselor via bot
            import os
            from telegram import Bot
            
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if bot_token:
                bot = Bot(token=bot_token)
                
                # Get case details
                case = service.get_case(case_id)
                if case:
                    try:
                        bot.send_message(
                            chat_id=int(counselor_id),
                            text=(
                                f"📋 New Case Assigned to You!\n\n"
                                f"Case ID: {case_id[:8]}\n"
                                f"Problem: {case['problem']}\n\n"
                                f"Please start the conversation with the user."
                            )
                        )
                    except Exception as e:
                        print(f"Error sending notification: {e}")
            
            return JsonResponse({'success': True, 'message': 'Case assigned successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


