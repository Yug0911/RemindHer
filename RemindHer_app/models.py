from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, name, email, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(name=name, email=email, status='Active')
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, name, email, password):
        user = self.create_user(name, email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email

# class VoiceResponse(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     question = models.CharField(max_length=255)
#     response = models.CharField(max_length=255)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.question} - {self.response} by {self.user.email}"

class Reminder(models.Model):
    REMINDER_TYPES = [('Once', 'Once'), ('Daily', 'Daily')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    task = models.CharField(max_length=255)
    task_time = models.TimeField()
    task_date = models.DateField()
    reminder_type = models.CharField(max_length=10, choices=REMINDER_TYPES, default='Once')
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.task} for {self.user.email} on {self.task_date} at {self.task_time}"
    



class AddTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task_name = models.CharField(max_length=255)
    task_time = models.TimeField()
    task_date = models.DateField()
    reminder_type = models.CharField(max_length=10, choices=[('Once', 'Once'), ('Daily', 'Daily')])
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.task_name} for {self.user.email} on {self.task_date} at {self.task_time}"

class UserPreferences(models.Model):
    DIETARY_CHOICES = [
        ('None', 'None'),
        ('Vegetarian', 'Vegetarian'),
        ('Vegan', 'Vegan'),
        ('Keto', 'Keto'),
        ('Paleo', 'Paleo'),
        ('Gluten-Free', 'Gluten-Free'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dietary_preferences = models.CharField(max_length=20, choices=DIETARY_CHOICES, default='None')
    allergies = models.TextField(blank=True, help_text="Comma-separated list of allergies")
    cooking_skill_level = models.CharField(max_length=20, choices=[
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ], default='Intermediate')

    def __str__(self):
        return f"Preferences for {self.user.email}"

class InventoryItem(models.Model):
    CATEGORY_CHOICES = [
        ('Fridge', 'Fridge'),
        ('Pantry', 'Pantry'),
        ('Freezer', 'Freezer'),
        ('Spices', 'Spices'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=50, default='pieces')  # e.g., kg, liters, pieces
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Other')
    expiration_date = models.DateField(null=True, blank=True)
    added_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=1)

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit}) - {self.user.email}"

    @property
    def is_expired(self):
        if self.expiration_date:
            from django.utils import timezone
            return self.expiration_date < timezone.now().date()
        return False

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

class Recipe(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    ingredients = models.JSONField(help_text="List of ingredients with quantities")
    instructions = models.JSONField(help_text="Step-by-step instructions")
    prep_time = models.PositiveIntegerField(help_text="Preparation time in minutes")
    cook_time = models.PositiveIntegerField(help_text="Cooking time in minutes")
    servings = models.PositiveIntegerField(default=4)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    nutritional_info = models.JSONField(blank=True, null=True, help_text="Calories, protein, carbs, etc.")
    tags = models.JSONField(blank=True, null=True, help_text="Tags like 'vegan', 'quick', etc.")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroceryList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default="My Grocery List")
    items = models.JSONField(default=list, help_text="List of items to buy with quantities")
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.user.email}"

class CookingSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_step = models.PositiveIntegerField(default=1)
    timers = models.JSONField(blank=True, null=True, help_text="Active timers for the session")

    def __str__(self):
        return f"Cooking {self.recipe.name} by {self.user.email}"