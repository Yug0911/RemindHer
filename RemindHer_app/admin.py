from django.contrib import admin
from .models import CustomUser, Reminder, UserPreferences, InventoryItem, Recipe, GroceryList, CookingSession

admin.site.register(CustomUser)
admin.site.register(Reminder)
admin.site.register(UserPreferences)
admin.site.register(InventoryItem)
admin.site.register(Recipe)
admin.site.register(GroceryList)
admin.site.register(CookingSession)
