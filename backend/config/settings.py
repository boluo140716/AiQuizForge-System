import os
from pathlib import Path
from datetime import timedelta
from decouple import config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='change-me-in-production-!@#$%')

DEBUG = True
ALLOWED_HOSTS = []

# ===== 应用注册 =====
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 第三方
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    # 本地应用
    'users',
    'notes',
]

# ===== 中间件 =====
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',      
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ===== 数据库配置（MySQL）=====
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='quizforge_db'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

# ===== Redis 配置 =====
REDIS_HOST = config('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = config('REDIS_PORT', default='6379')

REDIS_PASSWORD = config('REDIS_PASSWORD', default='')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ===== 用户模型 =====
AUTH_USER_MODEL = 'users.User'

# ===== 密码验证 =====
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===== 国际化 =====
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

# 媒体文件配置（用户上传头像等）
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===== REST Framework 配置 =====
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS':[
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',    
    ],
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        'generate_quiz': '5/min',  # 每分钟最多生成5个测验
    },
}

# ===== JWT 配置 =====
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=180),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ===== CORS 跨域配置 =====
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True



#异步任务配置
CELERY_BROKER_URL = f'redis://:{config("REDIS_PASSWORD", default="")}@{config("REDIS_HOST", default="127.0.0.1")}:{config("REDIS_PORT", default="6379")}/0'
CELERY_RESULT_BACKEND = f'redis://:{config("REDIS_PASSWORD", default="")}@{config("REDIS_HOST", default="127.0.0.1")}:{config("REDIS_PORT", default="6379")}/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Shanghai'

# ===== Celery 可靠性配置 =====
CELERY_TASK_ACKS_LATE = True                    # 任务执行完才确认；worker 崩溃时任务可重投
CELERY_TASK_REJECT_ON_WORKER_LOST = True        # worker 掉线，任务退回队列
CELERY_TASK_ACKS_ON_FAILURE_OR_TIMEOUT = False  # 失败/超时不提前确认（交给重试与看门狗）
CELERY_WORKER_PREFETCH_MULTIPLIER = 1           # 一次只取一个任务，避免任务囤积在单个 worker
CELERY_TASK_TIME_LIMIT = 300                    # 单任务硬超时 5 分钟
CELERY_TASK_SOFT_TIME_LIMIT = 240               # 单任务软超时 4 分钟（可捕获做清理）

# 看门狗：超过该分钟数仍无心跳更新的 processing 任务，视为卡死并回收
QUIZ_STUCK_MINUTES = 10

# Celery Beat 定时任务：每 2 分钟跑一次看门狗
CELERY_BEAT_SCHEDULE = {
    'reap-stuck-quizzes': {
        'task': 'notes.task.reap_stuck_quizzes',
        'schedule': 120.0,
    },
}

# ===== AI 服务配置 =====
AI_SERVICE_URL = config('AI_SERVICE_URL', default='http://127.0.0.1:8001')
AI_SERVICE_TOKEN = config('AI_SERVICE_TOKEN', default='quizforge-internal-secret-token-2026')