
from rest_framework import serializers
from .models import Product, ProductImage, ProductCategory
from django.utils.text import slugify


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['image']


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'slug']


class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'price_off', 'price', 'discounted_price', 'primary_image', 'stock','is_featured',]
        read_only_fields = ['slug']
    
    def get_primary_image(self, obj):
        request = self.context.get('request')
        image = obj.images.first()
        if image:
            url = image.image.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None
    def get_discounted_price(self, obj):
        return obj.final_price

    def get_description(self, obj):
        return obj.description[:150] + '...' if len(obj.description) > 100 else obj.description
    

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, required=False)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=ProductCategory.objects.all())
    discounted_price = serializers.SerializerMethodField()
    related_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['slug']
        extra_fields = ['related_products']

    def get_related_products(self, obj):
        related = Product.objects.filter(category=obj.category, status='active').exclude(pk=obj.pk)[:9]
        context = self.context
        return ProductListSerializer(related, many=True, context=context).data

    def get_discounted_price(self, obj):
        return obj.final_price

    def create(self, validated_data):
        validated_data.pop('images', None)
        if 'slug' not in validated_data or not validated_data['slug']:
            base_slug = slugify(validated_data['name'])
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            validated_data['slug'] = slug
        return Product.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('images', None)
        name = validated_data.get('name', instance.name)
        if name != instance.name:
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Product.objects.exclude(pk=instance.pk).filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

