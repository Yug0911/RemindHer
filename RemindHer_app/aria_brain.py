"""
ARIA Brain — Self-contained AI for RemindHer
No external API needed. Runs 100% locally inside Django.
Uses: regex + keyword matching + dateparser
"""

import re
import random
import dateparser
from django.utils import timezone
from urllib.parse import urlencode


# ── Personality Layer ─────────────────────────────────────────────────────────
RESPONSES = {
    "greet_morning": [
        "Good morning! You're up early. What can I help you with today?",
        "Morning! Hope you slept well. Ready to tackle the day?",
        "Good morning! What's on your mind today?",
    ],
    "greet_afternoon": [
        "Hey! Good afternoon. How's your day going?",
        "Afternoon! What can I do for you?",
        "Hi there! Having a good day so far?",
    ],
    "greet_evening": [
        "Good evening! Winding down or just getting started?",
        "Hey, good evening! What do you need?",
        "Evening! Long day? What can I help with?",
    ],
    "greet_generic": [
        "Hey! Good to hear from you. What's up?",
        "Hi! How can I help you today?",
        "Hello! What can I do for you?",
        "Hey there! What do you need?",
    ],
    "confirm_navigate": [
        "Sure, taking you there now!",
        "On it! Opening that for you.",
        "Got it, heading there now.",
        "Absolutely, let me take you there.",
        "Sure thing!",
    ],
    "confirm_reminder": [
        "Got it! Let me open the reminder form.",
        "Sure! I'll take you to create that reminder.",
        "Opening the reminder form for you now.",
        "On it! Let's set that reminder up.",
    ],
    "confirm_recipe": [
        "Let me check what you can cook with what you have!",
        "Great idea! Checking your ingredients for recipe ideas.",
        "Sure! Let me find some recipes based on your inventory.",
        "I'll look at what's in your kitchen and suggest something tasty!",
    ],
    "confirm_grocery": [
        "Here's your shopping list!",
        "Opening your grocery list now.",
        "Let me pull up your shopping list.",
        "Sure! Here's what you need to buy.",
    ],
    "confirm_inventory": [
        "Opening your kitchen inventory!",
        "Let me show you what's in your kitchen.",
        "Here's what you've got stored.",
        "Sure! Checking your inventory now.",
    ],
    "expiry_check": [
        "Let me check what's about to expire in your kitchen.",
        "Sure! I'll look for anything going bad soon.",
        "Checking your inventory for items expiring soon.",
    ],
    "unknown": [
        "Hmm, I'm not sure about that. Try asking me about reminders, recipes, or your inventory!",
        "I didn't quite get that. You can ask me to set reminders, check recipes, or open your inventory.",
        "Not sure I understood. Try: set a reminder, what can I cook, or show my grocery list.",
        "I'm still learning! Try asking about reminders, food, or your kitchen inventory.",
    ],
    "joke": [
        "Why did the chef get arrested? Because he was caught beating an egg!",
        "What do you call a fake noodle? An impasta!",
        "Why did the tomato turn red? Because it saw the salad dressing!",
        "I tried to write a joke about vegetables, but it was too corny.",
        "What do you call cheese that isn't yours? Nacho cheese!",
    ],
    "compliment": [
        "Aw, thank you! You're pretty great yourself.",
        "That's so sweet! I'm just here to help.",
        "Thanks! You just made my day — well, my processing cycle.",
        "Thank you! Now, what can I do for this wonderful person?",
    ],
    "how_are_you": [
        "I'm doing great, thanks for asking! What about you?",
        "Running perfectly! Ready to help. How are you doing?",
        "All systems go! How can I help you today?",
        "Fantastic as always! What's on your mind?",
    ],
    "thanks": [
        "You're welcome! Anything else I can help with?",
        "Happy to help! Is there anything else you need?",
        "Of course! Let me know if you need anything else.",
        "Anytime! That's what I'm here for.",
    ],
    "confirm_preferences": [
        "Opening your preferences so you can update your settings.",
        "Sure! Let me take you to your preferences.",
        "Here are your settings and preferences!",
    ],
}

def pick(key):
    options = RESPONSES.get(key, RESPONSES["unknown"])
    return random.choice(options)


# ── Intent Definitions ────────────────────────────────────────────────────────
INTENTS = [
    ("greet", ["hello","hi","hey","good morning","good afternoon","good evening","what's up","howdy","sup"], 80),
    ("how_are_you", ["how are you","how do you do","you okay","you good","how's it going","how are things"], 75),
    ("thanks", ["thank you","thanks","cheers","appreciate it","thank u","thx"], 80),
    ("joke", ["joke","funny","make me laugh","tell me something funny","humor me","laugh"], 75),
    ("compliment", ["you're great","you're amazing","i love you","good job","well done","you're awesome","nice work"], 70),
    ("set_reminder", ["remind me","set a reminder","add reminder","create reminder","new reminder","don't let me forget","remember to","set reminder","make a reminder"], 75),
    ("view_reminders", ["show reminders","my reminders","view reminders","list reminders","what are my reminders","reminders","upcoming reminders","do i have reminders"], 75),
    ("inventory", ["inventory","fridge","pantry","freezer","spices","what do i have","my ingredients","kitchen items","what's in my kitchen","check kitchen","my food"], 75),
    ("expiry", ["expiring","expire","going bad","use soon","old food","what's expiring","about to expire","expiry","check expiry","spoil"], 75),
    ("recipes", ["recipe","cook","what can i make","what can i cook","suggest a recipe","cooking ideas","dinner ideas","meal ideas","what should i cook","food ideas","make something","cook tonight"], 75),
    ("grocery", ["grocery","shopping","shopping list","buy","need to buy","what to buy","groceries","market list","things to buy","purchase"], 75),
    ("cooking_session", ["start cooking","cook now","begin recipe","cook this","start recipe","guide me","step by step"], 75),
    ("dashboard", ["home","dashboard","go home","main menu","go back","main page","start page","go to home"], 80),
    ("preferences", ["settings","preferences","profile","my profile","dietary","allergies","update settings","change settings"], 75),
    ("time", ["what time","current time","what's the time","tell me the time","time now"], 80),
    ("date", ["what day","what's today","today's date","what date","current date","day today"], 80),
    ("low_stock", ["low stock","running out","almost out","need more","restock","running low"], 75),
    ("navigate_external", ["go to","open","redirect me to","take me to","visit","navigate to","show me","launch"], 75),
]

EXTERNAL_URLS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "reddit": "https://www.reddit.com",
    "github": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com",
    "wikipedia": "https://www.wikipedia.org",
    "whatsapp": "https://web.whatsapp.com",
    "linkedin": "https://www.linkedin.com",
    "tiktok": "https://www.tiktok.com",
}


# ── Intent Detector ───────────────────────────────────────────────────────────
def detect_intent(text):
    text_lower = text.lower().strip()
    
    best_intent = None
    
    for intent_name, keywords, threshold in INTENTS:
        for keyword in keywords:
            if keyword in text_lower:
                return intent_name
    
    return "unknown"


# ── Entity Extractor ─────────────────────────────────────────────────────────
def extract_entities(text):
    text_lower = text.lower()
    
    entities = {
        "time": None,
        "date": None,
        "task": None,
        "food": [],
        "numbers": [],
        "website": None,
    }
    
    # Try dateparser for natural time expressions
    parsed_dt = dateparser.parse(text, settings={"PREFER_DATES_FROM": "future"})
    if parsed_dt:
        entities["time"] = parsed_dt.strftime("%I:%M %p")
        entities["date"] = parsed_dt.strftime("%Y-%m-%d")
    
    # Extract food-related words
    food_keywords = {"milk","eggs","bread","tomato","chicken","rice","pasta",
                     "butter","cheese","apple","banana","onion","garlic",
                     "potato","carrot","spinach","flour","sugar","salt","oil",
                     "fish","beef","pork","vegetables","fruits","yogurt","curd"}
    words = set(text_lower.split())
    entities["food"] = list(words.intersection(food_keywords))
    
    # Extract task (text after "remind me to" / "remember to")
    task_patterns = [
        r"remind me to (.+)",
        r"remember to (.+)",
        r"don't let me forget to (.+)",
        r"set a reminder (?:to|for) (.+)",
    ]
    for pattern in task_patterns:
        match = re.search(pattern, text_lower)
        if match:
            entities["task"] = match.group(1).strip()
            break
    
    # Extract website name from navigation commands
    website_patterns = [
        r"(?:go to|open|redirect me to|take me to|visit|navigate to|show me|launch)\s+(.+)",
    ]
    for pattern in website_patterns:
        match = re.search(pattern, text_lower)
        if match:
            website_raw = match.group(1).strip().rstrip(".")
            # Strip common TLDs for matching
            for tld in [".com", ".org", ".net", ".io", ".co"]:
                if website_raw.endswith(tld):
                    website_raw = website_raw[:-len(tld)]
                    break
            # Check if it matches a known site
            for site_name in EXTERNAL_URLS.keys():
                if site_name in website_raw:
                    entities["website"] = site_name
                    break
            if not entities["website"]:
                entities["website"] = website_raw
    
    return entities


# ── Context Manager ─────────────────────────────────────────────────────────
class ConversationContext:
    def __init__(self):
        self.history = []
        self.last_intent = None
        self.last_entities = {}
        self.turn_count = 0

    def add(self, role, text, intent=None):
        self.history.append({
            "role": role,
            "text": text,
            "intent": intent,
        })
        if role == "user":
            self.turn_count += 1
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def clear(self):
        self.history = []
        self.last_intent = None
        self.last_entities = {}
        self.turn_count = 0


# ── Live Data Fetcher ─────────────────────────────────────────────────────────
def get_live_data(user):
    from .models import Reminder, InventoryItem, GroceryList
    today = timezone.now().date()
    now = timezone.now()

    data = {
        "reminders": [],
        "expiring": [],
        "expired": [],
        "low_stock": [],
        "grocery_pending": [],
        "hour": now.hour,
    }

    # Active reminders
    reminders = Reminder.objects.filter(
        user=user, is_completed=False
    ).order_by("reminder_date", "reminder_time")[:5]
    data["reminders"] = [
        f"'{r.task}' at {r.reminder_time.strftime('%I:%M %p')} on {r.reminder_date.strftime('%b %d')}"
        for r in reminders
    ]

    # Inventory alerts
    items = InventoryItem.objects.filter(user=user)
    data["expiring"] = [
        i.name for i in items
        if i.expiration_date and 0 <= (i.expiration_date - today).days <= 3
    ]
    data["expired"] = [
        i.name for i in items
        if i.expiration_date and i.expiration_date < today
    ]
    data["low_stock"] = [i.name for i in items if i.is_low_stock()]

    # Grocery pending items
    try:
        grocery = GroceryList.objects.get(user=user, is_completed=False)
        data["grocery_pending"] = [
            i["name"] for i in grocery.items if not i.get("purchased")
        ]
    except Exception:
        pass

    return data


# ── Response Builder ──────────────────────────────────────────────────────────
def build_response(intent, entities, live_data, user, context):
    hour = live_data.get("hour", 12)
    name = (user.name or "").split()[0] if user.name else ""

    # Greeting
    if intent == "greet":
        if hour < 12:
            base = pick("greet_morning")
        elif hour < 18:
            base = pick("greet_afternoon")
        else:
            base = pick("greet_evening")

        alerts = []
        if live_data["expiring"]:
            alerts.append(f"heads up — {live_data['expiring'][0]} is expiring soon")
        if live_data["reminders"]:
            alerts.append(f"you have {len(live_data['reminders'])} upcoming reminder(s)")
        if live_data["expired"]:
            alerts.append(f"{len(live_data['expired'])} item(s) in your kitchen have expired")

        if alerts:
            base += f" By the way, {' and '.join(alerts[:2])}."

        return {"message": base, "action": None, "url": None}

    # How are you
    elif intent == "how_are_you":
        return {"message": pick("how_are_you"), "action": None, "url": None}

    # Thanks
    elif intent == "thanks":
        return {"message": pick("thanks"), "action": None, "url": None}

    # Joke
    elif intent == "joke":
        return {"message": pick("joke"), "action": None, "url": None}

    # Compliment
    elif intent == "compliment":
        return {"message": pick("compliment"), "action": None, "url": None}

    # Set Reminder
    elif intent == "set_reminder":
        task = entities.get("task")
        time = entities.get("time")
        date = entities.get("date")

        if task and time:
            msg = f"Got it! I'll help you set a reminder to {task} at {time}. Opening the form!"
        elif task:
            msg = f"Sure! Let me open the reminder form for '{task}'."
        else:
            msg = pick("confirm_reminder")

        url = "/create-reminder/"
        if task:
            params = {"task": task}
            if date:
                params["date"] = date
            if time:
                params["time"] = time
            url = f"/create-reminder/?{urlencode(params)}"

        return {"message": msg, "action": "navigate", "url": url}

    # View Reminders
    elif intent == "view_reminders":
        count = len(live_data["reminders"])
        if count == 0:
            msg = "You have no active reminders right now. Want to create one?"
        elif count == 1:
            msg = f"You have 1 reminder: {live_data['reminders'][0]}. Opening your reminders now!"
        else:
            msg = f"You have {count} reminders coming up. Let me show you all of them!"
        return {"message": msg, "action": "navigate", "url": "/view_reminders/"}

    # Inventory
    elif intent == "inventory":
        alerts = []
        if live_data["expired"]:
            alerts.append(f"{len(live_data['expired'])} expired item(s) to remove")
        if live_data["expiring"]:
            alerts.append(f"{', '.join(live_data['expiring'][:2])} expiring soon")
        if live_data["low_stock"]:
            alerts.append(f"{len(live_data['low_stock'])} item(s) running low")

        if alerts:
            msg = f"Opening your inventory. Quick heads up: {' and '.join(alerts)}."
        else:
            msg = pick("confirm_inventory")
        return {"message": msg, "action": "navigate", "url": "/inventory/"}

    # Expiry Check
    elif intent == "expiry":
        expired = live_data["expired"]
        expiring = live_data["expiring"]

        if not expired and not expiring:
            msg = "Great news! Nothing in your kitchen is expired or expiring soon. You're all good!"
            return {"message": msg, "action": None, "url": None}

        parts = []
        if expired:
            items = ", ".join(expired[:3])
            parts.append(f"these items have already expired: {items}")
        if expiring:
            items = ", ".join(expiring[:3])
            parts.append(f"these are expiring in the next 3 days: {items}")

        msg = f"Heads up! {'. And '.join(parts)}. Opening your inventory so you can manage them."
        return {"message": msg, "action": "navigate", "url": "/inventory/"}

    # Recipes
    elif intent == "recipes":
        expiring = live_data["expiring"]
        if expiring:
            msg = f"Great timing! You have {', '.join(expiring[:2])} expiring soon. Let me find recipes that use them!"
        else:
            msg = pick("confirm_recipe")
        return {"message": msg, "action": "navigate", "url": "/recipes/suggest/"}

    # Grocery
    elif intent == "grocery":
        pending = live_data["grocery_pending"]
        low = live_data["low_stock"]

        if pending:
            msg = f"You have {len(pending)} item(s) on your list: {', '.join(pending[:3])}{'...' if len(pending) > 3 else ''}. Opening your list!"
        elif low:
            msg = f"Your grocery list is empty but {', '.join(low[:2])} are running low. You might want to add them!"
        else:
            msg = pick("confirm_grocery")
        return {"message": msg, "action": "navigate", "url": "/grocery/"}

    # Dashboard
    elif intent == "dashboard":
        return {"message": "Taking you home!", "action": "navigate", "url": "/"}

    # Preferences
    elif intent == "preferences":
        return {"message": pick("confirm_preferences"), "action": "navigate", "url": "/preferences/"}

    # Time
    elif intent == "time":
        import datetime
        now = datetime.datetime.now().strftime("%I:%M %p")
        return {"message": f"It's {now} right now.", "action": None, "url": None}

    # Date
    elif intent == "date":
        import datetime
        today = datetime.date.today().strftime("%A, %B %d %Y")
        return {"message": f"Today is {today}.", "action": None, "url": None}

    # Low Stock
    elif intent == "low_stock":
        low = live_data["low_stock"]
        if low:
            items = ", ".join(low[:4])
            msg = f"These items are running low: {items}. Want me to open your grocery list?"
        else:
            msg = "Everything looks well-stocked! Nothing is running low right now."
        return {"message": msg, "action": None, "url": None}

    # Navigate to External Website
    elif intent == "navigate_external":
        website = entities.get("website")
        if website:
            if website in EXTERNAL_URLS:
                target_url = EXTERNAL_URLS[website]
                msg = f"Sure! Taking you to {website.title()} now!"
                return {"message": msg, "action": "redirect", "url": target_url}
            else:
                # Clean the website name for URL formatting
                target_url = website
                for tld in [".com", ".org", ".net", ".io", ".co"]:
                    if target_url.endswith(tld):
                        target_url = target_url[:-len(tld)]
                        break
                if not target_url.startswith(("http://", "https://")):
                    target_url = f"https://{target_url}.com"
                display_name = website.split('.')[0].title()
                msg = f"Sure! Opening {display_name} for you now!"
                return {"message": msg, "action": "redirect", "url": target_url}
        else:
            msg = "I didn't catch which website you want to go to. Try saying 'go to YouTube' or 'open Google'."
            return {"message": msg, "action": None, "url": None}

    # Unknown
    else:
        text_lower = context.history[-1]["text"] if context.history else ""
        if "?" in text_lower or text_lower.startswith(("what","how","why","when","where","who","can","is","are","do","does")):
            msg = f"That's a good question! I'm focused on your kitchen and reminders. Try asking me: what can I cook, show my reminders, or what's expiring?"
        else:
            msg = pick("unknown")
        return {"message": msg, "action": None, "url": None}


# ── Main Entry Point ──────────────────────────────────────────────────────────
_contexts = {}

def get_context(user_id):
    if user_id not in _contexts:
        _contexts[user_id] = ConversationContext()
    return _contexts[user_id]

def clear_context(user_id):
    if user_id in _contexts:
        _contexts[user_id].clear()


def process_message(user_message, user):
    context = get_context(user.id)
    intent = detect_intent(user_message)
    entities = extract_entities(user_message)
    live_data = get_live_data(user)

    context.add("user", user_message, intent)
    context.last_intent = intent
    context.last_entities = entities

    result = build_response(intent, entities, live_data, user, context)
    context.add("aria", result["message"], intent)

    return {
        "message": result["message"],
        "action": result.get("action"),
        "url": result.get("url"),
        "data": result.get("data"),
        "intent": intent,
        "entities": entities,
    }
