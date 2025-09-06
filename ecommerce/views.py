from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Store, Product, Order, OrderItem
from .forms import UserRegisterForm
from .forms import ReviewForm
from django.contrib.auth.decorators import login_required


def home(request):
    stores = Store.objects.all()
    return render(request, 'ecommerce/home.html', {'stores': stores})


def store_detail(request, store_id):
    store = get_object_or_404(Store, id=store_id)
    products = store.products.all()
    return render(request, 'ecommerce/store_detail.html', {'store': store, 'products': products})


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all()
    review_form = ReviewForm()

    if request.method == 'POST' and 'rating' in request.POST:
        # Only process review form if POST contains review fields
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            return redirect('product_detail', product_id=product.id)

    context = {
        'product': product,
        'reviews': reviews,
        'form': review_form
    }
    return render(request, 'ecommerce/product_detail.html', context)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'ecommerce/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'ecommerce/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


# Simple cart using session
def cart_detail(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(id__in=cart.keys())
    total = sum([p.price * cart[str(p.id)] for p in products])
    return render(request, 'ecommerce/cart.html', {'products': products, 'cart': cart, 'total': total})


def cart_add(request, product_id):
    cart = request.session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session['cart'] = cart
    return redirect('cart_detail')


def cart_remove(request, product_id):
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
    request.session['cart'] = cart
    return redirect('cart_detail')


@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('home')
    products = Product.objects.filter(id__in=cart.keys())
    total = sum([p.price * cart[str(p.id)] for p in products])
    order = Order.objects.create(user=request.user, total=total, paid=True)
    for product in products:
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=cart[str(product.id)],
            price=product.price
        )
    request.session['cart'] = {}
    return render(request, 'ecommerce/checkout.html', {'order': order})


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserRegisterForm()
    return render(request, 'ecommerce/register.html', {'form': form})