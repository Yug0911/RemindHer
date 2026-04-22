# RemindHer - Smart Reminder & Kitchen Assistant

## Project Overview

**RemindHer** is a comprehensive Django-based web application designed as a smart personal assistant, primarily focused on helping users manage daily reminders and kitchen-related tasks. The application combines intelligent reminder management with inventory tracking, recipe suggestions, grocery list management, and interactive cooking sessions.

---

## Core Features

### 1. 🔔 Smart Reminder System
- Create reminders for one-time or daily tasks
- Set specific date and time for reminders
- View all active and completed reminders
- Snooze or cancel existing reminders
- Track reminder completion status

### 2. 🎤 Voice Assistant
- Voice-based command processing
- Voice questionnaire for user preferences
- Text-to-speech (TTS) for audio feedback
- Speech recognition for voice input
- Natural language processing for commands
- **External website navigation** - Redirect to YouTube, Google, Facebook, Instagram, Netflix, Reddit, and other popular sites via voice commands

### 3. 📦 Inventory Management
- Track household items across categories (Fridge, Pantry, Freezer, Spices)
- Record quantities and units (kg, liters, pieces)
- Set expiration date tracking with automatic alerts
- Low-stock threshold notifications
- Automatic expiration warnings

### 4. 🍳 Recipe Management
- Browse and manage recipes with detailed instructions
- Recipe database with ingredients and step-by-step directions
- Prep time and cook time tracking
- Serving size and difficulty level
- Nutritional information storage
- Tags and dietary categorization

### 5. 💡 Smart Recipe Suggestions
- AI-powered recipe recommendations based on available inventory
- Filter recipes by dietary preferences
- Account for user allergies and restrictions
- Suggest recipes based on expiring ingredients

### 6. 🛒 Grocery List Management
- Create and manage shopping lists
- Add, update, and delete items
- Mark items as purchased
- Auto-suggest items based on inventory
- Create reminders for grocery shopping

### 7. 👩‍🍳 Interactive Cooking Sessions
- Step-by-step guided cooking
- Built-in timers for each cooking step
- Progress tracking through recipe steps
- Session completion logging

### 8. 👤 User Preferences & Profile
- Dietary preferences (Vegetarian, Vegan, Keto, Paleo, Gluten-Free)
- Allergy tracking
- Cooking skill level (Beginner, Intermediate, Advanced)
- User authentication and profile management

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | Django 5.1.7 |
| **REST API** | Django REST Framework 3.15.2 |
| **Authentication** | Django-allauth 65.4.1 |
| **Task Scheduling** | Celery 5.4.0 + Django-Celery-Beat 2.7.0 |
| **Data Processing** | NumPy 2.2.4, Pandas 2.2.3 |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Database** | SQLite3 (Development) |
| **Date Parsing** | dateparser 1.2.1 |

---

## Project Structure

```
RemindHer-master/
├── RemindHer/                 # Django project configuration
│   ├── settings.py           # Project settings
│   ├── urls.py               # Main URL configuration
│   ├── celery.py             # Celery configuration
│   └── wsgi.py               # WSGI application
│
├── RemindHer_app/            # Main application
│   ├── models.py             # Database models
│   ├── views.py              # View functions and API endpoints
│   ├── urls.py               # App URL routing
│   ├── serializers.py       # DRF serializers
│   ├── admin.py              # Django admin configuration
│   │
│   ├── templates/            # HTML templates
│   │   ├── landing.html      # Dashboard/home page
│   │   ├── create_reminder.html
│   │   ├── view_reminders.html
│   │   ├── voice_assistant.html
│   │   ├── questionnaire.html
│   │   ├── inventory.html
│   │   ├── recipes.html
│   │   ├── recipe_suggestions.html
│   │   ├── grocery_list.html
│   │   ├── cooking_session.html
│   │   └── Login.html
│   │
│   ├── static/               # Static assets
│   │   ├── css/              # Stylesheets
│   │   ├── js/               # JavaScript files
│   │   └── images/           # Image assets
│   │
│   └── utils/                # Utility modules
│       └── voice_assistant.py
│
├── requirements.txt          # Python dependencies
├── manage.py                 # Django management script
└── db.sqlite3               # SQLite database
```

---

## Database Models

### User
- Email-based authentication
- Name and status fields
- Custom user manager

### Reminder
- Task description, time, and date
- Reminder type (Once/Daily)
- Completion status tracking

### AddTask
- Additional task management model
- Similar to Reminder with flexible scheduling

### UserPreferences
- Dietary preferences (None, Vegetarian, Vegan, Keto, Paleo, Gluten-Free)
- Allergy tracking
- Cooking skill level

### InventoryItem
- Name, quantity, and unit
- Category (Fridge, Pantry, Freezer, Spices, Other)
- Expiration date with auto-detection
- Low-stock threshold alerts
- Auto-updated timestamps

### Recipe
- Name and description
- Ingredients and instructions (JSON)
- Prep and cook time
- Difficulty level
- Nutritional information
- Tags for categorization

### GroceryList
- User-associated shopping lists
- Items stored as JSON
- Completion status

### CookingSession
- Associated with a recipe
- Step-by-step progress tracking
- Timer management
- Session start and completion timestamps

---

## API Endpoints

### Authentication
- `/api-register/` - User registration
- `/api-login/` - User login

### Reminders
- `/create-reminder/` - Create new reminder
- `/view_reminders/` - List user reminders
- `/snooze/<id>/<minutes>/` - Snooze reminder
- `/cancel/<id>/` - Cancel reminder

### Inventory
- `/inventory/` - List inventory items
- `/inventory/add/` - Add new item
- `/inventory/update/<id>/` - Update item
- `/inventory/delete/<id>/` - Delete item
- `/inventory/alerts/` - Get expiring/low-stock alerts

### Recipes
- `/recipes/` - List all recipes
- `/recipes/suggest/` - Get recipe suggestions

### Cooking Sessions
- `/cooking/start/<id>/` - Start cooking session
- `/cooking/session/<id>/` - View/update session
- `/cooking/update-step/<id>/` - Update cooking step
- `/cooking/set-timer/<id>/` - Set cooking timer

### Grocery
- `/grocery/` - View grocery list
- `/grocery/add/` - Add item
- `/grocery/update/<index>/` - Update item
- `/grocery/delete/<index>/` - Delete item
- `/grocery/complete/` - Complete shopping

---

## Key Features Breakdown

### Voice Questionnaire Flow
1. User initiates voice questionnaire
2. System asks questions about dietary preferences
3. User responds via voice input
4. Responses are processed and stored in UserPreferences
5. Preferences are used for recipe suggestions

### Supported Voice Commands
The voice assistant (ARIA) supports various commands including:

| Command Type | Examples |
|-------------|----------|
| **Reminders** | "Remind me to...", "Set a reminder for..." |
| **Inventory** | "Check my inventory", "What's in my fridge?" |
| **Recipes** | "What can I cook?", "Suggest a recipe" |
| **Grocery** | "Show my shopping list", "Add to grocery" |
| **Website Navigation** | "Go to YouTube", "Open Google", "Redirect me to Netflix" |

#### Supported External Websites
- YouTube, Google, Facebook, Instagram, Twitter/X, Reddit
- GitHub, StackOverflow, Netflix, Amazon, Wikipedia
- WhatsApp, LinkedIn, TikTok

### Inventory Alerts
- Automatic detection of expired items
- Low-stock threshold warnings
- Alerts displayed on dashboard
- Integration with grocery list for auto-suggestions

### Recipe Suggestions Algorithm
1. Get user's available inventory
2. Filter by dietary preferences and allergies
3. Match ingredients with recipe requirements
4. Prioritize recipes using soon-to-expire items
5. Return ranked suggestions

### Cooking Session Features
- Step-by-step instruction display
- Built-in countdown timers
- Progress tracking (current step / total steps)
- Audio notifications via TTS

---

## Security Features

- Django authentication system
- CSRF protection
- Password hashing
- Session management
- User-specific data isolation

---

## Installation & Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Start development server:**
   ```bash
   python manage.py runserver
   ```

4. **Access the application:**
   Navigate to `http://localhost:8000`

---

## Target Audience

Primarily designed for home users, especially:
- Busy professionals managing household tasks
- Home cooks looking for recipe management
- Anyone needing smart reminder assistance

---

## Future Enhancements

- Mobile application development
- Push notification integration
- Email reminders
- Shopping automation
- Social recipe sharing
- Meal planning calendar
- Nutritional tracking dashboard