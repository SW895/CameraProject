# Generated by Django 4.2.3 on 2023-11-15 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='arhivevideo',
            old_name='video',
            new_name='video_path',
        ),
        migrations.RemoveField(
            model_name='arhivevideo',
            name='path',
        ),
        migrations.AlterField(
            model_name='arhivevideo',
            name='car_det',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='arhivevideo',
            name='cat_det',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='arhivevideo',
            name='chiken_det',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='arhivevideo',
            name='human_det',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
