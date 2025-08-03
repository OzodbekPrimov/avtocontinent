from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Authentication
    path('login/', views.dashboard_login, name='login'),
    path('logout/', views.dashboard_logout, name='logout'),

    # Main dashboard
    path('', views.dashboard_home, name='home'),

    # Banners CRUD
    path('banners/', views.banners_management, name='banners'),
    path('banners/create/', views.banner_create, name='banner_create'),
    path('banners/<int:banner_id>/edit/', views.banner_edit, name='banner_edit'),
    path('banners/<int:banner_id>/delete/', views.banner_delete, name='banner_delete'),

    # Brands CRUD
    path('brands/', views.brands_management, name='brands'),
    path('brands/create/', views.brand_create, name='brand_create'),
    path('brands/<int:brand_id>/edit/', views.brand_edit, name='brand_edit'),
    path('brands/<int:brand_id>/delete/', views.brand_delete, name='brand_delete'),

    # Car Models CRUD
    path('models/', views.models_management, name='models'),
    path('models/create/', views.model_create, name='model_create'),
    path('models/<int:model_id>/edit/', views.model_edit, name='model_edit'),
    path('models/<int:model_id>/delete/', views.model_delete, name='model_delete'),

    # Categories CRUD
    path('categories/', views.categories_management, name='categories'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:category_id>/delete/', views.category_delete, name='category_delete'),

    # Products CRUD
    path('products/', views.products_management, name='products'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='product_delete'),

    # Orders Management
    path('orders/', views.orders_management, name='orders'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),

    # Users Management
    path('users/', views.users_management, name='users'),

    # Analytics
    path('analytics/', views.analytics, name='analytics'),

    # Settings
    path('settings/', views.settings_management, name='settings'),

    # AJAX endpoints
    path('ajax/toggle-product-status/', views.ajax_toggle_product_status, name='ajax_toggle_product_status'),
    path('ajax/toggle-product-featured/', views.ajax_toggle_product_featured, name='ajax_toggle_product_featured'),
    path('ajax/toggle-banner-status/', views.ajax_toggle_banner_status, name='ajax_toggle_banner_status'),

    path('ajax/toggle-brand-status/', views.ajax_toggle_brand_status, name='ajax_toggle_brand_status'),
    path('ajax/delete-brand/', views.ajax_delete_brand, name='ajax_delete_brand'),

    path('ajax/toggle-model-status/', views.ajax_toggle_model_status, name='ajax_toggle_model_status'),
    path('ajax/delete-model/', views.ajax_delete_model, name='ajax_delete_model'),

    path('ajax/toggle-category-status/', views.ajax_toggle_category_status, name='ajax_toggle_category_status'),
    path('ajax/update-order-status/', views.ajax_update_order_status, name='ajax_update_order_status'),
    path('ajax/confirm-payment/', views.ajax_confirm_payment, name='ajax_confirm_payment'),
    path('ajax/reject-payment/', views.ajax_reject_payment, name='ajax_reject_payment'),



]