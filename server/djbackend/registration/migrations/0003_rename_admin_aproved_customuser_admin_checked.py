# Generated by Django 4.2.3 on 2024-02-06 12:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0002_alter_customuser_managers_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='customuser',
            old_name='admin_aproved',
            new_name='admin_checked',
        ),
    ]