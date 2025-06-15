from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.blog.views import ArticleViewSet, CategoryViewSet, TagViewSet, PhotoViewSet, \
    PhotoAlbumViewSet, ConfigViewSet, CommentViewSet

router = DefaultRouter()
router.register('articles', ArticleViewSet, basename='article')
router.register('categories', CategoryViewSet, basename='category')
router.register('tags', TagViewSet, basename='tag')
router.register('photos', PhotoViewSet, basename='photo')
router.register('albums', PhotoAlbumViewSet, basename='album')
router.register('configs', ConfigViewSet, basename='config'),
router.register('comments', CommentViewSet, basename='comment'),
urlpatterns = [
    path('', include(router.urls)),
]
