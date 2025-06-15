import base64
import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime

from captcha.image import ImageCaptcha
from django.core.cache import cache
from django.http import JsonResponse

from djangoAdmin.utils.pagination import paginate_queryset
from django.db import IntegrityError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from rest_framework import viewsets, status
from rest_framework.views import APIView

from djangoAdmin import settings
from apps.menu.models import SysRoleMenu, SysMenu, SysMenuSerializer
from apps.role.models import SysUserRole
from apps.user.models import SysUser, SysUserSerializer


class CaptchaView(APIView):
    # 验证码字符集（排除易混淆字符）
    CAPTCHA_CHARS = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789'
    CAPTCHA_LENGTH = 4  # 验证码长度
    TIMEOUT = 300  # 验证码有效期（秒）

    def get(self, request):
        try:
            # 生成随机验证码（使用安全随机数）
            captcha_text = ''.join(secrets.choice(self.CAPTCHA_CHARS) for _ in range(self.CAPTCHA_LENGTH))
            # 生成验证码图片
            image = ImageCaptcha()
            image_data = image.generate(captcha_text)

            # 转换为Base64字符串
            base64_str = base64.b64encode(image_data.getvalue()).decode()
            # 生成唯一令牌并存储验证码
            captcha_token = str(uuid.uuid4())
            cache.set(f'captcha_{captcha_token}', captcha_text, timeout=self.TIMEOUT)

            return JsonResponse({
                'code': 200,
                'base64str': f'data:image/png;base64,{base64_str}',
                'captcha_token': captcha_token
            })

        except Exception as e:
            return JsonResponse({
                'code': 500,
                'errorInfo': '验证码生成失败'
            }, status=500)


class LoginView(APIView):
    CAPTCHA_TIMEOUT = 300

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        captcha_code = request.data.get('captcha')
        captcha_token = request.data.get('captcha_token')
        # 参数校验
        if not all([captcha_code, captcha_token]):
            return Response({'code': 400, 'errorInfo': '验证码参数缺失'},
                            status=status.HTTP_400_BAD_REQUEST)

        # 获取缓存验证码
        try:
            cache_key = f'captcha_{captcha_token}'
            real_captcha = cache.get(cache_key)

            # 立即删除已使用的验证码（无论对错）
            if real_captcha:
                cache.delete(cache_key)

            if not real_captcha:
                return Response({'code': 400, 'errorInfo': '验证码已过期'},
                                status=status.HTTP_400_BAD_REQUEST)

            # 不区分大小写校验
            if real_captcha.lower() != captcha_code.lower():
                return Response({'code': 400, 'errorInfo': '验证码错误'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': '验证服务异常'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # 用户验证
        try:
            user = SysUser.objects.get(username=username, password=hashlib.md5(password.encode()).hexdigest())
        except SysUser.DoesNotExist:
            return Response({'code': 400, 'errorInfo': '用户名或密码错误'}, status=status.HTTP_400_BAD_REQUEST)

        # 生成JWT
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        # 更新登录时间
        user.login_date = now().date()
        user.save()

        # 获取角色信息
        role_list = SysUserRole.objects.filter(user_id=user.id).values('role__id', 'role__name')
        roles = ",".join([role['role__name'] for role in role_list])

        # 获取所有原始菜单ID（不经过处理）
        raw_menu_ids = set()
        for role in SysUserRole.objects.filter(user=user).select_related('role'):
            raw_menu_ids.update(
                SysRoleMenu.objects.filter(role=role.role)
                .values_list('menu_id', flat=True)
            )

        # 获取所有相关菜单对象（包括原始菜单及其祖先）
        menu_map = SysMenu.objects.in_bulk(raw_menu_ids)
        all_parent_ids = set()
        for menu_id in raw_menu_ids:
            all_parent_ids.update(self.get_all_parents(menu_id, menu_map))

        # 合并最终需要的菜单ID（原始菜单 + 所有父级菜单）
        final_menu_ids = raw_menu_ids.union(all_parent_ids)

        # 查询菜单并动态过滤子菜单
        menus = SysMenu.objects.filter(id__in=final_menu_ids).prefetch_related(
            Prefetch('children',
                     queryset=SysMenu.objects.filter(id__in=raw_menu_ids),  # 关键修改：只包含原始权限ID
                     to_attr='filtered_children')
        ).order_by('order_num')

        menu_tree = self.build_menu_tree(menus)
        return Response({
            'code': 200,
            'token': token,
            'user': SysUserSerializer(user).data,
            'info': '登录成功！',
            'roles': roles,
            'menuList': menu_tree
        })

        # 获取所有祖先菜单ID（包含路径上的所有父级）

    def get_all_parents(self, menu_id, menu_map):
        parents = set()
        current_id = menu_id
        while current_id:
            menu = menu_map.get(current_id)
            if not menu or not menu.parent_id:
                break
            parents.add(menu.parent_id)
            current_id = menu.parent_id
        return parents

    def build_menu_tree(self, menus):
        menu_dict = {}
        processed_ids = set()

        # 第一次遍历：创建所有节点
        sorted_menus = sorted(menus, key=lambda x: x.order_num)
        for menu in sorted_menus:
            menu_data = SysMenuSerializer(menu).data
            menu_data['children'] = []
            menu_dict[menu.id] = menu_data

        # 第二次遍历：构建树结构
        root_menus = []
        for menu in sorted_menus:
            menu_data = menu_dict[menu.id]

            # 处理父级关系
            if menu.parent and menu.parent.id in menu_dict:
                parent_data = menu_dict[menu.parent.id]
                # 检查是否重复添加
                if menu_data not in parent_data['children']:
                    parent_data['children'].append(menu_data)
                    processed_ids.add(menu.id)

            # 仅当没有父级或父级不存在时作为根节点
            if menu.id not in processed_ids:
                root_menus.append(menu_data)
                processed_ids.add(menu.id)

        # 按order_num排序根节点
        return sorted(root_menus, key=lambda x: x['order_num'])


class RegisterView(APIView):
    def post(self, request):
        # 获取请求参数
        username = request.data.get('username')
        password = request.data.get('password')
        captcha_code = request.data.get('captcha')
        captcha_token = request.data.get('captcha_token')

        # 基础参数校验
        required_fields = ['username', 'password', 'captcha_code', 'captcha_token']
        if not all([username, password, captcha_code, captcha_token]):
            return Response({'code': 400, 'errorInfo': '缺少必要参数'},
                            status=status.HTTP_400_BAD_REQUEST)
        # 验证码校验逻辑
        try:
            cache_key = f'captcha_{captcha_token}'
            real_captcha = cache.get(cache_key)

            # 无论验证结果如何都删除已使用的验证码
            if real_captcha:
                cache.delete(cache_key)

            if not real_captcha:
                return Response({'code': 400, 'errorInfo': '验证码已过期'},
                                status=status.HTTP_400_BAD_REQUEST)

            if real_captcha.lower() != captcha_code.lower():
                return Response({'code': 400, 'errorInfo': '验证码错误'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': '验证服务异常'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # 创建用户
        try:
            # 检查用户名唯一性
            if SysUser.objects.filter(username=username).exists():
                return Response({'code': 400, 'errorInfo': '用户名已存在'},
                                status=status.HTTP_400_BAD_REQUEST)

            # 创建用户记录
            new_user = SysUser.objects.create(
                username=username,
                password=hashlib.md5(password.encode()).hexdigest(),
                status=0,  # 默认状态为正常
                create_time=now().date(),
                update_time=now().date()
            )

            # ✅ 新增角色分配逻辑
            try:
                # 自动分配角色ID为2
                SysUserRole.objects.create(
                    user_id=new_user.id,
                    role_id=2  # 根据你的实际角色ID调整
                )
            except Exception as role_error:
                # 如果角色分配失败，回滚用户创建
                new_user.delete()
                return Response({'code': 500, 'errorInfo': f'角色分配失败: {str(role_error)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'code': 200,
                'info': '注册成功'
            })

        except IntegrityError:
            return Response({'code': 500, 'errorInfo': '用户创建失败'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AvatarView(APIView):
    def post(self, request):
        data = request.data
        obj_user = get_object_or_404(SysUser, id=data['id'])
        obj_user.avatar = data['avatar']
        obj_user.save()
        return Response({'code': 200})


class SysUserViewSet(viewsets.ModelViewSet):
    queryset = SysUser.objects.all()
    serializer_class = SysUserSerializer

    def list(self, request, *args, **kwargs):
        query = request.query_params.get('query', '')
        page_num = request.query_params.get('pageNum', 1)
        page_size = request.query_params.get('pageSize', 10)

        queryset = self.get_queryset().filter(username__icontains=query).order_by('id')

        try:
            page, total = paginate_queryset(queryset, page_num, page_size)
            users = list(page.object_list.values())

            user_ids = [user['id'] for user in users]
            role_list = SysUserRole.objects.filter(user_id__in=user_ids).values('user_id', 'role__id', 'role__name')
            role_dict = {user_id: [] for user_id in user_ids}
            for role in role_list:
                role_dict[role['user_id']].append({'id': role['role__id'], 'name': role['role__name']})

            for user in users:
                user['roleList'] = role_dict.get(user['id'], [])

            return Response({
                'code': 200,
                'total': total,
                'userList': users,
            })
        except ValueError as e:
            return Response({'code': 404, 'errorInfo': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_password = request.data.get('oldPassword')
        new_password = request.data.get('newPassword')

        if instance.password != hashlib.md5(old_password.encode()).hexdigest():
            return Response({'code': 500, 'errorInfo': '原密码错误！'}, status=status.HTTP_400_BAD_REQUEST)

        instance.password = hashlib.md5(new_password.encode()).hexdigest()
        instance.update_time = now().date()
        instance.save()
        return Response({'code': 200})

    def create(self, request, *args, **kwargs):
        try:
            request.data['create_time'] = now().date()
            request.data['update_time'] = now().date()
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '用户名已存在！'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            request.data['update_time'] = now().date()
            return super().update(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '用户名已存在！'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['delete'], detail=False, url_path='batch-delete')
    def batch_delete(self, request):
        try:
            id_list = json.loads(request.body.decode("utf-8"))
            SysUserRole.objects.filter(user_id__in=id_list).delete()
            SysUser.objects.filter(id__in=id_list).delete()
            return Response({'code': 200, 'info': '删除成功！'})
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            id = kwargs.get('pk')
            SysUserRole.objects.filter(user_id=id).delete()
            SysUser.objects.filter(id=id).delete()
            return Response({'code': 200, 'info': '删除成功！'})
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch'], url_path='assign-roles')
    def assign_roles(self, request, pk=None):
        data = json.loads(request.body.decode("utf-8"))
        user_id = data.get('id')
        role_ids = data.get('roleIds')

        if not user_id:
            return Response({'code': 400, 'info': '用户ID不能为空！'}, status=status.HTTP_400_BAD_REQUEST)
        if not role_ids or not isinstance(role_ids, list):
            return Response({'code': 400, 'info': '角色ID列表不能为空且必须是列表！'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = SysUser.objects.get(id=user_id)
        except SysUser.DoesNotExist:
            return Response({'code': 404, 'info': '用户不存在！'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # 删除用户现有的角色关联
            SysUserRole.objects.filter(user_id=user_id).delete()

            # 创建新的角色关联
            user_roles = [SysUserRole(user_id=user_id, role_id=role_id) for role_id in role_ids]
            SysUserRole.objects.bulk_create(user_roles)

            return Response({'code': 200, 'info': '角色分配成功！'})
        except Exception as e:
            return Response({'code': 500, 'info': f'分配角色时出错: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        user = self.get_object()
        default_password = hashlib.md5("123456".encode()).hexdigest()
        try:
            user.password = default_password
            user.update_time = now().date()
            user.save()
            return Response({'code': 200, 'info': '密码重置成功！'})
        except Exception as e:
            return Response({'code': 500, 'info': f'重置密码时出错: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch'], url_path='change-status')
    def change_status(self, request, pk=None):
        user = self.get_object()
        try:
            # 获取前端传递的 status 参数
            status_data = request.data.get('status')
            if status_data is None:
                return Response({'code': 400, 'info': 'status 参数不能为空！'}, status=status.HTTP_400_BAD_REQUEST)

            # 将用户的状态设置为前端传递的值
            user.status = status_data
            user.update_time = now().date()
            user.save()
            return Response({'code': 200, 'info': '状态更新成功！', 'user': SysUserSerializer(user).data})
        except Exception as e:
            return Response({'code': 500, 'info': f'状态更新时出错: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
