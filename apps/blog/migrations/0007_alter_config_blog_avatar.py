# Generated by Django 5.1.3 on 2025-05-19 23:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0006_photoalbum_photo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="config",
            name="blog_avatar",
            field=models.CharField(
                default="https://pub-d470eef1ae124f929afa0d8350e779c7.r2.dev/blog/2025/05/1cafdf3a6a6161cc1e3c349a06f0cddc.jpg",
                max_length=255,
                verbose_name="博客头像",
            ),
        ),
    ]
