from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import json

from .models import User, Store, Product, Category, Review, Order, OrderItem, Cart, CartItem, PasswordResetToken
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, StoreForm, 
    ProductForm, ReviewForm, UserProfileForm, PasswordResetRequestForm, PasswordResetForm
)


def home(request):
    """Homepage view"""
    featured_products = Product.objects.filter(is_active=True)[:6]
    context = {
        'featured_products': featured_products,
    }
    return render(request, 'ecommerce/home.html', context)


def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created successfully.')
            
            if user.is_vendor():
                return redirect('ecommerce:vendor_dashboard')
            else:
                return redirect('ecommerce:home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'ecommerce/auth/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                elif user.is_vendor():
                    return redirect('ecommerce:vendor_dashboard')
                else:
                    return redirect('ecommerce:home')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'ecommerce/auth/login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('ecommerce:home')


def product_list(request):
    """Product listing view with search and filtering"""
    products = Product.objects.filter(is_active=True).select_related('store', 'category')
    categories = Category.objects.all()
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(store__name__icontains=query)
        )
    
    # Category filtering
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Sorting
    sort_by = request.GET.get('sort')
    if sort_by in ['name', '-name', 'price', '-price', '-created_at']:
        products = products.order_by(sort_by)
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'categories': categories,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    return render(request, 'ecommerce/products/list.html', context)


def product_detail(request, product_id):
    """Product detail view"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    reviews = product.reviews.all().order_by('-created_at')
    
    # Calculate average rating
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    context = {
        'product': product,
        'reviews': reviews,
        'average_rating': round(average_rating),
    }
    return render(request, 'ecommerce/products/detail.html', context)


@login_required
def add_review(request, product_id):
    """Add review for a product"""
    if not request.user.is_buyer():
        messages.error(request, 'Only buyers can leave reviews.')
        return redirect('ecommerce:product_detail', product_id=product_id)
    
    product = get_object_or_404(Product, id=product_id)
    
    # Check if user already reviewed this product
    existing_review = Review.objects.filter(product=product, buyer=request.user).first()
    if existing_review:
        messages.warning(request, 'You have already reviewed this product.')
        return redirect('ecommerce:product_detail', product_id=product_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.buyer = request.user
            
            # Check if user has purchased this product (verified review)
            has_purchased = OrderItem.objects.filter(
                order__buyer=request.user,
                product=product
            ).exists()
            review.is_verified = has_purchased
            
            review.save()
            messages.success(request, 'Your review has been added successfully!')
            return redirect('ecommerce:product_detail', product_id=product_id)
    
    return redirect('ecommerce:product_detail', product_id=product_id)


@login_required
def vendor_dashboard(request):
    """Vendor dashboard view"""
    if not request.user.is_vendor():
        messages.error(request, 'Access denied. Vendor account required.')
        return redirect('ecommerce:home')
    
    stores = request.user.stores.all()
    products = Product.objects.filter(store__vendor=request.user)
    
    # Calculate statistics
    total_stores = stores.count()
    total_products = products.count()
    total_orders = OrderItem.objects.filter(product__store__vendor=request.user).count()
    total_revenue = sum(
        item.get_total_price() for item in 
        OrderItem.objects.filter(product__store__vendor=request.user)
    )
    
    recent_stores = stores[:4]
    recent_products = products.order_by('-created_at')[:5]
    
    context = {
        'total_stores': total_stores,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_stores': recent_stores,
        'recent_products': recent_products,
    }
    return render(request, 'ecommerce/vendor/dashboard.html', context)


@login_required
def my_stores(request):
    """View for managing vendor stores"""
    if not request.user.is_vendor():
        messages.error(request, 'Access denied. Vendor account required.')
        return redirect('ecommerce:home')
    
    stores = request.user.stores.all()
    context = {'stores': stores}
    return render(request, 'ecommerce/vendor/stores.html', context)


@login_required
def create_store(request):
    """Create new store view"""
    if not request.user.is_vendor():
        messages.error(request, 'Access denied. Vendor account required.')
        return redirect('ecommerce:home')
    
    if request.method == 'POST':
        form = StoreForm(request.POST)
        if form.is_valid():
            store = form.save(commit=False)
            store.vendor = request.user
            store.save()
            messages.success(request, f'Store "{store.name}" created successfully!')
            return redirect('ecommerce:my_stores')
    else:
        form = StoreForm()
    
    return render(request, 'ecommerce/vendor/create_store.html', {'form': form})


@login_required
def edit_store(request, store_id):
    """Edit store view"""
    store = get_object_or_404(Store, id=store_id, vendor=request.user)
    
    if request.method == 'POST':
        form = StoreForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, f'Store "{store.name}" updated successfully!')
            return redirect('ecommerce:my_stores')
    else:
        form = StoreForm(instance=store)
    
    return render(request, 'ecommerce/vendor/edit_store.html', {'form': form, 'store': store})


@login_required
def delete_store(request, store_id):
    """Delete store view"""
    store = get_object_or_404(Store, id=store_id, vendor=request.user)
    
    if request.method == 'POST':
        store_name = store.name
        store.delete()
        messages.success(request, f'Store "{store_name}" deleted successfully!')
        return redirect('ecommerce:my_stores')
    
    return render(request, 'ecommerce/vendor/delete_store.html', {'store': store})


@login_required
def store_products(request, store_id):
    """View products for a specific store"""
    store = get_object_or_404(Store, id=store_id, vendor=request.user)
    products = store.products.all().order_by('-created_at')
    
    context = {
        'store': store,
        'products': products,
    }
    return render(request, 'ecommerce/vendor/store_products.html', context)


@login_required
def create_product(request, store_id):
    """Create new product view"""
    store = get_object_or_404(Store, id=store_id, vendor=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.store = store
            product.save()
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('ecommerce:store_products', store_id=store.id)
    else:
        form = ProductForm()
    
    return render(request, 'ecommerce/vendor/create_product.html', {'form': form, 'store': store})


@login_required
def edit_product(request, product_id):
    """Edit product view"""
    product = get_object_or_404(Product, id=product_id, store__vendor=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('ecommerce:store_products', store_id=product.store.id)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'ecommerce/vendor/edit_product.html', {'form': form, 'product': product})


@login_required
def delete_product(request, product_id):
    """Delete product view"""
    product = get_object_or_404(Product, id=product_id, store__vendor=request.user)
    
    if request.method == 'POST':
        product_name = product.name
        store_id = product.store.id
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('ecommerce:store_products', store_id=store_id)
    
    return render(request, 'ecommerce/vendor/delete_product.html', {'product': product})


@login_required
def profile(request):
    """User profile view"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('ecommerce:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'ecommerce/auth/profile.html', {'form': form})



# Cart and Checkout Views

def get_or_create_cart(request):
    """Helper function to get or create cart for session"""
    if not request.session.session_key:
        request.session.create()
    
    cart, created = Cart.objects.get_or_create(
        session_key=request.session.session_key
    )
    return cart


@require_POST
def add_to_cart(request):
    """Add product to cart via AJAX"""
    if not request.user.is_authenticated or not request.user.is_buyer():
        return JsonResponse({'success': False, 'message': 'Login required'})
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        if not product.is_in_stock() or product.quantity_in_stock < quantity:
            return JsonResponse({'success': False, 'message': 'Insufficient stock'})
        
        cart = get_or_create_cart(request)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.quantity_in_stock:
                cart_item.quantity = product.quantity_in_stock
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Product added to cart',
            'cart_count': cart.get_total_items()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def cart_count(request):
    """Get cart item count via AJAX"""
    if not request.session.session_key:
        return JsonResponse({'count': 0})
    
    try:
        cart = Cart.objects.get(session_key=request.session.session_key)
        count = cart.get_total_items()
    except Cart.DoesNotExist:
        count = 0
    
    return JsonResponse({'count': count})


@login_required
def cart_view(request):
    """Shopping cart view"""
    if not request.user.is_buyer():
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('ecommerce:home')
    
    cart = None
    cart_items = []
    total_price = 0
    
    if request.session.session_key:
        try:
            cart = Cart.objects.get(session_key=request.session.session_key)
            cart_items = cart.items.all().select_related('product', 'product__store')
            total_price = cart.get_total_price()
        except Cart.DoesNotExist:
            pass
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'ecommerce/buyer/cart.html', context)


@login_required
@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    if not request.user.is_buyer():
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    try:
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        data = json.loads(request.body)
        new_quantity = int(data.get('quantity', 1))
        
        if new_quantity <= 0:
            cart_item.delete()
            return JsonResponse({'success': True, 'message': 'Item removed from cart'})
        
        if new_quantity > cart_item.product.quantity_in_stock:
            return JsonResponse({
                'success': False, 
                'message': f'Only {cart_item.product.quantity_in_stock} items available'
            })
        
        cart_item.quantity = new_quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart updated',
            'item_total': cart_item.get_total_price(),
            'cart_total': cart.get_total_price(),
            'cart_count': cart.get_total_items()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    if not request.user.is_buyer():
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('ecommerce:cart')
    
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name
    cart_item.delete()
    
    messages.success(request, f'"{product_name}" removed from cart.')
    return redirect('ecommerce:cart')


@login_required
def checkout(request):
    """Checkout process"""
    if not request.user.is_buyer():
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('ecommerce:home')
    
    cart = None
    cart_items = []
    
    if request.session.session_key:
        try:
            cart = Cart.objects.get(session_key=request.session.session_key)
            cart_items = cart.items.all().select_related('product', 'product__store')
        except Cart.DoesNotExist:
            pass
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('ecommerce:cart')
    
    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address')
        if not shipping_address:
            messages.error(request, 'Shipping address is required.')
            return render(request, 'ecommerce/buyer/checkout.html', {'cart_items': cart_items, 'cart': cart})
        
        # Create order
        order = Order.objects.create(
            buyer=request.user,
            total_amount=cart.get_total_price(),
            shipping_address=shipping_address
        )
        
        # Create order items and update product stock
        for cart_item in cart_items:
            if cart_item.product.quantity_in_stock >= cart_item.quantity:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price_at_purchase=cart_item.product.price
                )
                
                # Update product stock
                cart_item.product.quantity_in_stock -= cart_item.quantity
                cart_item.product.save()
            else:
                messages.error(request, f'Insufficient stock for {cart_item.product.name}')
                return render(request, 'ecommerce/buyer/checkout.html', {'cart_items': cart_items, 'cart': cart})
        
        # Clear cart
        cart.delete()
        
        # Send confirmation email (placeholder - will be implemented in next phase)
        # send_order_confirmation_email(order)
        
        messages.success(request, f'Order #{order.order_id} placed successfully!')
        return redirect('ecommerce:order_confirmation', order_id=order.order_id)
    
    context = {
        'cart_items': cart_items,
        'cart': cart,
    }
    return render(request, 'ecommerce/buyer/checkout.html', context)


@login_required
def order_confirmation(request, order_id):
    """Order confirmation view"""
    order = get_object_or_404(Order, order_id=order_id, buyer=request.user)
    context = {'order': order}
    return render(request, 'ecommerce/buyer/order_confirmation.html', context)


@login_required
def my_orders(request):
    """View user's orders"""
    if not request.user.is_buyer():
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('ecommerce:home')
    
    orders = request.user.orders.all().order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    return render(request, 'ecommerce/buyer/orders.html', context)


@login_required
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, order_id=order_id, buyer=request.user)
    context = {'order': order}
    return render(request, 'ecommerce/buyer/order_detail.html', context)

