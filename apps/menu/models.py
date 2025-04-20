from django.db import models
from django.db.models import Prefetch
from rest_framework import serializers

from apps.role.models import SysRole


# Create your models here.
class SysMenuQuerySet(models.QuerySet):
    def with_children(self):
        return self.prefetch_related(
            Prefetch('children',
                     queryset=SysMenu.objects.all().order_by('order_num'),
                     to_attr='prefetched_children'
                     )
        )


class SysMenu(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True, verbose_name="菜单名称")
    icon = models.CharField(max_length=100, null=True, verbose_name="菜单图标")
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="父菜单",
        related_name='children',
        db_column='parent_id'  # 保持数据库字段名为 parent_id
    )
    order_num = models.IntegerField(null=True, verbose_name="显示顺序")
    path = models.CharField(max_length=200, null=True, verbose_name="路由地址")
    component = models.CharField(max_length=255, null=True, verbose_name="组件路径")
    menu_type = models.CharField(max_length=1, null=True, verbose_name="菜单类型（M目录 C菜单 F按钮）")
    perms = models.CharField(max_length=100, null=True, verbose_name="权限标识")
    create_time = models.DateField(null=True, verbose_name="创建时间", )
    update_time = models.DateField(null=True, verbose_name="更新时间")
    remark = models.CharField(max_length=500, null=True, verbose_name="备注")
    objects = SysMenuQuerySet.as_manager()

    class Meta:
        db_table = "sys_menu"
        ordering = ["order_num"]


class SysMenuSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = SysMenu
        fields = '__all__'

    def get_children(self, obj):
        # 自动递归序列化子菜单，并保持排序
        children = obj.children.all().order_by('order_num')
        return SysMenuSerializer(children, many=True).data if children.exists() else []


# 系统角色菜单关联类
class SysRoleMenu(models.Model):
    id = models.AutoField(primary_key=True)
    role = models.ForeignKey(SysRole, on_delete=models.PROTECT)
    menu = models.ForeignKey(SysMenu, on_delete=models.PROTECT)

    class Meta:
        db_table = "sys_role_menu"


class SysRoleMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysRoleMenu
        fields = '__all__'
