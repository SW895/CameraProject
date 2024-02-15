from django.contrib import admin
from .models import ArchiveVideo, CachedVideo


admin.site.register(ArchiveVideo)
admin.site.register(CachedVideo)
