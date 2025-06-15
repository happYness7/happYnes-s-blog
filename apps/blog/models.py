from django.db import models


class Category(models.Model):
    category_name = models.CharField(max_length=55, unique=True, verbose_name="分类名称")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = 'blog_category'
        verbose_name = '文章分类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.category_name


class Tag(models.Model):
    tag_name = models.CharField(max_length=55, unique=True, verbose_name="标签名称")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = 'blog_tag'
        verbose_name = '文章标签'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.tag_name


class Article(models.Model):
    STATUS_CHOICES = (
        (1, '公开'),
        (2, '私密'),
        (3, '草稿箱')
    )
    TYPE_CHOICES = (
        (1, '原创'),
        (2, '转载'),
        (3, '翻译')
    )

    article_title = models.CharField(max_length=255, verbose_name="文章标题")
    author = models.ForeignKey('user.SysUser', on_delete=models.CASCADE, verbose_name="作者", default=1)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name="分类")
    article_content = models.TextField(verbose_name="文章内容")
    article_cover = models.CharField(max_length=1234, verbose_name="封面图",
                                     default='https://pub-d470eef1ae124f929afa0d8350e779c7.r2.dev/blog/article_cover/ff1fe06c6e6947608dcb489277d237d3.jpg')
    is_top = models.IntegerField(choices=[(1, '置顶'), (2, '不置顶')], default=2, verbose_name="置顶状态")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="文章状态")
    type = models.IntegerField(choices=TYPE_CHOICES, default=1, verbose_name="文章类型")
    article_description = models.CharField(max_length=255, verbose_name="文章摘要")
    order = models.IntegerField(null=True, blank=True, verbose_name="排序权重")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")
    tags = models.ManyToManyField(Tag, through='ArticleTag', verbose_name="文章标签", related_name='article_tags')

    class Meta:
        db_table = 'blog_article'
        ordering = ['-created_at']
        verbose_name = '文章管理'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['-created_at'], name='create_time_idx'),
        ]

    def __str__(self):
        return self.article_title


class ArticleTag(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, verbose_name="文章")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, verbose_name="标签")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="关联时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = 'blog_article_tag'
        verbose_name = '文章标签关联'
        verbose_name_plural = verbose_name
        unique_together = ('article', 'tag')


class Comment(models.Model):
    COMMENT_TYPE = (
        (1, '文章'),
        (2, '说说'),
        (3, '留言')
    )

    comment_type = models.IntegerField(choices=COMMENT_TYPE, verbose_name="评论类型")
    from_user = models.ForeignKey('user.SysUser', on_delete=models.CASCADE, related_name='sent_comments',
                                  verbose_name="评论人", null=True)
    content = models.TextField(verbose_name="评论内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = 'blog_comment'
        verbose_name = '评论管理'
        verbose_name_plural = verbose_name


class Config(models.Model):
    blog_name = models.CharField(max_length=55, default='happYness7', verbose_name="博客名称")
    blog_avatar = models.CharField(max_length=255,
                                   default='https://pub-d470eef1ae124f929afa0d8350e779c7.r2.dev/blog/2025/05/1cafdf3a6a6161cc1e3c349a06f0cddc.jpg',
                                   verbose_name="博客头像")
    personal_say = models.CharField(max_length=255, null=True, verbose_name="个人签名")
    blog_notice = models.CharField(max_length=255, null=True, verbose_name="博客公告")
    qq_link = models.CharField(max_length=255, null=True, blank=True, verbose_name="QQ链接")
    we_chat_link = models.CharField(max_length=255, null=True, blank=True, verbose_name="微信链接")
    github_link = models.CharField(max_length=255, null=True, blank=True, verbose_name="GitHub链接")
    git_ee_link = models.CharField(max_length=255, null=True, blank=True, verbose_name="Gitee链接")

    class Meta:
        db_table = 'blog_config'
        verbose_name = '系统配置'
        verbose_name_plural = verbose_name


class PhotoAlbum(models.Model):
    STATUS_CHOICES = (
        (1, '正常'),
        (2, '回收站')
    )

    album_name = models.CharField(max_length=26, null=True, blank=True, verbose_name="相册名称")
    description = models.CharField(max_length=55, null=True, blank=True, verbose_name="相册描述")
    album_cover = models.CharField(max_length=555, null=True, blank=True, verbose_name="相册封面")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = 'blog_photo_album'
        verbose_name = '相册管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.album_name or '未命名相册'


class Photo(models.Model):
    STATUS_CHOICES = (
        (1, '正常'),
        (2, '回收站')
    )

    album = models.ForeignKey(
        PhotoAlbum,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="所属相册",
        related_name='photos'
    )
    url = models.CharField(max_length=555, null=True, blank=True, verbose_name="图片地址")
    status = models.IntegerField(choices=STATUS_CHOICES, default=1, verbose_name="状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = 'blog_photo'
        verbose_name = '照片管理'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"照片 {self.id}"
