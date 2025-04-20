import json

from django.core.paginator import Paginator, EmptyPage
from django.db import IntegrityError
from django.shortcuts import render
from django.utils.timezone import now
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.menu.models import SysRoleMenu, SysMenu
from apps.role.models import SysRole, SysRoleSerializer, SysUserRole
from apps.user.models import SysUser


# Create your views here.


class SysRoleViewSet(viewsets.ModelViewSet):
    queryset = SysRole.objects.all()
    serializer_class = SysRoleSerializer

    @action(methods=['get'], detail=False, url_path='role-list')
    def role_list(self, request, *args, **kwargs):
        query = request.query_params.get('query', '')
        page_num = int(request.query_params.get('pageNum', 1))
        page_size = int(request.query_params.get('pageSize', 10))

        page_num = max(1, page_num)
        page_size = max(1, page_size)

        queryset = self.get_queryset().filter(name__icontains=query).order_by('id')
        paginator = Paginator(queryset, page_size)

        if page_num > paginator.num_pages:
            page_num = paginator.num_pages
        try:
            role_list_page = paginator.page(page_num)
            roles = list(role_list_page.object_list.values())

            role_ids = [role['id'] for role in roles]

            # 新增：获取角色原始菜单ID
            role_menu_ids = SysRoleMenu.objects.filter(
                role_id__in=role_ids
            ).values('role_id', 'menu_id')

            menu_ids_dict = {}
            for role_id in role_ids:
                original_ids = [item['menu_id'] for item in role_menu_ids if item['role_id'] == role_id]
                menu_ids_dict[role_id] = self._process_menu_ids(original_ids)  # 调用工具方法

            # 将处理后的menuIds添加到角色数据中
            for role in roles:
                role['menuIds'] = menu_ids_dict.get(role['id'], [])

            return Response({
                'code': 200,
                'total': paginator.count,
                'roleList': roles
            })
        except Exception as e:
            return Response({
                'code': 500,
                'errorInfo': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except EmptyPage:
            return Response({
                'code': 404,
                'errorInfo': 'Page not found',
            }, status=status.HTTP_404_NOT_FOUND)

    @action(methods=['delete'], detail=False, url_path='batch-delete')
    def batch_delete(self, request):
        try:
            id_list = json.loads(request.body.decode("utf-8"))
            SysUserRole.objects.filter(role_id__in=id_list).delete()
            SysRole.objects.filter(id__in=id_list).delete()
            return Response({'code': 200, 'info': '删除成功！'})
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        try:
            id = kwargs.get('pk')
            SysUserRole.objects.filter(role_id=id).delete()
            SysRole.objects.filter(id=id).delete()
            return Response({'code': 200, 'info': '删除成功！'})
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
            request.data['create_time'] = now().date()
            request.data['update_time'] = now().date()
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '角色已存在！'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            request.data['update_time'] = now().date()
            return super().update(request, *args, **kwargs)
        except IntegrityError:
            return Response({'code': 400, 'errorInfo': '角色已存在！'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['patch'], detail=True, url_path='assign-menus')
    def assign_menus(self, request, pk=None):
        data = json.loads(request.body.decode("utf-8"))
        menu_ids = data.get('menuIds')
        if not pk:
            return Response({'code': 400, 'info': '角色ID不能为空！'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            role = SysRole.objects.get(id=pk)
        except SysRole.DoesNotExist:
            return Response({'code': 404, 'info': '角色不存在！'}, status=status.HTTP_404_NOT_FOUND)

        try:
            SysRoleMenu.objects.filter(role_id=pk).delete()
            role_menus = [SysRoleMenu(role_id=pk, menu_id=menu_id) for menu_id in menu_ids]
            SysRoleMenu.objects.bulk_create(role_menus)
            return Response({'code': 200, 'info': '分配成功！'})
        except Exception as e:
            return Response({'code': 500, 'info': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _process_menu_ids(self, raw_ids):
        """统一处理菜单ID的工具方法"""
        # 获取所有菜单关系（缓存查询结果）
        all_menus = SysMenu.objects.prefetch_related('children').in_bulk()
        parent_child_map = {
            menu.id: [child.id for child in menu.children.all()]
            for menu in all_menus.values() if menu.children.exists()
        }

        filtered_ids = set(raw_ids)

        # 第一步：移除被子菜单包含的父菜单的子菜单ID
        for menu_id in raw_ids:
            if menu := all_menus.get(menu_id):
                if menu.parent_id and menu.parent_id in filtered_ids:
                    filtered_ids.discard(menu_id)

        # 第二步：处理父菜单自身
        final_ids = set()
        for menu_id in filtered_ids:
            if menu_id in parent_child_map:  # 是父菜单
                final_ids.add(menu_id)
            else:  # 是子菜单
                parent_id = all_menus[menu_id].parent_id
                if parent_id not in filtered_ids:
                    final_ids.add(menu_id)

        return list(final_ids)
