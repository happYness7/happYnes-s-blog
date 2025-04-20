from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SysRoleViewSet

router = DefaultRouter()
router.register('', SysRoleViewSet, basename='role')  # 注册 RoleViewSet

urlpatterns = [
    path('', include(router.urls)),  # 包含 DRF 路由
]
