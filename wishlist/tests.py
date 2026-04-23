from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from product.models import Product, ProductCategory
from user.models import User
from video.models import Video, VideoCategory
from .models import Wishlist


class WishlistAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            name='Regular User',
            password='password123',
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            name='Other User',
            password='password123',
        )
        self.product_category = ProductCategory.objects.create(name='Shoes', slug='shoes')
        self.video_category = VideoCategory.objects.create(name='Fitness', slug='fitness')
        self.product = Product.objects.create(
            name='Running Shoe',
            slug='running-shoe',
            description='A' * 160,
            price='120.00',
            stock=5,
            category=self.product_category,
            status='active',
        )
        self.draft_product = Product.objects.create(
            name='Draft Shoe',
            slug='draft-shoe',
            description='Draft product',
            price='80.00',
            stock=3,
            category=self.product_category,
            status='draft',
        )
        self.video = Video.objects.create(
            title='Core Workout',
            slug='core-workout',
            category=self.video_category,
            description='B' * 160,
            price='15.00',
            status='published',
        )
        self.draft_video = Video.objects.create(
            title='Hidden Workout',
            slug='hidden-workout',
            category=self.video_category,
            description='Hidden video',
            price='12.00',
            status='draft',
        )

    def test_authenticated_user_can_add_product_to_wishlist(self):
        self.client.force_authenticate(self.user)

        response = self.client.post('/api/v1/wishlist/products/', {'slug': self.product.slug}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Wishlist.objects.filter(user=self.user, product=self.product).exists())

    def test_authenticated_user_can_add_video_to_wishlist(self):
        self.client.force_authenticate(self.user)

        response = self.client.post('/api/v1/wishlist/videos/', {'slug': self.video.slug}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Wishlist.objects.filter(user=self.user, video=self.video).exists())

    def test_duplicate_product_add_is_rejected(self):
        Wishlist.objects.create(user=self.user, product=self.product)
        self.client.force_authenticate(self.user)

        response = self.client.post('/api/v1/wishlist/products/', {'slug': self.product.slug}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['slug'][0], 'Product is already in your wishlist.')

    def test_remove_product_wishlist_item(self):
        Wishlist.objects.create(user=self.user, product=self.product)
        self.client.force_authenticate(self.user)

        response = self.client.delete(f'/api/v1/wishlist/products/{self.product.slug}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Wishlist.objects.filter(user=self.user, product=self.product).exists())

    def test_remove_missing_product_wishlist_item_returns_404(self):
        self.client.force_authenticate(self.user)

        response = self.client.delete(f'/api/v1/wishlist/products/{self.product.slug}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_product_wishlist_list_returns_only_current_users_items_with_pagination(self):
        Wishlist.objects.create(user=self.user, product=self.product)
        Wishlist.objects.create(user=self.other_user, product=self.draft_product)
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/v1/wishlist/products/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['slug'], self.product.slug)

    def test_video_wishlist_list_returns_only_current_users_items_with_pagination(self):
        Wishlist.objects.create(user=self.user, video=self.video)
        Wishlist.objects.create(user=self.other_user, video=self.draft_video)
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/v1/wishlist/videos/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['slug'], self.video.slug)

    def test_inactive_product_cannot_be_added_by_non_staff_user(self):
        self.client.force_authenticate(self.user)

        response = self.client.post('/api/v1/wishlist/products/', {'slug': self.draft_product.slug}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['slug'][0], 'Product not found.')

    def test_unpublished_video_cannot_be_added_by_non_staff_user(self):
        self.client.force_authenticate(self.user)

        response = self.client.post('/api/v1/wishlist/videos/', {'slug': self.draft_video.slug}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['slug'][0], 'Video not found.')

    def test_anonymous_requests_are_rejected(self):
        product_list = self.client.get('/api/v1/wishlist/products/')
        product_add = self.client.post('/api/v1/wishlist/products/', {'slug': self.product.slug}, format='json')
        product_delete = self.client.delete(f'/api/v1/wishlist/products/{self.product.slug}/')
        video_list = self.client.get('/api/v1/wishlist/videos/')
        video_add = self.client.post('/api/v1/wishlist/videos/', {'slug': self.video.slug}, format='json')
        video_delete = self.client.delete(f'/api/v1/wishlist/videos/{self.video.slug}/')

        self.assertEqual(product_list.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(product_add.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(product_delete.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(video_list.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(video_add.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(video_delete.status_code, status.HTTP_401_UNAUTHORIZED)


class WishlistModelConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='constraints@example.com',
            name='Constraint User',
            password='password123',
        )
        product_category = ProductCategory.objects.create(name='Bags', slug='bags')
        video_category = VideoCategory.objects.create(name='Yoga', slug='yoga')
        self.product = Product.objects.create(
            name='Travel Bag',
            slug='travel-bag',
            description='Bag',
            price='55.00',
            stock=4,
            category=product_category,
            status='active',
        )
        self.video = Video.objects.create(
            title='Yoga Basics',
            slug='yoga-basics',
            category=video_category,
            description='Video',
            price='10.00',
            status='published',
        )

    def test_exactly_one_target_constraint_blocks_both_null(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Wishlist.objects.create(user=self.user)

    def test_exactly_one_target_constraint_blocks_both_targets(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Wishlist.objects.create(user=self.user, product=self.product, video=self.video)

