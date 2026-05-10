from django.urls import path
from .views import RegisterView, MeView,ProfileView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),  
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  
    path('me/', MeView.as_view(), name='me'),  
    path('profile/', ProfileView.as_view(), name='profile'),
]