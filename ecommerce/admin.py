from django.contrib import admin
from .models import Store, Product, Review, Order, OrderItem, ResetToken

admin.site.register(Store)
admin.site.register(Product)
admin.site.register(Review)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ResetToken)
