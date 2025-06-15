import random
from apps.user.models import SysUser
from django.db import IntegrityError
from django.utils.timezone import now
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from apps.blog.models import Article, Category, Tag, ArticleTag, Photo, PhotoAlbum, Config, Comment
from apps.blog.serializers import ArticleSerializer, CategorySerializer, TagSerializer, PhotoSerializer, \
    PhotoAlbumSerializer, ConfigSerializer, CommentSerializer
from djangoAdmin.utils.pagination import paginate_queryset


# Create your views here.

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        query_params = request.query_params

        conditions = Q()
        if title := query_params.get('article_title'):
            conditions &= Q(article_title__icontains=title)
        if category_name := query_params.get('category'):
            try:
                category = Category.objects.get(category_name=category_name)
                conditions &= Q(category=category)
            except Category.DoesNotExist:
                return Response({'code': 404, 'errorInfo': '分类不存在！'}, status=status.HTTP_404_NOT_FOUND)
        if tag_param := query_params.get('tags'):
            try:
                tag_names = [name.strip() for name in tag_param.split(',')]
                if not tag_names:
                    raise ValueError("标签参数不能为空")

                # 获取所有存在的标签
                tags = Tag.objects.filter(tag_name__in=tag_names)

                # 验证是否所有标签都存在
                existing_tags = set(tags.values_list('tag_name', flat=True))
                missing_tags = set(tag_names) - existing_tags
                if missing_tags:
                    raise Tag.DoesNotExist(f"缺失标签: {', '.join(missing_tags)}")
                for tag in tags:
                    queryset = queryset.filter(tags=tag)
            except ValueError as e:
                return Response(
                    {'code': 400, 'errorInfo': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Tag.DoesNotExist as e:
                return Response(
                    {'code': 404, 'errorInfo': str(e)},
                    status=status.HTTP_404_NOT_FOUND
                )
        if is_top := query_params.get('is_top'):
            try:
                conditions &= Q(is_top=int(is_top))
            except ValueError:
                return Response({'code': 400, 'errorInfo': 'is_top参数错误！'}, status=status.HTTP_400_BAD_REQUEST)
        start_date = query_params.get('start_time') or (
                query_params.getlist('dateRange') and query_params.getlist('dateRange')[0])
        end_date = query_params.get('end_time') or (
                query_params.getlist('dateRange') and query_params.getlist('dateRange')[-1])
        if start_date:
            conditions &= Q(created_at__gte=start_date)
        if end_date:
            conditions &= Q(created_at__lte=end_date)
        if param_status := query_params.get('status'):
            try:
                conditions &= Q(status=int(param_status))
            except ValueError:
                return Response({'code': 400, 'errorInfo': 'status参数错误！'}, status=status.HTTP_400_BAD_REQUEST)
        queryset = queryset.filter(conditions).distinct()
        # 优化查询性能
        queryset = queryset.select_related('category').prefetch_related('tags').order_by('is_top', 'id')
        try:
            page, total = paginate_queryset(queryset, request.query_params.get('pageNum', 1),
                                            request.query_params.get('pageSize', 10))
            # ✅ 使用序列化器处理分页数据
            serializer = self.get_serializer(page.object_list, many=True)

            return Response({
                'code': 200,
                'total': total,
                'articleList': serializer.data,  # 包含完整序列化数据
            })
        except ValueError as e:
            return Response({'code': 404, 'errorInfo': str(e)}, status=404)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=500)

    @action(detail=True, methods=['patch'], url_path='change-top')
    def change_top(self, request, pk=None):
        article = self.get_object()
        try:
            top_data = request.data.get('is_top')
            if top_data is None:
                return Response({'code': 400, 'errorInfo': 'is_top参数不能为空！'}, status=status.HTTP_400_BAD_REQUEST)
            article.is_top = top_data
            article.updated_at = now().date()
            article.save()
            return Response({'code': 200, 'info': '修改成功！'})
        except Exception as e:
            return Response({'code': 500, 'info': f'状态更新时出错: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            if instance.status == 2:
                return Response({'code': 400, 'errorInfo': '文章已私密！'}, status=status.HTTP_400_BAD_REQUEST)
            instance.status = 2
            instance.save()
            return Response({'code': 200, 'info': '文章私密成功！'})
        except Exception as e:
            return Response({'code': 500, 'errorInfo': f'文章私密时出错: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        # 设置创建时间和更新时间
        request.data['created_at'] = now()
        request.data['updated_at'] = now()

        # 处理 category 字段
        request.data['category_id'] = request.data.pop('category')
        # 调用父类的 create 方法保存 Article 对象
        response = super().create(request, *args, **kwargs)
        # 获取保存后的 Article 对象
        article_id = response.data.get('id')

        # 处理 tags 数组并存储到 article_tag 表
        tagids = request.data.get('tags', [])
        for tag_id in tagids:
            try:
                ArticleTag.objects.create(article_id=article_id, tag_id=tag_id)
            except Tag.DoesNotExist:
                return Response({'code': 404, 'errorInfo': f'标签 {tag_id} 不存在！'},
                                status=status.HTTP_404_NOT_FOUND)

        return response

    def update(self, request, *args, **kwargs):
        # 获取当前对象
        instance = self.get_object()
        # 保留原有的 created_at 值
        request.data['created_at'] = instance.created_at
        request.data['updated_at'] = now()

        # 处理 category 字段
        request.data['category_id'] = request.data.pop('category')
        # 调用父类的 create 方法保存 Article 对象
        response = super().update(request, *args, **kwargs)
        # 获取保存后的 Article 对象
        article_id = response.data.get('id')

        # 删除旧的标签关联
        ArticleTag.objects.filter(article_id=article_id).delete()

        # 处理 tags 数组并存储到 article_tag 表
        tagids = request.data.get('tags', [])
        for tag_id in tagids:
            try:
                ArticleTag.objects.create(article_id=article_id, tag_id=tag_id)
            except Tag.DoesNotExist:
                return Response({'code': 404, 'errorInfo': f'标签 {tag_id} 不存在！'},
                                status=status.HTTP_404_NOT_FOUND)
        return response

    @action(methods=['get'], detail=True, url_path='adjacent-articles')
    def adjacent_articles(self, request, pk=None):
        try:
            current_article = self.get_object()
        except Article.DoesNotExist:
            return Response({'code': 404, 'errorInfo': '文章不存在'}, status=status.HTTP_404_NOT_FOUND)

            # 获取基准排序字段值
        current_id = current_article.id

        # 构建排序条件（按id升序）
        base_queryset = Article.objects.all().order_by('id')

        # 获取上一篇（id更小的最大文章）
        prev_article = base_queryset.filter(id__lt=current_id).order_by('-id').first()

        # 获取下一篇（id更大的最小文章）
        next_article = base_queryset.filter(id__gt=current_id).order_by('id').first()

        # 序列化结果
        serializer_class = self.get_serializer_class()
        prev_data = serializer_class(prev_article).data if prev_article else None
        next_data = serializer_class(next_article).data if next_article else None

        return Response({
            'code': 200,
            'data': {
                'prev': prev_data,
                'next': next_data
            }
        })


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @action(methods=['get'], detail=False, url_path='category-list')
    def category_list(self, request, *args, **kwargs):
        query = request.query_params.get('query', '')
        page_num = int(request.query_params.get('pageNum', 1))
        page_size = int(request.query_params.get('pageSize', 10))

        queryset = self.get_queryset().filter(category_name__icontains=query).order_by('id')
        try:
            page, total = paginate_queryset(queryset, page_num, page_size)
            # ✅ 使用序列化器处理分页数据
            serializer = self.get_serializer(page.object_list, many=True)

            return Response({
                'code': 200,
                'total': total,
                'categoryList': serializer.data,  # 包含完整序列化数据
            })
        except ValueError as e:
            return Response({'code': 404, 'errorInfo': str(e)}, status=404)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=500)

    def create(self, request, *args, **kwargs):
        try:
            request.data['created_at'] = now()
            request.data['updated_at'] = now()
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '分类已存在！'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            # 获取当前对象
            instance = self.get_object()
            # 保留原有的 created_at 值
            request.data['created_at'] = instance.created_at
            request.data['updated_at'] = now()
            return super().update(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '分类已存在！'}, status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    @action(methods=['get'], detail=False, url_path='tag-list')
    def tag_list(self, request, *args, **kwargs):
        query = request.query_params.get('query', '')
        page_num = int(request.query_params.get('pageNum', 1))
        page_size = int(request.query_params.get('pageSize', 10))

        queryset = self.get_queryset().filter(tag_name__icontains=query).order_by('id')
        try:
            page, total = paginate_queryset(queryset, page_num, page_size)
            # ✅ 使用序列化器处理分页数据
            serializer = self.get_serializer(page.object_list, many=True)

            return Response({
                'code': 200,
                'total': total,
                'tagList': serializer.data,  # 包含完整序列化数据
            })
        except ValueError as e:
            return Response({'code': 404, 'errorInfo': str(e)}, status=404)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=500)

    def create(self, request, *args, **kwargs):
        try:
            request.data['created_at'] = now()
            request.data['updated_at'] = now()
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '标签已存在！'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            # 获取当前对象
            instance = self.get_object()
            # 保留原有的 created_at 值
            request.data['created_at'] = instance.created_at
            request.data['updated_at'] = now()
            return super().update(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '标签已存在！'}, status=status.HTTP_400_BAD_REQUEST)


class PhotoViewSet(viewsets.ModelViewSet):
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer

    def list(self, request, *args, **kwargs):
        # 基础查询集
        queryset = self.filter_queryset(self.get_queryset())

        # ✅ 公共过滤条件（移到分页判断前）
        if album_id := request.query_params.get('albumId'):
            try:  # 增加相册存在性校验
                album = PhotoAlbum.objects.get(id=album_id)
                album_name = album.album_name
                queryset = queryset.filter(album_id=album_id)
            except PhotoAlbum.DoesNotExist:
                return Response({'code': 404, 'errorInfo': '相册不存在'},
                                status=status.HTTP_404_NOT_FOUND)

        # ✅ 状态过滤（公共逻辑）
        if status_param := request.query_params.get('status'):
            try:
                status_value = int(status_param)
                if status_value not in [1, 2]:
                    raise ValueError
                queryset = queryset.filter(status=status_value)
            except ValueError:
                return Response(
                    {'code': 400, 'errorInfo': 'status参数应为1或2'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ✅ 公共排序逻辑
        queryset = queryset.order_by('-created_at')

        # 分页判断
        if not request.query_params.get('pageNum') and not request.query_params.get('pageSize'):
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'code': 200,
                'total': len(queryset),
                'photoList': serializer.data,  # ✅ 保持字段名一致
                'albumName': album_name if album_id else None  # ✅ 安全获取相册名
            })
        else:
            # 原有分页逻辑
            page_num = int(request.query_params.get('pageNum', 1))
            page_size = int(request.query_params.get('pageSize', 10))
            page, total = paginate_queryset(queryset, page_num, page_size)
            serializer = self.get_serializer(page.object_list, many=True)
            return Response({
                'code': 200,
                'total': total,
                'photoList': serializer.data,
                'albumName': album_name if album_id else None
            })

    def create(self, request, *args, **kwargs):
        try:
            # 获取 album_id 和 urls 列表
            album_id = request.data.get('album_id')
            urls = request.data.get('urls', [])

            # 检查 album_id 是否存在
            if not album_id:
                return Response({'code': 400, 'errorInfo': '缺少album_id参数！'},
                                status=status.HTTP_400_BAD_REQUEST)

            # 检查 urls 是否为列表
            if not isinstance(urls, list):
                return Response({'code': 400, 'errorInfo': 'urls参数应为数组！'},
                                status=status.HTTP_400_BAD_REQUEST)

            # 检查相册是否存在
            try:
                album = PhotoAlbum.objects.get(id=album_id)
            except PhotoAlbum.DoesNotExist:
                return Response({'code': 404, 'errorInfo': '相册不存在！'},
                                status=status.HTTP_404_NOT_FOUND)

            # 批量创建照片
            for url in urls:
                photo_data = {
                    'url': url,
                    'album_id': album_id,
                }
                photo = Photo(**photo_data)
                photo.save()

            return Response({
                'code': 200,
                'info': '照片创建成功！',
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'code': 500, 'errorInfo': f'创建照片时出错: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['delete'], detail=False, url_path='batch-delete')
    def batch_delete(self, request):
        if not (photo_ids := request.data.get('photoIds')):
            return Response({'code': 400, 'errorInfo': '缺少photoIds参数'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(photo_ids, list):
            return Response({'code': 400, 'errorInfo': 'photoIds应为数组'},
                            status=status.HTTP_400_BAD_REQUEST)

        Photo.objects.filter(id__in=photo_ids).delete()

        return Response({'code': 200}, status=status.HTTP_200_OK)

    @action(methods=['patch'], detail=False, url_path='change-status')
    def change_status(self, request):
        """批量修改照片状态"""
        if not (photo_ids := request.data.get('photoIds')):
            return Response({'code': 400, 'errorInfo': '缺少photoIds参数'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(photo_ids, list):
            return Response({'code': 400, 'errorInfo': 'photoIds应为数组'},
                            status=status.HTTP_400_BAD_REQUEST)
        # 获取所有照片的状态
        try:
            status_param = Photo.objects.filter(id__in=photo_ids).values_list('status', flat=True).distinct()[0]
            print(status_param)
            if status_param not in [1, 2]:  # 验证状态值有效性
                raise ValueError
        except ValueError:
            return Response({'code': 400, 'errorInfo': 'status参数应为1（正常）或2（回收站）'},
                            status=status.HTTP_400_BAD_REQUEST)
        # 更新照片状态
        if status_param == 1:
            Photo.objects.filter(id__in=photo_ids).update(status=2)
        else:
            Photo.objects.filter(id__in=photo_ids).update(status=1)
        return Response({'code': 200, 'info': '状态修改成功！'}, status=status.HTTP_200_OK)

    @action(methods=['delete'], detail=False, url_path='delete-recycled')
    def delete_recycled(self, request):
        """删除所有在回收站的照片"""
        try:
            # 获取所有状态为回收站的照片
            recycled_photos = Photo.objects.filter(status=2)
            # 删除这些照片
            recycled_photos.delete()
            return Response({'code': 200, 'info': '回收站照片删除成功！'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': f'删除回收站照片时出错: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PhotoAlbumViewSet(viewsets.ModelViewSet):
    queryset = PhotoAlbum.objects.all()
    serializer_class = PhotoAlbumSerializer

    def list(self, request, *args, **kwargs):
        # 获取分页参数
        page_num = int(request.query_params.get('pageNum', 1))
        page_size = int(request.query_params.get('pageSize', 10))

        # 基础查询集
        queryset = self.filter_queryset(self.get_queryset())

        # 添加排序（按创建时间倒序）
        queryset = queryset.order_by('-created_at')

        try:
            # 分页处理
            page, total = paginate_queryset(queryset, page_num, page_size)

            # 序列化数据
            serializer = self.get_serializer(page.object_list, many=True)

            return Response({
                'code': 200,
                'total': total,
                'albumList': serializer.data  # 保持命名规范一致性
            })
        except ValueError as e:
            return Response({'code': 400, 'errorInfo': str(e)}, status=400)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=500)

    def create(self, request, *args, **kwargs):
        try:
            request.data['created_at'] = now()
            request.data['updated_at'] = now()
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '相册已存在！'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            # 获取当前对象
            instance = self.get_object()
            # 保留原有的 created_at 值
            request.data['created_at'] = instance.created_at
            request.data['updated_at'] = now()
            return super().update(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '相册已存在！'}, status=status.HTTP_400_BAD_REQUEST)


class ConfigViewSet(viewsets.ModelViewSet):
    queryset = Config.objects.all()
    serializer_class = ConfigSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    @action(methods=['get'], detail=False, url_path='message-list')
    def message_list(self, request):
        # 获取查询参数
        content = request.query_params.get('content')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')

        # 构建基础查询集（留言类型=3）
        queryset = Comment.objects.filter(comment_type=3).order_by('-created_at')

        # 构建过滤条件
        conditions = Q()
        if content:
            conditions &= Q(content__icontains=content)
        if start_time:
            conditions &= Q(created_at__gte=start_time)
        if end_time:
            conditions &= Q(created_at__lte=end_time)

        # 应用过滤条件
        queryset = queryset.filter(conditions)

        # 判断是否需要分页
        if not request.query_params.get('pageNum') and not request.query_params.get('pageSize'):
            # 不进行分页，返回全部数据
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'code': 200,
                'total': queryset.count(),
                'messageList': serializer.data
            })
        else:
            # 处理分页
            try:
                page_num = int(request.query_params.get('pageNum', 1))
                page_size = int(request.query_params.get('pageSize', 10))
                page, total = paginate_queryset(queryset, page_num, page_size)

                serializer = self.get_serializer(page.object_list, many=True)

                return Response({
                    'code': 200,
                    'total': total,
                    'messageList': serializer.data
                })
            except ValueError as e:
                return Response({'code': 400, 'errorInfo': str(e)}, status=400)
            except Exception as e:
                return Response({'code': 500, 'errorInfo': str(e)}, status=500)

    def create(self, request, *args, **kwargs):
        request.data['created_at'] = now()
        request.data['updated_at'] = now()

        # 1. 验证必填字段
        required_fields = ['content', 'comment_type']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {'code': 400, 'errorInfo': f'缺少必填字段: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 2. 用户处理逻辑（同步前端字段）
        user_id = request.data.get('user_id')  # 前端传递的字段
        if user_id:
            # 验证用户是否存在
            try:
                SysUser.objects.get(id=user_id)
                request.data['from_user_id'] = user_id  # 映射到模型字段
            except SysUser.DoesNotExist:
                return Response(
                    {'code': 400, 'errorInfo': '用户不存在'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # 游客处理
            while True:
                random_suffix = str(random.randint(100, 999)).zfill(3)
                guest_username = f'游客{random_suffix}'
                if not SysUser.objects.filter(username=guest_username).exists():
                    break
            guest_user = SysUser.objects.create(
                username=guest_username,
                password=None,
                status=0,
                create_time=now(),
            )
            request.data['from_user_id'] = guest_user.id

        # 3. 内容处理（保留原逻辑）
        request.data['content'] = request.data['content'].strip()
        if len(request.data['content']) > 1000:
            return Response(
                {'code': 400, 'errorInfo': '内容长度超过1000字符限制'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # 4. 保存数据
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'code': 500, 'errorInfo': f'服务器错误: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['delete'], detail=False, url_path='batch-delete')
    def batch_delete(self, request):
        if not (comment_ids := request.data.get('comment_ids')):
            return Response(
                {'code': 400, 'errorInfo': '缺少comment_ids参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(comment_ids, list):
            return Response(
                {'code': 400, 'errorInfo': 'comment_ids应为数组'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 安全删除（只删除存在的评论）
            deleted_count, _ = Comment.objects.filter(id__in=comment_ids).delete()

            return Response({
                'code': 200,
                'info': f'成功删除{deleted_count}条评论'
            })
        except Exception as e:
            return Response(
                {'code': 500, 'errorInfo': f'批量删除失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
