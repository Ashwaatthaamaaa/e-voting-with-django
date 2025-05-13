# e_voting/settings.py
"""
Django settings for e_voting project.
... (rest of the initial comments) ...
"""

from pathlib import Path
import os
import dj_database_url # <--- Import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '%6lp_p!%r$7t-2ql5hc5(r@)8u_fc+6@ugxcnz=h=b(fn#3$p9')

# SECURITY WARNING: don't run with debug turned on in production!
# Railway sets NODE_ENV=production automatically, you can use that or create your own like DJANGO_DEBUG
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# ALLOWED_HOSTS should include your Railway app's domain(s)
# Railway provides a default domain and you can add custom ones.
# Example: ALLOWED_HOSTS = ['myapp-production.up.railway.app', 'www.mycustomdomain.com']
# You can get this from the RAILWAY_PUBLIC_DOMAIN env var or set it manually.
ALLOWED_HOSTS = [os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'localhost'), '127.0.0.1']
# If using Railway's private networking, add the private URL if needed.

# CSRF Trusted Origins for secure POST requests
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host not in ['localhost', '127.0.0.1']]
if 'localhost' in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.append('http://localhost:8000') # Add local dev if needed
    CSRF_TRUSTED_ORIGINS.append('http://127.0.0.1:8000') # Add local dev if needed


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles', # Needed for collectstatic

    # My Created Applications
    'account.apps.AccountConfig',
    'voting.apps.VotingConfig',
    'administrator.apps.AdministratorConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # <-- Add WhiteNoise for static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'account.middleware.AccountCheckMiddleWare',
]

ROOT_URLCONF = 'e_voting.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates'), 'voting/templates', 'administrator/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'voting.context_processors.ElectionTitle'
            ],
        },
    },
]

WSGI_APPLICATION = 'e_voting.wsgi.application'


# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

# settings.py DATABASES section

# Default database configuration (e.g., for local development without DATABASE_URL)
DEFAULT_DB_CONFIG = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': BASE_DIR / 'db.sqlite3',
}

# Parse the DATABASE_URL environment variable
db_config = dj_database_url.config(
    default=os.environ.get('DATABASE_URL'),
    conn_max_age=600,
    conn_health_checks=True,
)

# If DATABASE_URL was not found or is empty, fall back to default
if not db_config:
     print("DATABASE_URL environment variable not found, falling back to default DB config.")
     DATABASES = {'default': DEFAULT_DB_CONFIG}
else:
     # No engine override needed for mysqlclient, dj-database-url default is fine
     DATABASES = {'default': db_config}
# Password validation
# ... (AUTH_PASSWORD_VALIDATORS remains the same) ...

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
# ... (LANGUAGE_CODE, TIME_ZONE, USE_I18N, USE_L10N, USE_TZ remain the same) ...
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True # Deprecated in Django 4.0+
USE_TZ = True

# Static files (CSS, JavaScript, Images) & Media Files
# https://docs.djangoproject.com/en/stable/howto/static-files/
# https://docs.djangoproject.com/en/stable/howto/static-files/deployment/
# https://whitenoise.readthedocs.io/

STATIC_URL = '/static/'
# This is where Django will look for static files in development
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# This is where collectstatic will copy files for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Simplified static file serving. Add 'whitenoise.middleware.WhiteNoiseMiddleware' to MIDDLEWARE
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') # Standard location

# Custom User Model & Auth Backend
AUTH_USER_MODEL = 'account.CustomUser'
AUTHENTICATION_BACKENDS = ['account.email_backend.EmailBackend']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Other Settings
ELECTION_TITLE_PATH = os.path.join(BASE_DIR, 'election_title.txt')

# Manage SEND_OTP via environment variable
SEND_OTP = os.environ.get('SEND_OTP', 'False') == 'True'

# SMS Gateway Credentials (using environment variables is recommended)
SMS_EMAIL = os.environ.get('SMS_EMAIL')
SMS_PASSWORD = os.environ.get('SMS_PASSWORD')
SMS_SENDER_NAME = os.environ.get('SMS_SENDER_NAME', 'E-Voting')

# Add Gunicorn if using it (recommended for production)
# INSTALLED_APPS += ['gunicorn'] # Add if not already managed by Railway buildpack/Nixpacks