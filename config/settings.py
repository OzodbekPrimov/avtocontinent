import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'modeltranslation',  # modeltranslation birinchi bo‘lishi kerak
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # For number formatting
    'store',
    'dashboard',
    'ckeditor',
    'ckeditor_uploader',
    'admin_thumbnails',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'django.middleware.locale.LocaleMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.categories',
                'store.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'avto',
        'USER': 'postgres',
        'PASSWORD': 'ozodbek2006',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'file': {
#             'level': 'INFO',
#             'class': 'logging.FileHandler',
#             'filename': 'debug.log',
#         },
#     },
#     'loggers': {
#         '': {
#             'handlers': ['file'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#     },
# }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Languages
LANGUAGES = [
    ('uz', 'O\'zbekcha'),
    ('ru', 'Русский'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]


# Modeltranslation sozlamalari
MODELTRANSLATION_DEFAULT_LANGUAGE = 'uz'  # Asosiy til
MODELTRANSLATION_LANGUAGES = ('uz', 'en', 'ru')

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CKEditor Configuration
CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': 'auto',
    },
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# Authentication settings - Removed global settings to avoid conflicts
# Each app will handle its own authentication redirects

# Email configuration (for production)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = '7849223276:AAHo4EAuyoTz_wF6CZ0J9vWlTdCBsE37mXQ'
TELEGRAM_BOT_USERNAME = 'avtokon_bot'
TELEGRAM_ADMIN_CHAT_ID = 6215451224
ADMIN_PHONE_NUMBER = 772225555
# Site settings
SITE_NAME = 'Avtokontinent.uz'
SITE_DESCRIPTION = 'Online Auto Spare Parts Store'

TELEGRAM_AUTH_EXPIRY_MINUTES = 5
MAX_LOGIN_ATTEMPTS = 3
AUTH_CLEANUP_INTERVAL_HOURS = 1

import os
from celery import Celery

# Celery sozlamalari
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('store')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# # Celery sozlamalari
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'





