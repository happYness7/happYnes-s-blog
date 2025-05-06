from django.core.paginator import EmptyPage
from django.db import IntegrityError
from django.db.models import Prefetch
from django.utils.timezone import now
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.menu.models import SysMenu, SysMenuSerializer, SysRoleMenu
from djangoAdmin.utils.pagination import paginate_queryset


# Create your views here.
class SysMenuViewSet(viewsets.ModelViewSet):
    queryset = SysMenu.objects.all()
    serializer_class = SysMenuSerializer

    @action(detail=False, methods=['get'], url_path='tree')
    def menu_tree(self, request):
        """获取完整菜单树（自动递归嵌套）"""
        queryset = SysMenu.objects.prefetch_related(
            Prefetch('children', queryset=SysMenu.objects.all().order_by('order_num'))
        ).filter(parent__isnull=True).order_by('order_num')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """菜单列表接口（返回所有根菜单及嵌套子菜单）"""
        try:
            # 1. 获取所有根菜单（parent为空的菜单）
            queryset = SysMenu.objects.filter(parent__isnull=True).order_by('order_num')

            # 2. 预取子菜单数据（优化查询性能）
            queryset = queryset.prefetch_related(
                Prefetch('children',
                         queryset=SysMenu.objects.all().order_by('order_num'),
                         to_attr='prefetched_children')
            )

            # 3. 序列化数据（自动包含嵌套子菜单）
            serializer = self.get_serializer(queryset, many=True)

            return Response({
                'code': 200,
                'data': serializer.data
            })

        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """创建菜单（支持parent_id字段）"""
        try:
            # 处理父级菜单关系
            parent_id = request.data.get('parent')
            print(request.data)
            if parent_id:
                parent_menu = SysMenu.objects.get(id=parent_id)
                request.data['parent'] = parent_menu.id  # 确保外键关系正确建立
            else:
                request.data['parent'] = None  # 明确设置为根菜单

            # 自动填充时间戳
            request.data.update({
                'create_time': now().date(),
                'update_time': now().date()
            })

            # 调用父类方法处理
            return super().create(request, *args, **kwargs)

        except SysMenu.DoesNotExist:
            return Response({'code': 404, 'errorInfo': '父菜单不存在'}, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError as e:
            return Response({'code': 400, 'errorInfo': '菜单名称已存在'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """更新菜单（支持parent_id字段）"""
        try:
            instance = self.get_object()
            # 处理父级菜单更新
            parent_id = request.data.get('parent')
            if parent_id:
                if parent_id == instance.id:  # 防止设置自己为父菜单
                    return Response({'code': 400, 'errorInfo': '不能设置自身为父菜单'},
                                    status=status.HTTP_400_BAD_REQUEST)
                parent_menu = SysMenu.objects.get(id=parent_id)
                request.data['parent'] = parent_menu.id
            else:
                request.data['parent'] = None

            # 自动更新修改时间
            request.data['update_time'] = now().date()

            # 调用父类方法处理
            return super().update(request, *args, **kwargs)

        except SysMenu.DoesNotExist:
            return Response({'code': 404, 'errorInfo': '父菜单不存在'}, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError as e:
            return Response({'code': 400, 'errorInfo': '菜单名称已存在'}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """删除菜单（自动级联删除所有子菜单）"""
        try:
            target_menu = self.get_object()

            # 1. 获取所有需要删除的菜单ID（包含目标菜单及其所有后代）
            delete_ids = set()
            queue = [target_menu]

            # 使用广度优先搜索收集所有后代菜单ID
            while queue:
                current_menu = queue.pop(0)
                delete_ids.add(current_menu.id)
                queue.extend(list(current_menu.children.all()))

            # 2. 批量删除（单个SQL操作）
            SysRoleMenu.objects.filter(menu_id__in=delete_ids).delete()
            SysMenu.objects.filter(id__in=delete_ids).delete()

            return Response({'code': 200, 'info': '删除成功！'})

        except SysMenu.DoesNotExist:
            return Response({'code': 404, 'errorInfo': '菜单不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'code': 500, 'errorInfo': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
