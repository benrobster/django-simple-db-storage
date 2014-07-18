# Create your views here.
from datetime import timedelta
import mimetypes
import datetime
from django.http import HttpResponse
from django.middleware.gzip import GZipMiddleware
from django.utils.decorators import method_decorator
from django.views.decorators.http import last_modified
from django.views.generic.base import View
from simple_db_storage import SimpleDatabaseStorage, CachedDatabaseStorage
from django.views.decorators.cache import cache_page


gzip_middleware = GZipMiddleware()



class DBFileView(View):

    def get(self, request, **kwargs):
        storage = CachedDatabaseStorage()
        filename = kwargs['filename']
        file = storage.open(filename, 'rb')
        file_content = file.read()
        content_type, encoding = mimetypes.guess_type(filename)
        response = HttpResponse(file_content, content_type=content_type)
        if encoding: # its already encoded (e.g. with gzip)
            response['Content-Encoding'] = encoding
            response['Content-Length'] = str(len(file_content))
        else: # gzip it
            gzip_middleware.process_response(request, response)

        # if we start using this for more than just images, the caching may be a bit extreme ... will need to rethink.
        expires = datetime.datetime.utcnow() + timedelta(days=(2 * 365)) # 2 yrs.
        response['Expires'] =  expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        response['Cache-Control'] = 'max-age=63072000, public' # 2 yrs
        return response

    def dispatch(self, request, *args, **kwargs):
        """
        Setup to return a browser-caching enabling 304 (Not-modified) status
        and doesn't bother the cache or db (besides looking at the modified time)
        """
        # see http://stackoverflow.com/questions/12993951/using-etag-last-modified-decorators-with-djangos-class-based-generic-views

        def _last_modified(request, *args, **kwargs):
            storage = CachedDatabaseStorage()
            return storage.modified_time(kwargs['filename'])

        @last_modified(_last_modified)
        def _dispatch(request, *args, **kwargs):
            return super(DBFileView, self).dispatch(request, *args, **kwargs)
        return _dispatch(request, *args, **kwargs)
