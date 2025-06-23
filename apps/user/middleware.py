# apps/user/middleware.py

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWTError
from rest_framework_jwt.settings import api_settings


class JwtAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        white_list = [
            "/api/user/login/",
            "/api/user/register/",
            "/api/user/captcha/",
            "/api/blog/",  # 所有/blog/前缀的路由
            "/api/media/",  # 媒体文件
            "/api/statistics/",
        ]
        path = request.path

        # 检查是否在白名单 (使用startswith匹配前缀)
        if any(path.startswith(white_path) for white_path in white_list):
            return None

        # Token验证逻辑
        token = request.META.get('HTTP_AUTHORIZATION')
        if not token:
            return JsonResponse({'code': 401, 'errorInfo': '缺少Token'}, status=401)

        try:
            jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
            jwt_decode_handler(token)
        except ExpiredSignatureError:
            return JsonResponse({'code': 401, 'errorInfo': 'Token过期'}, status=401)
        except InvalidTokenError:
            return JsonResponse({'code': 401, 'errorInfo': 'Token无效'}, status=401)
        except Exception as e:
            return JsonResponse({'code': 500, 'errorInfo': f'验证异常: {str(e)}'}, status=500)
