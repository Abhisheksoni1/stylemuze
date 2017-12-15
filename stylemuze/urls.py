"""stylemuze URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.conf import settings

from stylemuzeapp import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^login$', views.login),
    url(r'^register$', views.register),
    url(r'^get_feed$', views.get_feed),
    url(r'^get_users$', views.get_users),
    url(r'^get_brands$', views.get_brands),
    url(r'^get_posts$', views.get_user_posts),
    url(r'^get_user_details$', views.get_user_details),
    url(r'^vote_yes$', views.vote_yes),
    url(r'^get_updated_feed', views.get_feed_update),
    url(r'^vote_no$', views.vote_no),
    url(r'^get_item_comments$', views.get_item_comments),
    url(r'^add_comment$', views.add_comment),
    url(r'^upload_post$', views.upload_post),
    url(r'^search_user$', views.search_user),
    url(r'^search_brand$', views.search_brand),
    url(r'^add_bff$', views.add_bff),
    url(r'^add_follow$', views.add_follow),
    url(r'^remove_bff$', views.remove_bff),
    url(r'^remove_follow$', views.remove_follow),
    url(r'^get_notifications$', views.get_notifications),
    url(r'^get_single_post$', views.get_single_post),
    url(r'^mark_as_read$', views.mark_as_read),
    url(r'^update_gcm_id$', views.update_gcm_id),
    url(r'^change_like$', views.change_like),
    url(r'^change_favorite$', views.change_favorite),
    url(r'^get_user_favorites$', views.get_user_favorites),
    url(r'^get_brand_posts$', views.get_brand_posts),
    url(r'^change_image$', views.change_image),
    url(r'^get_item_likes$', views.get_item_likes),
    url(r'^get_image/(?P<name>.*)$', views.get_image),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
]
