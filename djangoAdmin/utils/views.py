from django.http import JsonResponse
from apps.blog.models import Article, Tag, Category
from apps.user.models import SysUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import uuid
import boto3
from django.conf import settings


class StatisticsView(APIView):
    """系统数据统计视图
    GET /api/statistics/ - 获取系统核心数据指标
    """

    def get(self, request):
        try:
            user_total = SysUser.objects.count()
            article_total = Article.objects.count()
            tag_total = Tag.objects.count()
            category_total = Category.objects.count()

            return Response({
                'code': status.HTTP_200_OK,
                'data': {
                    'user_total': user_total,
                    'article_total': article_total,
                    'tag_total': tag_total,
                    'category_total': category_total
                }
            })

        except Exception as e:
            return Response({
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'error': f'数据统计失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImageUploadView(APIView):
    """统一文件上传视图（增强健壮性版本）"""
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    UPLOAD_TYPES = {
        'article_cover': {'prefix': 'article_cover/'},
        'config': {'prefix': 'configs/'},
        'photo': {'prefix': 'photos/'},
        'avatar': {'prefix': 'avatars/'},
        'album_cover': {'prefix': 'photoAlbums/'},
    }
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    S3_TIMEOUT = 30  # 秒

    def _check_client_connection(self, request):
        """检查客户端是否保持连接（关键修复点）"""
        if request._request._stream.closed:
            raise BrokenPipeError("客户端已断开连接")

    def post(self, request):
        try:
            # 参数验证部分保持不变
            upload_type = request.query_params.get('type')
            config = self.UPLOAD_TYPES.get(upload_type)
            if not config:
                return Response({"error": "Invalid upload type"}, status=status.HTTP_400_BAD_REQUEST)

            file = request.FILES.get('file')
            if not file:
                return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

            # 文件验证逻辑
            file_extension = file.name.split('.')[-1].lower()
            if file_extension not in self.ALLOWED_EXTENSIONS:
                return Response({"error": f"仅支持 {', '.join(self.ALLOWED_EXTENSIONS)} 格式"},
                                status=status.HTTP_400_BAD_REQUEST)

            if file.size > self.MAX_FILE_SIZE:
                return Response({"error": "文件大小超过5MB限制"}, status=status.HTTP_400_BAD_REQUEST)

            # 生成存储路径
            file_name = f"{config['prefix']}{uuid.uuid4().hex}.{file_extension}"

            # 配置带超时的S3客户端（关键修复点）
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT,
                aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY,
                aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_KEY,
                config=boto3.session.Config(
                    connect_timeout=self.S3_TIMEOUT,
                    read_timeout=self.S3_TIMEOUT
                )
            )

            # 带连接检查的上传逻辑（关键修复点）
            self._check_client_connection(request)  # 上传前首次检查
            s3_client.upload_fileobj(
                Fileobj=file,
                Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME,
                Key=file_name,
                ExtraArgs={'ContentType': file.content_type},
                Callback=lambda bytes_transferred: self._check_client_connection(request)  # 每上传一个分块检查一次
            )

            # 生成访问URL
            file_url = f"{settings.CLOUDFLARE_R2_PUBLIC_URL}/{settings.CLOUDFLARE_R2_BUCKET_NAME}/{file_name}"
            return Response({"url": file_url}, status=status.HTTP_200_OK)

        except BrokenPipeError as e:
            # 捕获客户端提前断开异常（关键修复点）
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"客户端提前断开连接: {str(e)}")
            return Response(status=499)  # 使用Nginx特有的499状态码表示客户端关闭连接

        except Exception as e:
            # 原有异常处理保持不变
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
