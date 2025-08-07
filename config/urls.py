from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _

# Admin paneli sozlamalari (tarjima bilan)
admin.site.site_header = _('Avtokontinent.uz Admin')
admin.site.site_title = _('Avtokontinent.uz Admin')
admin.site.index_title = _('Welcome to Avtokontinent.uz Administration')

# URL sozlamalari
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # Til o‘zgartirish uchun
] + i18n_patterns(
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('store.urls')),

)

# Statik va media fayllar
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)