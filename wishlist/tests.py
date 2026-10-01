from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.contenttypes.models import ContentType

from product.models import Product, ProductCategory
from user.models import User
from video.models import Video, VideoCategory
from .models import WishlistItem

class WishlistAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            name='Regular User',
            password='password123',
        )
        self.product_category = ProductCategory.objects.create(name='Shoes', slug='shoes')
        self.video_category = VideoCategory.objects.create(name='Fitness', slug='fitness')
        
        self.product = Product.objects.create(
            name='Running Shoe',
            slug='running-shoe',
            price='120.00',
            stock=5,
            category=self.product_category,
            status='active',
        )
        self.video = Video.objects.create(
            title='Core Workout',
            slug='core-workout',
            category=self.video_category,
            price='15.00',
            status='published',
        )

    def test_toggle_product_wishlist(self):
        self.client.force_authenticate(self.user)
        # আপনার বর্তমান URL স্ট্রাকচার অনুযায়ী
        url = f'/api/wishlist/products/{self.product.id}/toggle/'
        
        # Add to wishlist
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['action'], 'added')
        
        # Remove from wishlist (Toggle)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['action'], 'removed')

    def test_toggle_video_wishlist(self):
        self.client.force_authenticate(self.user)
        url = f'/api/wishlist/videos/{self.video.id}/toggle/'
        
        # Add to wishlist
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['action'], 'added')