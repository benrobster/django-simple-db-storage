""" Copyright 2012, Nutrislice Inc.  All rights reserved """


import StringIO
import base64
import urlparse
from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage
from models import DBFile

from django.core.cache import cache

def file_from_data(data, name, mode):
    mem_file = StringIO.StringIO(data)
    mem_file.name = name
    mem_file.mode = mode
    file = File(mem_file)
    return file

def normalize_name(name):
    return name.replace('\\', '/').replace(' ', '_').replace('\n', '__')

class SimpleDatabaseStorage(Storage):

    def __init__(self):
        self.base_url = getattr(settings, "DB_FILES_URL", '/dbfiles/')

    def _get_cursor(self):
        from django.db import connections
        return connections['default'].cursor()

    def _open(self, name, mode='rb'):
        name = normalize_name(name)
        try:
            dbfile = DBFile.objects.get(file_name=name)
        except DBFile.DoesNotExist:
            raise IOError ("No such file exists in the DB: " + name)
        return file_from_data(dbfile.data, name, mode)

    def _save(self, name, content):
        name = normalize_name(name)
        try:
            dbfile = DBFile.objects.get(file_name=name)
        except DBFile.DoesNotExist:
            dbfile = DBFile(file_name=name)
        raw_data = content.read()
        dbfile.size = len(raw_data)
        dbfile.data = raw_data # should probably do this in chunks
        dbfile.save()
        del raw_data
        return name

    def get_available_name(self, name):
        """If filename exist, blob will be overwritten,
         to change this remove this function so Storage.get_available_name(self, name) will be used to generate new filename.
        """
        return name

    def delete(self, name):
        name = normalize_name(name)
        DBFile.objects.filter(file_name=name).delete()

    def exists(self, name):
        name = normalize_name(name)
        return len(DBFile.objects.filter(file_name=name).only('file_name'))>0

    def listdir(self, path):
        raise NotImplementedError

    def size(self, name):
        name = normalize_name(name)
        try:
            return DBFile.objects.filter(file_name=name).only('size')[0].size
        except IndexError:
            return None

    def url(self, name):
        name = normalize_name(name)
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self.base_url, name).replace('\\', '/')

    def created_time(self, name):
        name = normalize_name(name)
        try:
            return DBFile.objects.filter(file_name=name).only('created_time')[0].created_time
        except IndexError:
            return None

    def modified_time(self, name):
        name = normalize_name(name)
        try:
            return DBFile.objects.filter(file_name=name).only('modified_time')[0].modified_time
        except IndexError:
            return None




class CachedDatabaseStorage(SimpleDatabaseStorage):
    """ Uses cache to store files & their meta data, with database as a fallback and failsafe.
    """

    CACHE_TIMEOUT = 100000000

    def get_and_cache(self, name):
        try:
            dbfile = DBFile.objects.get(file_name=name)
            cache.set(name, dbfile, self.CACHE_TIMEOUT)
            return dbfile
        except DBFile.DoesNotExist:
            return None

    def get_file_attr_or_None(self, file_name, attr_name):
        """
        gets a file from the cache if available.  If its not in the cache
        """
        name = normalize_name(file_name)
        file = cache.get(name)
        if not file:
            file = self.get_and_cache(file_name)
            if not file:
                return None
        return getattr(file, attr_name)

    def _open(self, name, mode='rb'):
        name = normalize_name(name)
        cachefile = cache.get(name)
        if cachefile:
            return file_from_data(cachefile.data, name, mode)
        else:
            dbfile = self.get_and_cache(name)
            if dbfile:
                return file_from_data(dbfile.data, name, mode)
            else:
                raise IOError ("No such file exists in the DB: " + name)


    def _save(self, name, content):
        name = normalize_name(name)
        try:
            dbfile = DBFile.objects.get(file_name=name)
        except DBFile.DoesNotExist:
            dbfile = DBFile(file_name=name)
        raw_data = content.read()
        dbfile.size = len(raw_data)
        dbfile.data = raw_data
        dbfile.save()
        cache.set(name, dbfile, self.CACHE_TIMEOUT)
        del raw_data
        return name

    def delete(self, name):
        name = normalize_name(name)
        super(CachedDatabaseStorage, self).delete(name)
        cache.delete(name)

    def exists(self, name):
       name = normalize_name(name)
       return bool(cache.get(name) or self.get_and_cache(name))

    def size(self, name):
       return self.get_file_attr_or_None(name, 'size')

    def created_time(self, name):
        return self.get_file_attr_or_None(name, 'created_time')

    def modified_time(self, name):
        """
         we cache modified time seperately because ez thumbnails is pretty intensive on checking this (it uses
         it to check for existence and freshness) and we don't want to have to pull the whole file from cache every time.
        """
        modified_time = cache.get(name + "__modified_time")
        if not modified_time:
            modified_time = self.get_file_attr_or_None(name, 'modified_time')
            if modified_time:
                cache.set(name + "__modified_time",modified_time)
        return modified_time




