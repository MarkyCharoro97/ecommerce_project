from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Store, Product, Order, OrderItem

class EcommerceModelsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.store = Store.objects.create(owner=self.user, name='Test Store')
        self.product = Product.objects.create(
            store=self.store,
            name='Test Product',
            price=10.0,
            stock=100
        )

    def test_store_creation(self):
        self.assertEqual(self.store.name, 'Test Store')
        self.assertEqual(self.store.owner.username, 'testuser')

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.store, self.store)
        self.assertEqual(self.product.price, 10.0)

class EcommerceViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.store = Store.objects.create(owner=self.user, name='Test Store')
        self.product = Product.objects.create(
            store=self.store,
            name='Test Product',
            price=10.0,
            stock=100
        )

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Store')

    def test_store_detail_view(self):
        response = self.client.get(reverse('store_detail', args=[self.store.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Store')
        self.assertContains(response, 'Test Product')

    def test_product_detail_view(self):
        response = self.client.get(reverse('product_detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_user_registration(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'strongpassword123',
            'password2': 'strongpassword123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after registration
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_user_login_logout(self):
        login = self.client.login(username='testuser', password='12345')
        self.assertTrue(login)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)  # Redirect after logout

class EcommerceCartTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.store = Store.objects.create(owner=self.user, name='Test Store')
        self.product = Product.objects.create(
            store=self.store,
            name='Test Product',
            price=10.0,
            stock=100
        )

    def test_cart_add_remove(self):
        # Add to cart
        response = self.client.get(reverse('cart_add', args=[self.product.id]))
        self.assertEqual(self.client.session['cart'][str(self.product.id)], 1)

        # Remove from cart
        response = self.client.get(reverse('cart_remove', args=[self.product.id]))
        self.assertFalse(str(self.product.id) in self.client.session.get('cart', {}))

    def test_checkout_creates_order(self):
        self.client.login(username='testuser', password='12345')
        session = self.client.session
        session['cart'] = {str(self.product.id): 2}
        session.save()

        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Order.objects.filter(user=self.user).exists())
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.total, 20.0)
        self.assertEqual(order.items.first().quantity, 2)
