# from django.urls import path
# from . import views

# urlpatterns = [
#     path('login/', views.Login_view, name='login'),
#     path('register/', views.Register_view, name='register'),
#     path('', views.splashscreen, name='splashscreen'),
    
#     #api endpoints
#     path('api-register/', views.RegisterView.as_view(), name='api-register'),
#     path('api-login/', views.LoginView.as_view(), name='api-login'),
    
#     path('create/', views.create_reminder, name='create_reminder'),
#     path('snooze/<int:reminder_id>/<int:minutes>/', views.snooze_reminder, name='snooze_reminder'),
#     path('cancel/<int:reminder_id>/', views.cancel_reminder, name='cancel_reminder'),
#     path('check_reminders/', views.check_reminders, name='check_reminders'),
# ]
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.Login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.Register_view, name='register'),
    path('', views.splashscreen, name='splashscreen'),

    # API Endpoints
    path('api-register/', views.RegisterView.as_view(), name='api-register'),
    path('api-login/', views.LoginView.as_view(), name='api-login'),

    # Reminder Endpoints
    path('create-reminder/', views.create_reminder, name='create_reminder'),
    path('start-questionnaire/', views.start_questionnaire, name='start_questionnaire'),  # New URL
    path('voice-create/', views.create_reminder, name='voice_create_reminder'),
    path('snooze/<int:reminder_id>/<int:minutes>/', views.snooze_reminder, name='snooze_reminder'),
    path('cancel/<int:reminder_id>/', views.cancel_reminder, name='cancel_reminder'),
    path('check_reminders/', views.check_reminders, name='check_reminders'),
    path('view_reminders/', views.view_reminders, name='view_reminders'),
    path('landing/', views.landing, name='landing'),

    # Inventory Endpoints
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add/', views.add_inventory_item, name='add_inventory_item'),
    path('inventory/update/<int:item_id>/', views.update_inventory_item, name='update_inventory_item'),
    path('inventory/delete/<int:item_id>/', views.delete_inventory_item, name='delete_inventory_item'),
    path('inventory/alerts/', views.get_inventory_alerts, name='inventory_alerts'),
    path('voice-command/', views.process_voice_command, name='process_voice_command'),
    path('voice-assistant/', views.voice_assistant, name='voice_assistant'),

    # Recipe Endpoints
    path('recipes/', views.recipe_list, name='recipe_list'),
    path('recipes/suggest/', views.suggest_recipes, name='suggest_recipes'),
    path('cooking/start/<int:recipe_id>/', views.start_cooking_session, name='start_cooking_session'),
    path('cooking/session/<int:session_id>/', views.cooking_session, name='cooking_session'),
    path('cooking/update-step/<int:session_id>/', views.update_cooking_step, name='update_cooking_step'),
    path('cooking/set-timer/<int:session_id>/', views.set_cooking_timer, name='set_cooking_timer'),

    # Grocery List Endpoints
    path('grocery/', views.grocery_list_view, name='grocery_list'),
    path('grocery/add/', views.add_grocery_item, name='add_grocery_item'),
    path('grocery/update/<int:item_index>/', views.update_grocery_item, name='update_grocery_item'),
    path('grocery/delete/<int:item_index>/', views.delete_grocery_item, name='delete_grocery_item'),
    path('grocery/complete/', views.complete_grocery_list, name='complete_grocery_list'),
    path('grocery/suggestions/', views.get_grocery_suggestions, name='grocery_suggestions'),
    path('grocery/reminder/', views.create_grocery_reminder, name='create_grocery_reminder'),
]
