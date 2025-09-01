from django.urls import path
from . import views

app_name = 'ecommerce'

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/<int:product_id>/review/', views.add_review, name='add_review'),
    
    # Vendor URLs
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/stores/', views.my_stores, name='my_stores'),
    path('vendor/stores/create/', views.create_store, name='create_store'),
    path('vendor/stores/<int:store_id>/edit/', views.edit_store, name='edit_store'),
    path('vendor/stores/<int:store_id>/delete/', views.delete_store, name='delete_store'),
    path('vendor/stores/<int:store_id>/products/', views.store_products, name='store_products'),
    path('vendor/stores/<int:store_id>/products/create/', views.create_product, name='create_product'),
    path('vendor/products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('vendor/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
]


    
    # Cart and Checkout URLs
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/count/', views.cart_count, name='cart_count'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.my_orders, name='my_orders'),
    path('orders/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<uuid:order_id>/confirmation/', views.order_confirmation, name='order_confirmation'),

