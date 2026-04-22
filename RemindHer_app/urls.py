from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('splashscreen/', views.splashscreen, name='splashscreen'),

    # Reminders
    path('create-reminder/', views.create_reminder, name='create_reminder'),
    path('view_reminders/', views.view_reminders, name='view_reminders'),
    path('snooze/<int:pk>/<int:minutes>/', views.snooze_reminder, name='snooze_reminder'),
    path('cancel/<int:pk>/', views.cancel_reminder, name='cancel_reminder'),
    path('complete/<int:pk>/', views.complete_reminder, name='complete_reminder'),

    # Voice Assistant (ARIA)
    path('voice/', views.voice_assistant_page, name='voice_assistant'),
    path('voice/chat/', views.voice_chat, name='voice_chat'),
    path('voice/clear/', views.voice_clear_history, name='voice_clear'),

    # Inventory
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/add/', views.inventory_add, name='inventory_add'),
    path('inventory/update/<int:pk>/', views.inventory_update, name='inventory_update'),
    path('inventory/delete/<int:pk>/', views.inventory_delete, name='inventory_delete'),
    path('inventory/alerts/', views.inventory_alerts, name='inventory_alerts'),

    # Recipes
    path('recipes/', views.recipes, name='recipes'),
    path('recipes/suggest/', views.recipe_suggestions, name='recipe_suggestions'),

    # Cooking Sessions
    path('cooking/start/<int:recipe_id>/', views.start_cooking, name='start_cooking'),
    path('cooking/session/<int:pk>/', views.cooking_session_view, name='cooking_session'),
    path('cooking/update-step/<int:pk>/', views.update_step, name='update_step'),
    path('cooking/set-timer/<int:pk>/', views.set_timer, name='set_timer'),

    # Grocery
    path('grocery/', views.grocery_list_view, name='grocery_list'),
    path('grocery/add/', views.grocery_add, name='grocery_add'),
    path('grocery/toggle/<int:index>/', views.grocery_toggle, name='grocery_toggle'),
    path('grocery/delete/<int:index>/', views.grocery_delete, name='grocery_delete'),
    path('grocery/complete/', views.grocery_complete, name='grocery_complete'),

    # User Preferences
    path('preferences/', views.user_preferences, name='preferences'),
]
