from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.user.views import LoginView, AvatarView, SysUserViewSet, CaptchaView, RegisterView

router = DefaultRouter()
router.register('', SysUserViewSet, basename='user')  # 使用复数形式表示资源集合

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),  # 登录路由
    path('register/', RegisterView.as_view(), name='register'),
    path('captcha/', CaptchaView.as_view(), name='captcha'),
    path('update-avatar/', AvatarView.as_view(), name='update-avatar'),  # 头像更新路由
    path('', include(router.urls)),  # 包含 DRF 路由
]
