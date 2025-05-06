# apps/user/middleware.py

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWTError
from rest_framework_jwt.settings import api_settings


class JwtAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        white_list = ["/user/login/", "/user/captcha/"]
        path = request.path
        if path not in white_list and not path.startswith("/media"):
            token = request.META.get('HTTP_AUTHORIZATION')
            try:
                jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
                jwt_decode_handler(token)
            except ExpiredSignatureError:
                return JsonResponse({'code': 401, 'errorInfo': 'Token过期，请重新登录！'}, status=401)
            except InvalidTokenError:
                return JsonResponse({'code': 401, 'errorInfo': 'Token验证失败！'}, status=401)
            except PyJWTError:
                return JsonResponse({'code': 500, 'errorInfo': 'Token验证异常！'}, status=500)
        else:
            return None
