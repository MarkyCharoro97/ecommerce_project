from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('store/<int:store_id>/', views.store_detail, name='store_detail'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
