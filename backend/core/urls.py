from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.urls import path



urlpatterns = [
    path("", views.BasePageView.as_view(), name="home"),    

]


urlpatterns += [
    path("sitemap.xml", sitemap, name="django.contrib.sitemaps.views.sitemap",)
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

