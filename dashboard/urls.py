from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_home, name='home'),
    
    # Management pages
    path('products/', views.products_management, name='products'),
    path('orders/', views.orders_management, name='orders'),
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('users/', views.users_management, name='users'),
    path('analytics/', views.analytics, name='analytics'),
    path('settings/', views.settings_management, name='settings'),
    
    # AJAX endpoints
    path('ajax/toggle-product-status/', views.ajax_toggle_product_status, name='ajax_toggle_product_status'),
    path('ajax/toggle-product-featured/', views.ajax_toggle_product_featured, name='ajax_toggle_product_featured'),
]