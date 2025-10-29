"""
Standalone admin interface for case management.
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from pathlib import Path
import json

# Import Firebase module - defer import to avoid Django settings issues
_admin_firebase_service = None

def get_admin_firebase_service():
    global _admin_firebase_service
    print(f"[DEBUG] get_admin_firebase_service called, _admin_firebase_service is: {_admin_firebase_service}")
    if _admin_firebase_service is None:
        print("[DEBUG] Initializing Firebase service...")
        try:
            cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json')
            abs_path = Path(cred_path)
            if not abs_path.is_absolute():
                base_dir = Path(getattr(settings, 'BASE_DIR', '.'))
                abs_path = base_dir / abs_path
            print(f"[DEBUG] FIREBASE_CREDENTIALS_PATH setting: {cred_path}")
            print(f"[DEBUG] Resolved credentials path: {abs_path}")
            print(f"[DEBUG] Credentials file exists: {abs_path.exists()}")
        except Exception as debug_e:
            print(f"[DEBUG] Error while checking credentials path: {debug_e}")
        try:
            from .firebase_service import get_firebase_service
            print("[DEBUG] Import successful, calling get_firebase_service()...")
            _admin_firebase_service = get_firebase_service()
            print(f"[DEBUG] Admin Firebase initialized: {_admin_firebase_service}")
        except Exception as e:
            print(f"[ERROR] Firebase service error: {e}")
            import traceback
            traceback.print_exc()
            return None
    print(f"[DEBUG] Returning service: {_admin_firebase_service is not None}")
    return _admin_firebase_service


def admin_dashboard(request):
    """Main admin dashboard for managing cases."""
    # Test Firebase connection before rendering
    print("Testing Firebase connection...")
    try:
        service = get_admin_firebase_service()
        if service:
            print("Firebase connected!")
        else:
            print("Firebase failed to connect!")
    except Exception as e:
        print(f"Firebase error in dashboard: {e}")
        import traceback
        traceback.print_exc()
    
    return render(request, 'admin_dashboard.html')


def api_cases(request):
    """API endpoint to get all cases."""
    print("API called: /admin-ui/api/cases/")
    try:
        service = get_admin_firebase_service()
        print(f"Firebase service: {service}")
        if not service:
            print("No Firebase service!")
            import json
            import traceback
            traceback.print_exc()
            response_data = {'cases': [], 'error': 'Firebase not connected'}
            print(f"Returning: {json.dumps(response_data)}")
            return JsonResponse(response_data, status=200)
        
        print("Fetching cases from Firebase...")
        cases = []
        for doc in service.db.collection('cases').stream():
            case_data = doc.to_dict()
            case_data['id'] = doc.id
            print(f"Found case: {doc.id}")
            
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
        
        # Sort by created_at descending if present
        try:
            cases.sort(key=lambda c: c.get('created_at', ''), reverse=True)
        except Exception:
            pass
        print(f"Returning {len(cases)} cases")
        return JsonResponse({'cases': cases})
    except Exception as e:
        print(f"Error getting cases: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'cases': []}, status=200)  # Return empty list without error


def api_counselors(request):
    """API endpoint to get all counselors."""
    try:
        service = get_admin_firebase_service()
        if not service:
            return JsonResponse({'counselors': []}, status=200)  # Return empty list
        
        users = []
        for doc in service.db.collection('users').stream():
            user_data = doc.to_dict()
            if user_data.get('role') in ['counselor', 'leader']:
                users.append({
                    'telegram_id': user_data.get('telegram_id'),
                    'first_name': user_data.get('first_name', 'Unknown'),
                    'username': user_data.get('username', 'N/A'),
                    'role': user_data.get('role', 'user')
                })
        
        return JsonResponse({'counselors': users})
    except Exception as e:
        print(f"Error getting counselors: {e}")
        return JsonResponse({'counselors': []}, status=200)  # Return empty list


def api_assign_case(request, case_id):
    """API endpoint to assign a case to a counselor."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        counselor_id = data.get('counselor_id')
        
        if not counselor_id:
            return JsonResponse({'error': 'Counselor ID required'}, status=400)
        
        service = get_admin_firebase_service()
        if not service:
            return JsonResponse({'error': 'Firebase not connected'}, status=500)
        
        # Assign case
        service.assign_case(case_id, counselor_id, None)
        
        # Notify counselor via Telegram
        import os
        import asyncio
        from telegram import Bot
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if bot_token:
            try:
                bot = Bot(token=bot_token)
                case = service.get_case(case_id)
                if case:
                    # Run async send_message in sync context
                    asyncio.run(bot.send_message(
                        chat_id=int(counselor_id),
                        text=(
                            f"New Case Assigned to You!\n\n"
                            f"Case ID: {case_id[:8]}\n"
                            f"Problem: {case['problem']}\n\n"
                            f"Please start the conversation with the user."
                        )
                    ))
            except Exception as e:
                print(f"Notification error: {e}")
        
        return JsonResponse({'success': True, 'message': 'Case assigned successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

