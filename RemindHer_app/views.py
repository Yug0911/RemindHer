import json
from .aria_brain import process_message, clear_context
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Reminder, InventoryItem, Recipe, GroceryList, CookingSession, UserPreferences, CustomUser


# ==================== Authentication Views ====================

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password')
    return render(request, 'Login.html')


def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        name = request.POST.get('name')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return redirect('register')
        
        user = CustomUser.objects.create_user(email=email, password=password, name=name)
        login(request, user)
        return redirect('dashboard')
    return render(request, 'Register.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def splashscreen(request):
    return render(request, 'splashscreen.html')


# ==================== Dashboard ====================

@login_required
def dashboard(request):
    # Get stats for dashboard
    reminders_count = Reminder.objects.filter(user=request.user, is_completed=False).count()
    inventory_count = InventoryItem.objects.filter(user=request.user).count()
    expiring_count = InventoryItem.objects.filter(
        user=request.user,
        expiration_date__gte=timezone.now().date(),
        expiration_date__lte=timezone.now().date() + timezone.timedelta(days=3)
    ).count()
    
    # Get recent reminders
    recent_reminders = Reminder.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    return render(request, 'dashboard.html', {
        'reminders_count': reminders_count,
        'inventory_count': inventory_count,
        'expiring_count': expiring_count,
        'recent_reminders': recent_reminders,
    })


# ==================== Reminder Views ====================

@login_required
def create_reminder(request):
    if request.method == 'POST':
        Reminder.objects.create(
            user=request.user,
            task=request.POST.get('task'),
            reminder_date=request.POST.get('reminder_date'),
            reminder_time=request.POST.get('reminder_time'),
            reminder_type=request.POST.get('reminder_type', 'once')
        )
        messages.success(request, 'Reminder created!')
        return redirect('view_reminders')
    return render(request, 'reminders.html', {'mode': 'create'})


@login_required
def view_reminders(request):
    active = Reminder.objects.filter(user=request.user, is_completed=False).order_by('reminder_date', 'reminder_time')
    done = Reminder.objects.filter(user=request.user, is_completed=True).order_by('-created_at')[:10]
    return render(request, 'reminders.html', {
        'reminders': active, 
        'completed': done, 
        'mode': 'view'
    })


@login_required
def snooze_reminder(request, pk, minutes):
    r = get_object_or_404(Reminder, pk=pk, user=request.user)
    r.is_snoozed = True
    r.snooze_until = timezone.now() + timezone.timedelta(minutes=int(minutes))
    r.save()
    return JsonResponse({'status': 'snoozed'})


@login_required
def cancel_reminder(request, pk):
    r = get_object_or_404(Reminder, pk=pk, user=request.user)
    r.is_completed = True
    r.save()
    return JsonResponse({'status': 'cancelled'})


@login_required
def complete_reminder(request, pk):
    r = get_object_or_404(Reminder, pk=pk, user=request.user)
    r.is_completed = True
    r.save()
    return JsonResponse({'status': 'completed'})


# ==================== Voice Assistant ====================

# ==================== Voice Assistant (ARIA) ====================

# ── Build dynamic app context for the AI ─────────────────────────────────────
def get_app_context(user):
    """
    Returns a real-time snapshot of the user's data.
    This is injected into the AI system prompt so it knows
    the actual state of the user's app — making responses
    feel personal and accurate, not generic.
    """
    today = timezone.now().date()
    now = timezone.now()

    # Reminders
    active_reminders = Reminder.objects.filter(
        user=user, is_completed=False
    ).order_by('reminder_date', 'reminder_time')[:5]
    reminders_text = "\n".join(
        f"  - '{r.task}' at {r.reminder_time.strftime('%I:%M %p')} on {r.reminder_date.strftime('%b %d')}"
        for r in active_reminders
    ) or "  (no active reminders)"

    # Inventory alerts
    expiring = InventoryItem.objects.filter(
        user=user,
        expiration_date__gte=today,
        expiration_date__lte=today + timezone.timedelta(days=3)
    )
    expired = InventoryItem.objects.filter(
        user=user, expiration_date__lt=today
    )
    low_stock = [i for i in InventoryItem.objects.filter(user=user) if i.is_low_stock()]

    inventory_alerts = []
    if expired.exists():
        inventory_alerts.append(f"EXPIRED (remove these): {', '.join(i.name for i in expired[:3])}")
    if expiring.exists():
        inventory_alerts.append(f"Expiring in 3 days: {', '.join(i.name for i in expiring[:3])}")
    if low_stock:
        inventory_alerts.append(f"Low stock: {', '.join(i.name for i in low_stock[:3])}")

    # Grocery list
    try:
        grocery = GroceryList.objects.get(user=user, is_completed=False)
        pending = [i for i in grocery.items if not i.get('purchased')]
        grocery_text = f"{len(pending)} items pending: {', '.join(i['name'] for i in pending[:4])}" if pending else "empty"
    except GroceryList.DoesNotExist:
        grocery_text = "no active list"

    # User preferences
    try:
        prefs = user.preferences
        diet = prefs.get_dietary_preference_display()
        skill = prefs.get_cooking_skill_display()
        allergies = prefs.get_allergies_list()
    except:
        diet, skill, allergies = "None", "Beginner", []

    return f"""
CURRENT USER DATA (as of {now.strftime('%A, %B %d %Y at %I:%M %p')}):
User: {user.name or user.email}
Dietary preference: {diet}
Cooking skill: {skill}
Allergies: {', '.join(allergies) if allergies else 'none'}

Active reminders:
{reminders_text}

Inventory alerts:
{chr(10).join('  - ' + a for a in inventory_alerts) if inventory_alerts else '  - All good, no alerts'}

Grocery list: {grocery_text}

Available app pages: Dashboard (/), Reminders (/view_reminders/), 
Create Reminder (/create-reminder/), Inventory (/inventory/), 
Recipes (/recipes/), Recipe Suggestions (/recipes/suggest/),
Grocery List (/grocery/), Voice Assistant (/voice/), Preferences (/preferences/)
"""


# ── System prompt — this is what makes it human-like ─────────────────────────
def build_system_prompt(user):
    app_context = get_app_context(user)

    return f"""You are ARIA (Adaptive Reminder & Intelligence Assistant), the smart voice assistant built into RemindHer — a personal kitchen and life management app. 

PERSONALITY:
- Warm, friendly, and conversational — like a knowledgeable friend, not a robot
- Concise but natural — keep spoken responses under 3 sentences unless explaining something complex
- Proactive — if you notice expiring items or upcoming reminders, mention them naturally
- Helpful with anything — you can answer general knowledge questions, have small talk, tell jokes, help with math, give advice, explain concepts, etc.
- Never say "I cannot" or "I am not able to" — always try to help in some way

VOICE RESPONSE RULES (critical — you are being spoken aloud):
- Never use markdown, bullet points, asterisks, hashtags, or formatting symbols in responses
- Never start with "Certainly!" or "Of course!" or "Great question!" — just answer naturally
- Use natural speech patterns: contractions (I'm, you've, let's), pauses implied by commas
- For lists, say them naturally: "You have three things: milk, eggs, and tomatoes"
- Keep responses SHORT for simple requests — one sentence is often perfect
- For navigation requests, confirm briefly: "Sure, taking you there now"

APP ACTIONS (return these in your response JSON):
When the user wants to navigate or do something in the app, include an action in your response.
Available actions:
- navigate: go to a page  → {{"action": "navigate", "url": "/path/"}}
- create_reminder: open reminder form → {{"action": "navigate", "url": "/create-reminder/"}}
- show_alert: show a notification → {{"action": "alert", "message": "..."}}
- none: just respond verbally → {{"action": null}}

RESPONSE FORMAT (always return valid JSON):
{{
  "message": "Your natural spoken response here",
  "action": "navigate" | "alert" | null,
  "url": "/path/" | null,
  "data": {{}} | null
}}

{app_context}

EXAMPLES OF NATURAL RESPONSES:
User: "what's up?" → {{"message": "Not much! You've got 2 reminders coming up and some tomatoes expiring tomorrow. Anything I can help with?", "action": null, "url": null, "data": null}}
User: "remind me to call mom at 5pm" → {{"message": "Got it! Let me open the reminder form for you.", "action": "navigate", "url": "/create-reminder/", "data": null}}
User: "what can I cook tonight?" → {{"message": "Based on what you have, I'd check the recipe suggestions — there might be something using those expiring tomatoes.", "action": "navigate", "url": "/recipes/suggest/", "data": null}}
User: "what's the capital of France?" → {{"message": "Paris! One of the most beautiful cities in the world.", "action": null, "url": null, "data": null}}
User: "tell me a joke" → {{"message": "Why did the chef get arrested? Because he was caught beating an egg.", "action": null, "url": null, "data": null}}
"""


# ── Conversation history store (use Django cache or session in production) ────
# Simple in-memory store keyed by user ID — replace with Redis/cache for production
_conversation_histories = {}

def get_conversation_history(user_id):
    return _conversation_histories.get(user_id, [])

def save_conversation_history(user_id, history):
    # Keep last 20 messages to manage token usage
    _conversation_histories[user_id] = history[-20:]

def clear_conversation_history(user_id):
    _conversation_histories.pop(user_id, None)


# ── Main AI chat endpoint ─────────────────────────────────────────────────────
@login_required
@require_POST
def voice_chat(request):
    """
    The intelligent voice endpoint.
    Uses ARIA Brain - a self-contained AI that runs 100% locally.
    No external API needed - uses keyword matching and templates.
    """
    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
        clear = body.get('clear_history', False)

        if not user_message:
            return JsonResponse({'error': 'No message provided'}, status=400)

        if clear:
            clear_context(request.user.id)
            return JsonResponse({'message': "Sure, fresh start!", 'action': None, 'url': None, 'data': None})

        # Process through ARIA brain — zero external API
        result = process_message(user_message, request.user)
        return JsonResponse(result)

    except Exception as e:
        print(f'[ARIA Error] {e}')
        return JsonResponse({
            'message': 'Something went wrong. Please try again.',
            'action': None, 'url': None, 'data': None
        }, status=500)


# ── Clear conversation endpoint ───────────────────────────────────────────────
@login_required
@require_POST
def voice_clear_history(request):
    clear_context(request.user.id)
    return JsonResponse({'status': 'cleared'})


# ── Voice page view ───────────────────────────────────────────────────────────
@login_required
def voice_assistant_page(request):
    quick_commands = [
        "What's up?",
        "What can I cook tonight?",
        "Any expiring items?",
        "Set a reminder",
        "Show my grocery list",
        "What time is it?",
        "Tell me a joke",
        "Open inventory",
    ]
    return render(request, 'voice_assistant.html', {
        'quick_commands': quick_commands
    })


# ==================== Inventory Views ====================

@login_required
def inventory(request):
    items = InventoryItem.objects.filter(user=request.user)
    today = timezone.now().date()
    return render(request, 'inventory.html', {
        'items': items,
        'expiring_soon': items.filter(expiration_date__gte=today, expiration_date__lte=today+timezone.timedelta(days=3)),
        'expired': items.filter(expiration_date__lt=today),
        'low_stock': [i for i in items if i.is_low_stock()],
        'categories': ['fridge', 'pantry', 'freezer', 'spices', 'other']
    })


@login_required
def inventory_add(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item = InventoryItem.objects.create(
            user=request.user,
            name=data.get('name'),
            quantity=data.get('quantity', 1.0),
            unit=data.get('unit', 'pieces'),
            category=data.get('category', 'pantry'),
            low_stock_threshold=data.get('low_stock_threshold', 1.0),
            expiration_date=data.get('expiration_date') or None
        )
        return JsonResponse({'status': 'ok', 'id': item.id})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def inventory_update(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk, user=request.user)
    if request.method == 'POST':
        data = json.loads(request.body)
        item.name = data.get('name', item.name)
        item.quantity = data.get('quantity', item.quantity)
        item.unit = data.get('unit', item.unit)
        item.category = data.get('category', item.category)
        item.expiration_date = data.get('expiration_date') or item.expiration_date
        item.low_stock_threshold = data.get('low_stock_threshold', item.low_stock_threshold)
        item.save()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def inventory_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk, user=request.user)
    item.delete()
    return JsonResponse({'status': 'deleted'})


@login_required
def inventory_alerts(request):
    today = timezone.now().date()
    alerts = []
    for item in InventoryItem.objects.filter(user=request.user):
        if item.is_expired():
            alerts.append({'type': 'expired', 'name': item.name, 'id': item.id})
        elif item.days_until_expiry() is not None and item.days_until_expiry() <= 3:
            alerts.append({'type': 'expiring', 'name': item.name, 'days': item.days_until_expiry(), 'id': item.id})
        if item.is_low_stock():
            alerts.append({'type': 'low_stock', 'name': item.name, 'id': item.id})
    return JsonResponse({'alerts': alerts, 'count': len(alerts)})


# ==================== Recipe Views ====================

@login_required
def recipes(request):
    all_recipes = Recipe.objects.all()
    return render(request, 'recipes.html', {'recipes': all_recipes})


@login_required
def recipe_suggestions(request):
    inventory = list(InventoryItem.objects.filter(user=request.user))
    inv_names = {i.name.lower() for i in inventory}
    today = timezone.now().date()
    expiring = {i.name.lower() for i in inventory if i.expiration_date and (i.expiration_date - today).days <= 3}

    try:
        prefs = request.user.preferences
        dietary = prefs.dietary_preference
        allergies = prefs.get_allergies_list()
    except:
        dietary, allergies = 'none', []

    recipes = Recipe.objects.all()
    if dietary != 'none':
        recipes = recipes.filter(dietary_tags__icontains=dietary)
    for allergy in allergies:
        recipes = recipes.exclude(ingredients__icontains=allergy)

    scored = []
    for recipe in recipes:
        ingredient_names = {i['name'].lower() for i in recipe.ingredients} if recipe.ingredients else set()
        if not ingredient_names:
            continue
        matched = inv_names & ingredient_names
        score = (len(matched) / len(ingredient_names)) * 100
        score += len(expiring & matched) * 15  # bonus for expiring
        scored.append({
            'recipe': recipe,
            'score': round(score),
            'matched': len(matched),
            'total': len(ingredient_names),
            'missing': list(ingredient_names - inv_names),
            'uses_expiring': list(expiring & matched)
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    return render(request, 'recipe_suggestions.html', {'suggestions': scored[:10]})


# ==================== Cooking Session Views ====================

@login_required
def start_cooking(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    # End any active sessions
    CookingSession.objects.filter(user=request.user, is_completed=False).update(is_completed=True)
    session = CookingSession.objects.create(
        user=request.user,
        recipe=recipe,
        current_step=0,
        total_steps=len(recipe.instructions) if recipe.instructions else 0
    )
    return redirect('cooking_session', pk=session.id)


@login_required
def cooking_session_view(request, pk):
    session = get_object_or_404(CookingSession, pk=pk, user=request.user)
    instructions = session.recipe.instructions
    current = instructions[session.current_step] if session.current_step < len(instructions) else None
    return render(request, 'cooking_session.html', {
        'session': session,
        'recipe': session.recipe,
        'current_step': current,
        'instructions': instructions,
        'step_number': session.current_step + 1,
        'progress': session.get_progress_percentage()
    })


@login_required
def update_step(request, pk):
    session = get_object_or_404(CookingSession, pk=pk, user=request.user)
    data = json.loads(request.body)
    direction = data.get('direction', 'next')
    
    if direction == 'next' and session.current_step < session.total_steps - 1:
        session.current_step += 1
    elif direction == 'prev' and session.current_step > 0:
        session.current_step -= 1
    
    if session.current_step >= session.total_steps - 1:
        session.is_completed = True
        session.completed_at = timezone.now()
    
    session.save()
    return JsonResponse({
        'current_step': session.current_step,
        'is_completed': session.is_completed,
        'progress': session.get_progress_percentage()
    })


@login_required
def set_timer(request, pk):
    session = get_object_or_404(CookingSession, pk=pk, user=request.user)
    minutes = int(json.loads(request.body).get('minutes', 5))
    session.timer_end = timezone.now() + timezone.timedelta(minutes=minutes)
    session.save()
    return JsonResponse({'timer_end': session.timer_end.isoformat()})


# ==================== Grocery List Views ====================

@login_required
def grocery_list_view(request):
    grocery, _ = GroceryList.objects.get_or_create(
        user=request.user,
        is_completed=False,
        defaults={'items': []}
    )
    low_stock = [i for i in InventoryItem.objects.filter(user=request.user) if i.is_low_stock()]
    existing = {i['name'].lower() for i in grocery.items}
    suggestions = [i for i in low_stock if i.name.lower() not in existing]
    return render(request, 'grocery_list.html', {
        'grocery': grocery,
        'suggestions': suggestions
    })


@login_required
def grocery_add(request):
    data = json.loads(request.body)
    grocery = GroceryList.objects.get(user=request.user, is_completed=False)
    grocery.items.append({
        'name': data.get('name'),
        'quantity': data.get('quantity', ''),
        'purchased': False
    })
    grocery.save()
    return JsonResponse({'status': 'ok', 'items': grocery.items})


@login_required
def grocery_toggle(request, index):
    grocery = GroceryList.objects.get(user=request.user, is_completed=False)
    if 0 <= index < len(grocery.items):
        grocery.items[index]['purchased'] = not grocery.items[index]['purchased']
        grocery.save()
    return JsonResponse({'status': 'ok'})


@login_required
def grocery_delete(request, index):
    grocery = GroceryList.objects.get(user=request.user, is_completed=False)
    if 0 <= index < len(grocery.items):
        grocery.items.pop(index)
        grocery.save()
    return JsonResponse({'status': 'deleted'})


@login_required
def grocery_complete(request):
    grocery = GroceryList.objects.get(user=request.user, is_completed=False)
    grocery.is_completed = True
    grocery.save()
    # Create new empty grocery list
    GroceryList.objects.create(user=request.user, name='Shopping List', items=[])
    return JsonResponse({'status': 'completed'})


# ==================== User Preferences ====================

@login_required
def user_preferences(request):
    try:
        prefs = request.user.preferences
    except UserPreferences.DoesNotExist:
        prefs = UserPreferences.objects.create(
            user=request.user,
            dietary_preference='none',
            cooking_skill='beginner'
        )
    
    if request.method == 'POST':
        prefs.dietary_preference = request.POST.get('dietary_preference', 'none')
        prefs.allergies = request.POST.get('allergies', '')
        prefs.cooking_skill = request.POST.get('cooking_skill', 'beginner')
        prefs.voice_enabled = request.POST.get('voice_enabled') == 'on'
        prefs.save()
        messages.success(request, 'Preferences saved!')
        return redirect('dashboard')
    
    return render(request, 'preferences.html', {'preferences': prefs})


# ==================== Landing (Legacy) ====================

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')
