from django.db import models
import logging

class Camera(models.Model):
    camera_name = models.CharField(max_length=50, primary_key=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.camera_name


class Camera(models.Model):
    camera_name = models.CharField(max_length=50, primary_key=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.camera_name


class ArchiveVideo(models.Model):
    date_created = models.DateTimeField(blank=False)
    human_det = models.BooleanField(default=False)
    cat_det = models.BooleanField(default=False)
    chiken_det = models.BooleanField(default=False)
    car_det = models.BooleanField(default=False)
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return str(self.date_created)
    
    def get_fields(self):
        fields = [(field.name, getattr(self, field.name)) for field in ArchiveVideo._meta.fields]
        remove_list = []
        for id, field in enumerate(fields):
            if field[0].find('_det') < 1:
                remove_list.append(id)
        for index in reversed(remove_list):
            fields.remove(fields[index])
        return fields

    def get_fields(self):
        fields = [(field.name, getattr(self, field.name))
                  for field in ArchiveVideo._meta.fields]
        remove_list = []
        for id, field in enumerate(fields):
            if field[0].find('_det') < 1:
                remove_list.append(id)
        for index in reversed(remove_list):
            fields.remove(fields[index])
        return fields


class CachedVideo(models.Model):
    name = models.TextField(max_length=100)
    date_expire = models.DateTimeField()

    def __str__(self):
        return self.name
