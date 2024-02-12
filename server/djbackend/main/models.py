from django.db import models


class ArchiveVideo(models.Model):

    date_created = models.DateTimeField(blank=False)
    human_det = models.BooleanField(null=True, blank=True)
    cat_det = models.BooleanField(null=True, blank=True)
    chiken_det = models.BooleanField(null=True, blank=True)
    car_det = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return str(self.data_created)


class CachedVideo(models.Model):
    name = models.TextField()
    date_expire = models.DateTimeField()

    def __str__(self):
        return self.name
