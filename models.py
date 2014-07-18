import base64
from django.db import models

# Create your models here.
class DBFile(models.Model):

    file_name = models.CharField("File Name", max_length=255, primary_key=True)
    _data = models.TextField(db_column='data', blank=True)
    size = models.IntegerField()
    modified_time = models.DateTimeField(auto_now=True)
    created_time = models.DateTimeField(auto_now_add=True)

    def set_data(self, data):
        self._data = base64.encodestring(data)

    def get_data(self):
        return base64.decodestring(self._data)

    data = property(get_data, set_data)
