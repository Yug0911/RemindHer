from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class Reminder(models.Model):
    TYPE_CHOICES = [('once', 'Once'), ('daily', 'Daily')]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reminders')
    task = models.CharField(max_length=255)
    reminder_time = models.TimeField()
    reminder_date = models.DateField()
    reminder_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='once')
    is_completed = models.BooleanField(default=False)
    is_snoozed = models.BooleanField(default=False)
    snooze_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task} for {self.user.email}"


class UserPreferences(models.Model):
    DIET_CHOICES = [
        ('none', 'None'),
        ('vegetarian', 'Vegetarian'),
        ('vegan', 'Vegan'),
        ('keto', 'Keto'),
        ('paleo', 'Paleo'),
        ('gluten_free', 'Gluten-Free')
    ]
    SKILL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='preferences')
    dietary_preference = models.CharField(max_length=20, choices=DIET_CHOICES, default='none')
    allergies = models.TextField(blank=True)
    cooking_skill = models.CharField(max_length=20, choices=SKILL_CHOICES, default='beginner')
    voice_enabled = models.BooleanField(default=True)

    def get_allergies_list(self):
        return [a.strip() for a in self.allergies.split(',') if a.strip()]

    def __str__(self):
        return f"Preferences for {self.user.email}"


class InventoryItem(models.Model):
    CATEGORY_CHOICES = [
        ('fridge', 'Fridge'),
        ('pantry', 'Pantry'),
        ('freezer', 'Freezer'),
        ('spices', 'Spices'),
        ('other', 'Other')
    ]
    UNIT_CHOICES = [
        ('kg', 'kg'),
        ('g', 'g'),
        ('liters', 'liters'),
        ('ml', 'ml'),
        ('pieces', 'pieces'),
        ('cups', 'cups'),
        ('tbsp', 'tbsp'),
        ('tsp', 'tsp')
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='inventory')
    name = models.CharField(max_length=100)
    quantity = models.FloatField(default=1.0)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pieces')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='pantry')
    expiration_date = models.DateField(null=True, blank=True)
    low_stock_threshold = models.FloatField(default=1.0)
    updated_at = models.DateTimeField(auto_now=True)

    def is_expired(self):
        return self.expiration_date and self.expiration_date < timezone.now().date()

    def days_until_expiry(self):
        if self.expiration_date:
            return (self.expiration_date - timezone.now().date()).days
        return None

    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


class Recipe(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ingredients = models.JSONField(default=list)
    instructions = models.JSONField(default=list)
    prep_time = models.IntegerField(default=0)
    cook_time = models.IntegerField(default=0)
    servings = models.IntegerField(default=2)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    dietary_tags = models.CharField(max_length=200, blank=True)
    nutritional_info = models.JSONField(default=dict, blank=True)

    def get_tags(self):
        return [t.strip() for t in self.dietary_tags.split(',') if t.strip()]

    def __str__(self):
        return self.name


class GroceryList(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='grocery_lists')
    name = models.CharField(max_length=100, default='Shopping List')
    items = models.JSONField(default=list)
    is_completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.email}"


class CookingSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    current_step = models.IntegerField(default=0)
    total_steps = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    timer_end = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def get_progress_percentage(self):
        if self.total_steps == 0:
            return 0
        return int((self.current_step / self.total_steps) * 100)

    def __str__(self):
        return f"Cooking {self.recipe.name} by {self.user.email}"