from django.conf.urls import patterns, include, url
from django.conf import settings
from django.views.decorators.cache import cache_page
from views import DBFileView

urlpatterns = patterns('',
    url(r'^(?P<filename>.+)$', DBFileView.as_view())
)
