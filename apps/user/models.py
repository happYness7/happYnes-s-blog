from django.db import models
from rest_framework import serializers
from django.contrib.auth.models import AbstractUser


# Create your models here.
class SysUser(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True, verbose_name="用户名")
    password = models.CharField(max_length=100, verbose_name="密码", null=True)
    avatar = models.CharField(max_length=255, null=True, verbose_name="头像",
                              default="https://pub-d470eef1ae124f929afa0d8350e779c7.r2.dev/blog/configs/057c5dd3305a41278d74a7a5c7dffeb5.jpg")
    email = models.EmailField(max_length=100, null=True, verbose_name="邮箱")
    phonenumber = models.CharField(max_length=11, null=True, verbose_name="手机号")
    login_date = models.DateField(null=True, verbose_name="最后登录时间")
    status = models.IntegerField(verbose_name="账号状态（0正常 1停用）", null=True)
    create_time = models.DateField(null=True, verbose_name="创建时间")
    update_time = models.DateField(null=True, verbose_name="更新时间")
    remark = models.CharField(max_length=500, null=True, verbose_name="备注")

    class Meta:
        db_table = 'sys_user'


class SysUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysUser
        fields = '__all__'
