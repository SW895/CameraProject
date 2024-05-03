from django.db import models


class ArchiveVideo(models.Model):
    date_created = models.DateTimeField(blank=False)
    human_det = models.BooleanField(default=False)
    cat_det = models.BooleanField(default=False)
    chiken_det = models.BooleanField(default=False)
    car_det = models.BooleanField(default=False)

    def __str__(self):
        return str(self.date_created)


class CachedVideo(models.Model):
    name = models.TextField(max_length=100)
    date_expire = models.DateTimeField()

    def __str__(self):
        return self.name

    
class Camera(models.Model):
    camera_name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.camera_name