# RemindHer Deployment Guide - PythonAnywhere

## Prerequisites
- GitHub account with your project pushed
- PythonAnywhere account (free)

---

## Step 1: Sign Up

1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Click "Register"
3. Sign up with GitHub or email
4. Choose "Beginner" account type

---

## Step 2: Clone Your Repository

1. Open **Consoles** tab → Start new bash console
2. Run:
   ```bash
   git clone https://github.com/Yug0911/RemindHer.git
   ```
3. Navigate to project:
   ```bash
   cd RemindHer
   ```

---

## Step 3: Create Virtual Environment

```bash
mkvirtualenv venv --python=python3.12
```

Or if that doesn't work:
```bash
python3.12 -m venv venv
source venv/bin/activate
```

---

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 5: Configure Settings

Edit `RemindHer/settings.py`:

```python
# Around line 27
DEBUG = False

# Around line 29
ALLOWED_HOSTS = ['yourusername.pythonanywhere.com']
```

**Replace `yourusername` with your PythonAnywhere username**

---

## Step 6: Run Migrations

```bash
python manage.py migrate
```

---

## Step 7: Create Superuser

```bash
python manage.py createsuperuser
```

Enter your admin credentials.

---

## Step 8: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

---

## Step 9: Configure Web App

1. Go to **Web** tab
2. Click **Add new web app**
3. Select **manual configuration**
4. Select **Python 3.12**
5. Click **Next**

### Configure WSGI:

Click on the WSGI config file link and replace content with:

```python
"""
WSGI config for RemindHer project.
"""
import os
import sys

# Add project directory to path
path = '/home/yourusername/RemindHer'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'RemindHer.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Replace `yourusername` with your actual username**

---

## Step 10: Configure Static Files

In the Web tab:

1. Find **Static files** section
2. Add:
   - URL: `/static/`
   - Directory: `/home/yourusername/RemindHer/staticfiles`

---

## Step 11: Verify & Reload

1. Go to Web tab
2. Click **Reload** button
3. Visit `https://yourusername.pythonanywhere.com`

---

## Troubleshooting

### 500 Error
- Check error logs in Web tab
- Common fix:
  ```bash
  python manage.py migrate
  python manage.py collectstatic
  ```

### Static files not loading
- Verify static files config in Web tab
- Check directory path is correct

---

## Your Project is Ready! ✓