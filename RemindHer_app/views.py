from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import User, Reminder, AddTask, InventoryItem, Recipe, GroceryList, UserPreferences, CookingSession
from .serializers import UserSerializer
from rest_framework.parsers import JSONParser, FormParser
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from celery import shared_task
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
import re
from django.http import HttpResponse, JsonResponse
from dateparser import parse


# Existing views unchanged
class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Log the user in automatically after registration
            login(request, user)
            # Redirect to landing page (home page) after successful registration
            return redirect('landing')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not registered'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        if user.status != 'Active':
            return Response({'error': 'Account is inactive'}, status=status.HTTP_400_BAD_REQUEST)

        login(request, user)
        return Response({'message': 'Login successful'}, status=status.HTTP_200_OK)
    
def Login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request, 'Login.html', {'error': 'User not registered'})

        if not user.check_password(password):
            return render(request, 'Login.html', {'error': 'Invalid credentials'})

        if user.status != 'Active':
            return render(request, 'Login.html', {'error': 'Account is inactive'})

        login(request, user)
        return redirect('landing')  # Redirect to landing page

    return render(request, 'Login.html')

@login_required
@login_required
def landing(request):
    return render(request, 'landing.html')

def Register_view(request):
    return render(request, 'Register.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def splashscreen(request):
    return render(request, 'splashscreen.html')

@login_required
def create_reminder(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            task_description = data.get('task_description', '').strip()

            if not task_description:
                return JsonResponse({'error': 'Task description is required'}, status=400)

            # Parse the natural language description
            # For task: everything before time/date indicators or use full text
            task = task_description
            
            # Try to parse date and time from the description
            parsed_datetime = dateparser.parse(
                task_description,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RETURN_AS_TIMEZONE_AWARE': False,
                    'RELATIVE_BASE': datetime.datetime.now()
                }
            )
            
            # Extract task name by removing common time/date phrases
            import re
            # Remove common reminder phrases
            task_clean = re.sub(r'\b(remind me to|reminder to|remind|task)\b', '', task_description, flags=re.IGNORECASE).strip()
            # Remove date/time phrases
            time_patterns = [
                r'\b(at|on|in|by|tomorrow|today|tonight|this|next|every|daily)\s+\d+',
                r'\b\d+\s*(am|pm|AM|PM|o\'clock)\b',
                r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                r'\b(tomorrow|today|tonight)\b',
                r'\b(morning|afternoon|evening|night)\b',
                r'\bat\s+[\w\s:]+',
                r'\bon\s+[\w\s,]+',
            ]
            for pattern in time_patterns:
                task_clean = re.sub(pattern, '', task_clean, flags=re.IGNORECASE)
            
            task = task_clean.strip() or task_description
            
            # Set defaults if parsing failed
            now = datetime.datetime.now()
            if parsed_datetime:
                task_date = parsed_datetime.date()
                task_time = parsed_datetime.time()
            else:
                # Default: tomorrow at 9 AM
                task_date = (now + datetime.timedelta(days=1)).date()
                task_time = datetime.time(9, 0)
            
            # Determine reminder type (check for "daily" or "every day" keywords)
            reminder_type = 'Daily' if any(word in task_description.lower() for word in ['daily', 'every day', 'everyday']) else 'Once'

            # Create the reminder
            reminder = Reminder.objects.create(
                user=request.user,
                task=task,
                task_time=task_time,
                task_date=task_date,
                reminder_type=reminder_type
            )

            # Schedule the reminder (don't fail if scheduling fails)
            try:
                schedule_reminder(reminder)
            except Exception as e:
                print(f"Warning: Failed to schedule reminder: {e}")
                # Continue anyway - reminder is still created
            
            # Format date and time for display
            formatted_date = task_date.strftime('%B %d, %Y')
            formatted_time = task_time.strftime('%I:%M %p')

            return JsonResponse({
                'message': 'Reminder created successfully',
                'reminder_id': reminder.id,
                'task': task,
                'formatted_date': formatted_date,
                'formatted_time': formatted_time,
                'reminder_type': reminder_type
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f"An error occurred: {str(e)}"}, status=500)

    # Render the template for GET requests
    return render(request, 'create_reminder.html')

@shared_task
def play_ringtone(reminder_id):
    try:
        # from playsound import playsound  # Commented out due to installation issues
        reminder = Reminder.objects.get(id=reminder_id)
        print(f"Reminder triggered: {reminder.task} at {reminder.task_time}")
        # Try to play the sound file, but don't fail if it doesn't exist
        # try:
        #     playsound('RemindHer_app/static/images/marco.mp3')
        # except Exception as e:
        #     print(f"Warning: Could not play sound file: {e}")
        # Could implement alternative notification here (browser notification, etc.)
        reminder.is_completed = True
        reminder.save()
    except Exception as e:
        print(f"Error in play_ringtone: {e}")

def schedule_reminder(reminder):
    try:
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=reminder.task_time.minute,
            hour=reminder.task_time.hour,
            day_of_month=reminder.task_date.day,
            month_of_year=reminder.task_date.month,
        )
        PeriodicTask.objects.create(
            crontab=schedule,
            name=f'reminder-{reminder.id}',
            task='RemindHer_app.views.play_ringtone',
            args=json.dumps([reminder.id]),
            one_off=reminder.reminder_type.lower() == 'once'
        )
    except Exception as e:
        print(f"Warning: Failed to schedule reminder task: {e}")
        # Reminder is still created, just not scheduled

@login_required
def snooze_reminder(request, reminder_id, minutes):
    try:
        reminder = Reminder.objects.get(id=reminder_id, user=request.user)
        new_time = (datetime.combine(reminder.task_date, reminder.task_time) + timedelta(minutes=minutes)).time()
        reminder.task_time = new_time
        reminder.is_completed = False
        reminder.save()
        schedule_reminder(reminder)
        return JsonResponse({'message': 'Reminder snoozed'})
    except Reminder.DoesNotExist:
        return JsonResponse({'error': 'Reminder not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def cancel_reminder(request, reminder_id):
    try:
        reminder = Reminder.objects.get(id=reminder_id, user=request.user)
        reminder.is_completed = True
        reminder.save()
        PeriodicTask.objects.filter(name=f'reminder-{reminder.id}').delete()
        return JsonResponse({'message': 'Reminder canceled'})
    except Reminder.DoesNotExist:
        return JsonResponse({'error': 'Reminder not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def check_reminders(request):
    now = datetime.now()
    reminders = Reminder.objects.filter(
        user=request.user,
        task_date=now.date(),
        task_time__hour=now.hour,
        task_time__minute=now.minute,
        is_completed=False
    )
    if reminders.exists():
        reminder = reminders.first()
        return JsonResponse({
            'reminder': {'id': reminder.id, 'task': reminder.task}
        })
    return JsonResponse({'reminder': None})

@login_required
def view_reminders(request):
    # Get both Reminder and AddTask objects
    reminders = list(Reminder.objects.filter(user=request.user, is_completed=False).order_by('task_date', 'task_time'))
    add_tasks = list(AddTask.objects.filter(user=request.user, is_completed=False).order_by('task_date', 'task_time'))

    # Combine and sort all reminders
    all_reminders = []
    for r in reminders:
        all_reminders.append({
            'id': r.id,
            'task': r.task,
            'task_time': r.task_time,
            'task_date': r.task_date,
            'reminder_type': r.reminder_type,
            'created_at': r.created_at,
            'type': 'reminder'
        })

    for t in add_tasks:
        all_reminders.append({
            'id': t.id,
            'task': t.task_name,
            'task_time': t.task_time,
            'task_date': t.task_date,
            'reminder_type': t.reminder_type,
            'created_at': t.created_at,
            'type': 'addtask'
        })

    # Sort by date and time
    all_reminders.sort(key=lambda x: (x['task_date'], x['task_time']))

    return render(request, 'view_reminders.html', {
        'reminders': all_reminders
    })

@login_required
def voice_assistant(request):
    return render(request, 'voice_assistant.html')

@csrf_exempt
@login_required
def process_voice_command(request):
    print(f"Voice command request method: {request.method}")
    print(f"User: {request.user}")
    print(f"Request body: {request.body}")

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            command = data.get('command', '').strip()
            print(f"Voice command received: '{command}'")

            # Always create a reminder - super simple
            from datetime import datetime, timedelta
            now = datetime.now()

            task = AddTask(
                user=request.user,
                task_name=command or 'Voice reminder',
                task_time=(now + timedelta(hours=1)).time(),
                task_date=now.date(),
                reminder_type='Once'
            )
            task.save()
            print(f"Successfully created task: {task}")

            return JsonResponse({
                'success': True,
                'message': f'Reminder created: {task.task_name}'
            })

        except Exception as e:
            print(f"Critical error in voice command processing: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})

    return JsonResponse({'success': False, 'error': 'Method not allowed'})

def parse_voice_command(command):
    """
    Parse natural language voice commands to extract reminder details.
    Ultra-simplified and bulletproof parsing.
    """
    try:
        from datetime import datetime, timedelta

        print(f"Parsing command: '{command}'")

        # Default values - always valid
        now = datetime.now()
        task_time = (now + timedelta(hours=1)).time()  # 1 hour from now
        task_date = now.date()  # Today
        reminder_type = 'Once'
        task_text = "Custom reminder"

        # Check for daily keywords
        if any(word in command.lower() for word in ['daily', 'every day', 'each day', 'everyday']):
            reminder_type = 'Daily'

        # Simple time extraction - look for patterns like "5 PM", "3:30 PM", "8 AM"
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)?', command, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3).lower() if time_match.group(3) else None

            # Convert to 24-hour format
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            elif not ampm and hour <= 12:  # Assume PM for afternoon hours
                if hour < 8:
                    hour += 12

            # Validate hour
            if 0 <= hour <= 23:
                task_time = datetime.strptime(f"{hour}:{minute}", "%H:%M").time()
                print(f"Parsed time: {task_time}")

        # Simple date extraction
        cmd_lower = command.lower()
        if 'tomorrow' in cmd_lower:
            task_date = (now + timedelta(days=1)).date()
        elif 'today' in cmd_lower:
            task_date = now.date()

        # Extract task - remove everything that looks like time/date/reminder words
        task_text = command

        # Remove time patterns
        task_text = re.sub(r'\d{1,2}(?::\d{2})?\s*(am|pm|AM|PM)', '', task_text, flags=re.IGNORECASE)
        task_text = re.sub(r'\d{1,2}\s*(am|pm|AM|PM)', '', task_text, flags=re.IGNORECASE)

        # Remove common words
        remove_patterns = [
            r'\bremind\b', r'\bme\b', r'\bto\b', r'\bat\b', r'\bon\b', r'\bfor\b',
            r'\bset\b', r'\ba\b', r'\bdaily\b', r'\bevery\b', r'\bday\b',
            r'\btomorrow\b', r'\btoday\b', r'\bcreate\b', r'\breminder\b'
        ]

        for pattern in remove_patterns:
            task_text = re.sub(pattern, '', task_text, flags=re.IGNORECASE)

        # Clean up spaces
        task_text = re.sub(r'\s+', ' ', task_text).strip()

        # Final fallback
        if not task_text or len(task_text) < 2:
            # Use the original command but clean it minimally
            task_text = re.sub(r'\d{1,2}(?::\d{2})?\s*(am|pm|AM|PM)', '', command, flags=re.IGNORECASE)
            task_text = re.sub(r'\s+', ' ', task_text).strip()
            if not task_text:
                task_text = "Voice reminder"

        print(f"Final result: task='{task_text}', time={task_time}, date={task_date}, type={reminder_type}")

        return {
            'task': task_text,
            'time': task_time,
            'date': task_date,
            'type': reminder_type
        }

    except Exception as e:
        print(f"Critical parsing error: {e}")
        # Ultimate fallback - always return valid data
        now = datetime.now()
        return {
            'task': 'Voice reminder',
            'time': (now + timedelta(hours=1)).time(),
            'date': now.date(),
            'type': 'Once'
        }

# # New view for voice questionnaire@login_required

@login_required
@csrf_exempt
def start_questionnaire(request):
    print("START: Entering start_questionnaire")
    print(f"Method: {request.method}")
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    print(f"AJAX: {is_ajax}")
    
    if is_ajax and request.method == 'POST':
        print(f"User ID: {request.user.id}")
        try:
            data = json.loads(request.body)
            responses = data.get('responses', {})
            print(f"Received: {responses}")
            
            task_name = responses.get("What is the task name?", "Unnamed Task")
            task_time_str = responses.get("At what time should I remind you?", "10:00 PM")
            task_date_str = responses.get("On which date should I remind you?", "today")
            reminder_type = responses.get("Should I remind you once or daily?", "Once")
            
            task_name = "Unnamed Task" if task_name == "No response" else task_name
            task_time_str = "10:00 PM" if task_time_str == "No response" else task_time_str
            task_date_str = "today" if task_date_str == "No response" else task_date_str
            reminder_type = "Once" if reminder_type == "No response" else reminder_type
            
            print(f"Processed: Name={task_name}, Time={task_time_str}, Date={task_date_str}, Type={reminder_type}")
            
            # Parse time with better settings for Indian users
            task_time_parsed = parse(task_time_str, settings={
                'TIMEZONE': 'Asia/Kolkata',  # IST timezone
                'RETURN_AS_TIMEZONE_AWARE': False
            })
            if task_time_parsed:
                task_time = task_time_parsed.time()
            else:
                # Fallback to current time + 1 hour
                from datetime import datetime, timedelta
                task_time = (datetime.now() + timedelta(hours=1)).time()

            # Parse date with better settings
            task_date_parsed = parse(task_date_str, settings={
                'PREFER_DATES_FROM': 'future',
                'DATE_ORDER': 'DMY',  # Day-Month-Year for Indian format
                'TIMEZONE': 'Asia/Kolkata'
            })
            if task_date_parsed:
                task_date = task_date_parsed.date()
            else:
                # Fallback to tomorrow
                task_date = (datetime.now() + timedelta(days=1)).date()

            reminder_type = reminder_type.capitalize() if reminder_type.capitalize() in ['Once', 'Daily'] else 'Once'
            
            task = AddTask(
                user=request.user,
                task_name=task_name[:255],
                task_time=task_time,
                task_date=task_date,
                reminder_type=reminder_type
            )
            task.save()
            print(f"Saved: {task}")
            
            return JsonResponse({
                'message': 'Task added successfully',
                'task_id': task.id
            }, status=200)
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'message': 'Error adding task', 'error': str(e)}, status=200)
    
    print("Rendering questionnaire.html")
    return render(request, 'questionnaire.html')


# from django.contrib.auth import authenticate, login
# from django.shortcuts import render, redirect
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework import status
# from .models import User, Reminder
# from .serializers import UserSerializer
# from rest_framework.parsers import JSONParser, FormParser
# from django.contrib.auth.decorators import login_required
# import speech_recognition as sr
# import pyttsx3
# import dateparser
# from datetime import datetime, timedelta
# from celery import shared_task
# from django_celery_beat.models import PeriodicTask, CrontabSchedule
# import json
# from django.http import HttpResponse, JsonResponse
# import threading

# # Initialize speech recognition and TTS with a lock
# listener = sr.Recognizer()
# engine = pyttsx3.init()
# voices = engine.getProperty('voices')
# engine.setProperty('voice', voices[1].id)
# speech_lock = threading.Lock()  # Lock to synchronize speech

# listener.dynamic_energy_threshold = True
# listener.energy_threshold = 300
# listener.pause_threshold = 0.8
# listener.phrase_time_limit = 8
# listener.non_speaking_duration = 0.5

# def talk(text):
#     with speech_lock:  # Ensure only one speech at a time
#         engine.say(text)
#         engine.runAndWait()

# def take_command(prompt, expected_type="text"):
#     while True:
#         talk(prompt)
#         print(prompt)
#         try:
#             with sr.Microphone() as source:
#                 listener.adjust_for_ambient_noise(source, duration=2)
#                 print("Listening...")
#                 voice = listener.listen(source)
#                 command = listener.recognize_google(voice, language='en-US').lower()
#                 print(f"User said: {command}")

#                 if expected_type == "time":
#                     parsed = dateparser.parse(command, settings={'TIMEZONE': 'UTC'})
#                     return parsed.time() if parsed else None
#                 elif expected_type == "date":
#                     parsed = dateparser.parse(command, settings={'PREFER_DATES_FROM': 'future'})
#                     return parsed.date() if parsed else None
#                 elif expected_type == "text":
#                     return command
#         except sr.UnknownValueError:
#             talk("Sorry, I didn't catch that. Please repeat.")
#         except Exception as e:
#             print(f"Error: {e}")
#         talk("Please try again.")

# class RegisterView(APIView):
#     def post(self, request):
#         serializer = UserSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class LoginView(APIView):
#     def post(self, request):
#         email = request.data.get('email')
#         password = request.data.get('password')

#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             return Response({'error': 'User not registered'}, status=status.HTTP_400_BAD_REQUEST)

#         if not user.check_password(password):
#             return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

#         if user.status != 'Active':
#             return Response({'error': 'Account is inactive'}, status=status.HTTP_400_BAD_REQUEST)

#         login(request, user)
#         return Response({'message': 'Login successful'}, status=status.HTTP_200_OK)

# def Login_view(request):
#     return render(request, 'Login.html')

# def Register_view(request):
#     return render(request, 'Register.html')

# def splashscreen(request):
#     return render(request, 'splashscreen.html')

# @login_required
# def create_reminder(request):

# Inventory Management Views
@login_required
def inventory_list(request):
    items = InventoryItem.objects.filter(user=request.user)
    return render(request, 'inventory.html', {'items': items})

@login_required
@csrf_exempt
def add_inventory_item(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            quantity = data.get('quantity', 1)
            unit = data.get('unit', 'pieces')
            category = data.get('category', 'Other')
            expiration_date = data.get('expiration_date')
            low_stock_threshold = data.get('low_stock_threshold', 1)

            if not name:
                return JsonResponse({'error': 'Item name is required'}, status=400)

            item = InventoryItem.objects.create(
                user=request.user,
                name=name,
                quantity=quantity,
                unit=unit,
                category=category,
                expiration_date=expiration_date if expiration_date else None,
                low_stock_threshold=low_stock_threshold
            )

            return JsonResponse({
                'message': 'Item added successfully',
                'item_id': item.id,
                'name': item.name,
                'quantity': str(item.quantity),
                'unit': item.unit
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def update_inventory_item(request, item_id):
    try:
        item = InventoryItem.objects.get(id=item_id, user=request.user)
    except InventoryItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item.name = data.get('name', item.name)
            item.quantity = data.get('quantity', item.quantity)
            item.unit = data.get('unit', item.unit)
            item.category = data.get('category', item.category)
            expiration_date = data.get('expiration_date')
            item.expiration_date = expiration_date if expiration_date else None
            item.low_stock_threshold = data.get('low_stock_threshold', item.low_stock_threshold)
            item.save()

            return JsonResponse({
                'message': 'Item updated successfully',
                'item_id': item.id,
                'name': item.name,
                'quantity': str(item.quantity),
                'unit': item.unit
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def delete_inventory_item(request, item_id):
    try:
        item = InventoryItem.objects.get(id=item_id, user=request.user)
        item.delete()
        return JsonResponse({'message': 'Item deleted successfully'})
    except InventoryItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_inventory_alerts(request):
    expired_items = InventoryItem.objects.filter(
        user=request.user,
        expiration_date__lt=datetime.now().date()
    )
    low_stock_items = InventoryItem.objects.filter(
        user=request.user,
        quantity__lte=models.F('low_stock_threshold')
    )

    alerts = []
    for item in expired_items:
        alerts.append({
            'type': 'expired',
            'item': item.name,
            'message': f'{item.name} has expired'
        })
    for item in low_stock_items:
        alerts.append({
            'type': 'low_stock',
            'item': item.name,
            'message': f'{item.name} is running low ({item.quantity} {item.unit} remaining)'
        })

    return JsonResponse({'alerts': alerts})

# Voice command processing for inventory
@login_required
@csrf_exempt
def process_voice_command(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            command = data.get('command', '').lower().strip()

            if not command:
                return JsonResponse({'error': 'No command provided'}, status=400)

            # Parse inventory commands
            if 'add' in command and 'inventory' in command:
                # Extract item details from command
                # This is a simple parser - can be enhanced with NLP
                parts = command.replace('add to inventory', '').replace('add', '').strip().split()
                if len(parts) >= 2:
                    quantity = parts[0]
                    unit = parts[1] if len(parts) > 2 else 'pieces'
                    name = ' '.join(parts[1:]) if len(parts) > 2 else parts[1]

                    try:
                        quantity = float(quantity)
                        item = InventoryItem.objects.create(
                            user=request.user,
                            name=name,
                            quantity=quantity,
                            unit=unit
                        )
                        return JsonResponse({
                            'message': f'Added {quantity} {unit} of {name} to inventory',
                            'item_id': item.id
                        })
                    except ValueError:
                        return JsonResponse({'error': 'Could not parse quantity'}, status=400)

            elif 'remove' in command or 'used' in command:
                # Parse removal commands
                parts = command.replace('remove from inventory', '').replace('used', '').replace('remove', '').strip().split()
                if parts:
                    name = ' '.join(parts)
                    items = InventoryItem.objects.filter(user=request.user, name__icontains=name)
                    if items.exists():
                        item = items.first()
                        item.delete()
                        return JsonResponse({'message': f'Removed {item.name} from inventory'})
                    else:
                        return JsonResponse({'error': f'Item {name} not found in inventory'}, status=404)

            return JsonResponse({'message': 'Command processed', 'command': command})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

# Recipe Management Views
@login_required
def recipe_list(request):
    recipes = Recipe.objects.all()  # In a real app, filter by user preferences
    return render(request, 'recipes.html', {'recipes': recipes})

@login_required
def suggest_recipes(request):
    # Get user's inventory
    user_inventory = InventoryItem.objects.filter(user=request.user).values_list('name', flat=True)

    # Simple recipe suggestion based on available ingredients
    # In a real app, this would be more sophisticated
    recipes = Recipe.objects.all()
    suggestions = []

    for recipe in recipes:
        ingredients = recipe.ingredients if isinstance(recipe.ingredients, list) else []
        available_ingredients = [ing for ing in ingredients if any(inv_item.lower() in ing.lower() or ing.lower() in inv_item.lower() for inv_item in user_inventory)]
        if len(available_ingredients) >= len(ingredients) * 0.5:  # At least 50% ingredients available
            suggestions.append({
                'recipe': recipe,
                'match_percentage': len(available_ingredients) / len(ingredients) * 100,
                'available_ingredients': available_ingredients,
                'missing_ingredients': [ing for ing in ingredients if ing not in available_ingredients]
            })

    # Sort by match percentage
    suggestions.sort(key=lambda x: x['match_percentage'], reverse=True)

    return render(request, 'recipe_suggestions.html', {'suggestions': suggestions[:10]})  # Top 10 suggestions

@login_required
def start_cooking_session(request, recipe_id):
    try:
        recipe = Recipe.objects.get(id=recipe_id)
        # End any existing session
        CookingSession.objects.filter(user=request.user, completed_at__isnull=True).update(completed_at=datetime.now())

        # Start new session
        session = CookingSession.objects.create(user=request.user, recipe=recipe)
        return redirect('cooking_session', session_id=session.id)
    except Recipe.DoesNotExist:
        return JsonResponse({'error': 'Recipe not found'}, status=404)

@login_required
def cooking_session(request, session_id):
    try:
        session = CookingSession.objects.get(id=session_id, user=request.user)
        recipe = session.recipe
        instructions = recipe.instructions if isinstance(recipe.instructions, list) else []

        return render(request, 'cooking_session.html', {
            'session': session,
            'recipe': recipe,
            'instructions': instructions,
            'current_step': session.current_step
        })
    except CookingSession.DoesNotExist:
        return JsonResponse({'error': 'Cooking session not found'}, status=404)

@login_required
@csrf_exempt
def update_cooking_step(request, session_id):
    try:
        session = CookingSession.objects.get(id=session_id, user=request.user)
        if request.method == 'POST':
            data = json.loads(request.body)
            step = data.get('step', session.current_step)
            session.current_step = step
            if step >= len(session.recipe.instructions):
                session.completed_at = datetime.now()
            session.save()

            return JsonResponse({
                'message': 'Step updated',
                'current_step': session.current_step,
                'completed': session.completed_at is not None
            })
    except CookingSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def set_cooking_timer(request, session_id):
    try:
        session = CookingSession.objects.get(id=session_id, user=request.user)
        if request.method == 'POST':
            data = json.loads(request.body)
            timer_name = data.get('name', 'Timer')
            duration_minutes = data.get('duration', 5)

            # In a real app, you'd integrate with a timer system
            # For now, just store in session
            timers = session.timers or {}
            timers[timer_name] = {
                'duration': duration_minutes,
                'started_at': datetime.now().isoformat()
            }
            session.timers = timers
            session.save()

            return JsonResponse({'message': f'Timer set for {duration_minutes} minutes'})
    except CookingSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Grocery List Management Views
@login_required
def grocery_list_view(request):
    try:
        grocery_list = GroceryList.objects.filter(user=request.user, is_completed=False).first()
        if not grocery_list:
            grocery_list = GroceryList.objects.create(user=request.user)
    except:
        grocery_list = GroceryList.objects.create(user=request.user)

    return render(request, 'grocery_list.html', {'grocery_list': grocery_list})

@login_required
@csrf_exempt
def add_grocery_item(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_name = data.get('name', '').strip()
            quantity = data.get('quantity', 1)

            if not item_name:
                return JsonResponse({'error': 'Item name is required'}, status=400)

            # Get or create grocery list
            grocery_list, created = GroceryList.objects.get_or_create(
                user=request.user,
                is_completed=False,
                defaults={'items': []}
            )

            items = grocery_list.items or []
            # Check if item already exists
            item_exists = False
            for item in items:
                if item.get('name', '').lower() == item_name.lower():
                    item['quantity'] = item.get('quantity', 0) + quantity
                    item_exists = True
                    break

            if not item_exists:
                items.append({'name': item_name, 'quantity': quantity, 'completed': False})

            grocery_list.items = items
            grocery_list.save()

            return JsonResponse({
                'message': f'Added {quantity} {item_name} to grocery list',
                'item_count': len(items)
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def update_grocery_item(request, item_index):
    try:
        grocery_list = GroceryList.objects.filter(user=request.user, is_completed=False).first()
        if not grocery_list:
            return JsonResponse({'error': 'No active grocery list found'}, status=404)

        if request.method == 'POST':
            data = json.loads(request.body)
            completed = data.get('completed', False)

            items = grocery_list.items or []
            if 0 <= item_index < len(items):
                items[item_index]['completed'] = completed
                grocery_list.items = items
                grocery_list.save()

                return JsonResponse({'message': 'Item updated successfully'})
            else:
                return JsonResponse({'error': 'Item not found'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def delete_grocery_item(request, item_index):
    try:
        grocery_list = GroceryList.objects.filter(user=request.user, is_completed=False).first()
        if not grocery_list:
            return JsonResponse({'error': 'No active grocery list found'}, status=404)

        items = grocery_list.items or []
        if 0 <= item_index < len(items):
            removed_item = items.pop(item_index)
            grocery_list.items = items
            grocery_list.save()

            return JsonResponse({
                'message': f'Removed {removed_item["name"]} from grocery list'
            })
        else:
            return JsonResponse({'error': 'Item not found'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def complete_grocery_list(request):
    try:
        grocery_list = GroceryList.objects.filter(user=request.user, is_completed=False).first()
        if grocery_list:
            grocery_list.is_completed = True
            grocery_list.save()

            # Create new empty list
            GroceryList.objects.create(user=request.user)

            return JsonResponse({'message': 'Grocery list completed'})
        else:
            return JsonResponse({'error': 'No active grocery list found'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_grocery_suggestions(request):
    from django.db.models import F
    
    # Suggest items based on low inventory
    low_stock_items = InventoryItem.objects.filter(
        user=request.user,
        quantity__lte=F('low_stock_threshold')
    ).values_list('name', flat=True)

    # Suggest items based on consumption patterns (simplified)
    suggestions = list(low_stock_items)
    
    # Add default suggestions if no low-stock items
    if not suggestions:
        suggestions = [
            'Milk', 'Bread', 'Eggs', 'Butter', 'Cheese',
            'Chicken', 'Rice', 'Onions', 'Tomatoes', 'Potatoes',
            'Salt', 'Sugar', 'Oil', 'Garlic', 'Green Vegetables'
        ]
    
    return JsonResponse({'suggestions': suggestions})

@login_required
@csrf_exempt
def create_grocery_reminder(request):
    """Create a reminder for a grocery item"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_name = data.get('item_name', '').strip()
            reminder_date = data.get('reminder_date')
            reminder_time = data.get('reminder_time')
            
            if not item_name:
                return JsonResponse({'error': 'Item name is required'}, status=400)
            
            if not reminder_date or not reminder_time:
                return JsonResponse({'error': 'Date and time are required'}, status=400)
            
            # Parse the date and time
            from datetime import datetime
            try:
                reminder_dt = datetime.strptime(f"{reminder_date} {reminder_time}", '%Y-%m-%d %H:%M')
                task_date = reminder_dt.date()
                task_time = reminder_dt.time()
            except ValueError:
                return JsonResponse({'error': 'Invalid date or time format'}, status=400)
            
            # Create the reminder
            reminder = AddTask.objects.create(
                user=request.user,
                task_name=f"Buy {item_name}",
                task_date=task_date,
                task_time=task_time,
                reminder_type='Once'
            )
            
            return JsonResponse({
                'message': f'Reminder set for {item_name} on {reminder_date} at {reminder_time}',
                'reminder_id': reminder.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
#     if request.method == "POST":
#         task = request.POST.get('task')
#         task_time_str = request.POST.get('task_time')
#         task_date_str = request.POST.get('task_date')
#         reminder_type = request.POST.get('reminder_type')

#         try:
#             task_time = datetime.strptime(task_time_str, '%H:%M:%S').time()
#         except ValueError:
#             task_time = dateparser.parse(task_time_str).time() if task_time_str else None

#         task_date = datetime.strptime(task_date_str, '%Y-%m-%d').date() if task_date_str else None

#         if not task_time or not task_date:
#             return render(request, 'create_reminder.html', {
#                 'error': 'Invalid time or date format. Please try again.',
#                 'task': task, 'task_time': task_time_str, 'task_date': task_date_str, 'reminder_type': reminder_type
#             })

#         reminder = Reminder.objects.create(
#             user=request.user,
#             task=task,
#             task_time=task_time,
#             task_date=task_date,
#             reminder_type=reminder_type
#         )

#         schedule_reminder(reminder)
#         return JsonResponse({'message': 'Reminder set successfully', 'reminder_id': reminder.id})

#     task = take_command("Hey, what's the task?", "text")
#     task_time = take_command("At what time should I remind you?", "time")
#     task_date = take_command("On which date should I remind you?", "date")
#     reminder_type = take_command("Should I remind you once or daily?", "text")

#     confirmation = f"Reminder set for '{task}' on {task_date.strftime('%B %d')} at {task_time.strftime('%I:%M %p')}, {reminder_type}."
#     talk(confirmation)

#     task_time_str = task_time.strftime('%H:%M:%S')
#     task_date_str = task_date.strftime('%Y-%m-%d')

#     return render(request, 'create_reminder.html', {
#         'task': task, 'task_time': task_time_str, 'task_date': task_date_str, 'reminder_type': reminder_type
#     })

# @shared_task
# def play_ringtone(reminder_id):
#     from playsound import playsound
#     reminder = Reminder.objects.get(id=reminder_id)
#     playsound('static\images\marco.mp3')  # Replace with your ringtone file path
#     # Note: Popup logic will be handled client-side or via a desktop client
#     reminder.is_completed = True
#     reminder.save()

# def schedule_reminder(reminder):
#     schedule, _ = CrontabSchedule.objects.get_or_create(
#         minute=reminder.task_time.minute,
#         hour=reminder.task_time.hour,
#         day_of_month=reminder.task_date.day,
#         month_of_year=reminder.task_date.month,
#     )
#     PeriodicTask.objects.create(
#         crontab=schedule,
#         name=f'reminder-{reminder.id}',
#         task='RemindHer_app.views.play_ringtone',
#         args=json.dumps([reminder.id]),
#         one_off=reminder.reminder_type == 'Once'
#     )

# @login_required
# def snooze_reminder(request, reminder_id, minutes):
#     reminder = Reminder.objects.get(id=reminder_id, user=request.user)
#     new_time = (datetime.combine(reminder.task_date, reminder.task_time) + timedelta(minutes=minutes)).time()
#     reminder.task_time = new_time
#     reminder.is_completed = False
#     reminder.save()
#     schedule_reminder(reminder)
#     return JsonResponse({'message': 'Reminder snoozed'})

# @login_required
# def cancel_reminder(request, reminder_id):
#     reminder = Reminder.objects.get(id=reminder_id, user=request.user)
#     reminder.is_completed = True
#     reminder.save()
#     PeriodicTask.objects.filter(name=f'reminder-{reminder.id}').delete()
#     return JsonResponse({'message': 'Reminder canceled'})

# @login_required
# def check_reminders(request):
#     now = datetime.now()
#     reminders = Reminder.objects.filter(
#         user=request.user,
#         task_date=now.date(),
#         task_time__hour=now.hour,
#         task_time__minute=now.minute,
#         is_completed=False
#     )
#     if reminders.exists():
#         reminder = reminders.first()
#         return JsonResponse({
#             'reminder': {'id': reminder.id, 'task': reminder.task}
#         })
#     return JsonResponse({'reminder': None})

