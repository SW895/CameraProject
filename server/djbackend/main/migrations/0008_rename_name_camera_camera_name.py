# Generated by Django 4.2.3 on 2024-04-15 12:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_camera_alter_archivevideo_car_det_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='camera',
            old_name='name',
            new_name='camera_name',
        ),
    ]