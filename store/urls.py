from django.urls import path
from . import views
from . import signals



urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('brands/', views.brands, name='brands'),
    path('brand/<slug:brand_slug>/', views.brand_models, name='brand_models'),

    # Authentication
    path('login/', views.login_request, name='login'),
    path('logout/', views.store_logout, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    # path("save-auth/", views.save_auth, name="save_auth"),
    path("verify-code/", views.verify_code, name="verify_code"),
    path('auth/telegram/callback/', views.telegram_callback, name='telegram_callback'),

    # Cart and Orders
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order/<int:order_id>/payment/', views.order_payment, name='order_payment'),
    path('orders/', views.order_history, name='order_history'),
    path('favorites/', views.favorites, name='favorites'),

    # AJAX endpoints
    path('ajax/like-product/', views.ajax_like_product, name='ajax_like_product'),
    path('ajax/favorite-product/', views.ajax_favorite_product, name='ajax_favorite_product'),
    path('ajax/add-to-cart/', views.ajax_add_to_cart, name='ajax_add_to_cart'),
    path('ajax/update-cart-quantity/', views.ajax_update_cart_quantity, name='ajax_update_cart_quantity'),
    path('ajax/remove-from-cart/', views.ajax_remove_from_cart, name='ajax_remove_from_cart'),


    path('ajax/sync-cart/', views.ajax_sync_cart, name='ajax_sync_cart'),
    path('ajax/sync-favorites/', views.ajax_sync_favorites, name='ajax_sync_favorites'),

]

