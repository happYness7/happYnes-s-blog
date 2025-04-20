from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.user.views import LoginView, ImageView, AvatarView, SysUserViewSet

router = DefaultRouter()
router.register('', SysUserViewSet, basename='user')  # 使用复数形式表示资源集合

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),  # 登录路由
    path('upload-image/', ImageView.as_view(), name='upload-image'),  # 图片上传路由
    path('update-avatar/', AvatarView.as_view(), name='update-avatar'),  # 头像更新路由
    path('', include(router.urls)),  # 包含 DRF 路由
]
