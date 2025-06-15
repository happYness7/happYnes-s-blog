# 在 apps/blog/serializers.py 中创建
from rest_framework import serializers
from .models import Category, Tag, Article, ArticleTag, Comment, Config, PhotoAlbum, Photo
from apps.user.models import SysUserSerializer, SysUser  # 引用用户序列化器


class CategorySerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")

    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TagSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")

    class Meta:
        model = Tag
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ArticleSerializer(serializers.ModelSerializer):
    # 显示关联对象详细信息
    author = SysUserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True  # 仅在写入时生效
    )

    class Meta:
        model = Article
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'author', 'tags')


class ArticleTagSerializer(serializers.ModelSerializer):
    article = serializers.StringRelatedField()
    tag = serializers.StringRelatedField()

    class Meta:
        model = ArticleTag
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class CommentSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    from_user = SysUserSerializer(read_only=True)
    from_user_id = serializers.PrimaryKeyRelatedField(
        queryset=SysUser.objects.all(),
        source='from_user',
        write_only=True,  # 仅在写入时生效
        allow_null=True
    )

    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Config
        fields = '__all__'


class PhotoAlbumSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)

    class Meta:
        model = PhotoAlbum
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class PhotoSerializer(serializers.ModelSerializer):
    STATUS_DISPLAY = serializers.CharField(source='get_status_display', read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    album = PhotoAlbumSerializer(read_only=True)  # 读取时显示完整相册信息
    album_id = serializers.PrimaryKeyRelatedField(
        queryset=PhotoAlbum.objects.all(),
        source='album',
        write_only=True,  # 写入时使用ID字段
        allow_null=True,
        required=False
    )

    class Meta:
        model = Photo
        fields = [
            'id', 'album', 'album_id', 'url', 'status', 'STATUS_DISPLAY',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at', 'STATUS_DISPLAY')
