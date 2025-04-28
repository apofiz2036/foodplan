from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from planner import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('auth/', views.auth_view, name='auth'),
    path('registration/', views.register_view, name='registration'),
    path('lk/', views.lk_view, name='lk'),
    path('order/', views.order_view, name='order'),
    path('card/', views.card, name='card'),
    path('logout/', views.logout_view, name='logout'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('card/<int:dish_id>/', views.dish_card, name='card'),
    path('process_order/', views.process_order, name='process_order'),
    path('update_avatar/', views.update_avatar, name='update_avatar'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
