from django.db.models import Prefetch
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.menu.models import SysMenu, SysMenuSerializer


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
