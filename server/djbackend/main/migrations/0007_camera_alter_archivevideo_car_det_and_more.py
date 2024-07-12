# Generated by Django 4.2.3 on 2024-04-15 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_cachedvideo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Camera',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=False)),
            ],
        ),
        migrations.AlterField(
            model_name='archivevideo',
            name='car_det',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='archivevideo',
            name='cat_det',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='archivevideo',
            name='chiken_det',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='archivevideo',
            name='human_det',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='cachedvideo',
            name='name',
            field=models.TextField(max_length=100),
        ),
    ]
