from django.utils.text import slugify
from rest_framework import serializers

from .models import Video, VideoCategory, VideoOrder


class VideoCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoCategory
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']


    def create(self, validated_data):
        if 'slug' not in validated_data or not validated_data['slug']:
            base_slug = slugify(validated_data['name'])
            slug = base_slug
            counter = 1
            while VideoCategory.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            validated_data['slug'] = slug
        return super().create(validated_data)

class VideoListSerializer(serializers.ModelSerializer):
    category = VideoCategorySerializer(read_only=True)
    short_description = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    is_unlocked = serializers.SerializerMethodField()
    income = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Video
        fields = [
            'id', 'title', 'slug', 'category',
            'price', 'income', 'thumbnail', 'trailer',
            'short_description', 'duration_display',
            'views_count', 'is_featured', 'status',
            'is_unlocked', 'created_at',
        ]

    def get_short_description(self, obj):
        if len(obj.description) > 150:
            return obj.description[:150].rstrip() + '…'
        return obj.description

    def get_duration_display(self, obj):
        return obj.duration_display

    def get_is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return VideoOrder.objects.filter(user=request.user, video=obj, payment_status='captured').exists()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        is_staff = request and request.user.is_authenticated and request.user.is_staff
        if is_staff:
            data.pop('is_unlocked', None)
        else:
            data.pop('income', None)
            data.pop('status', None)
        return data


class VideoDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=VideoCategory.objects.all())
    duration_display = serializers.SerializerMethodField()
    is_unlocked = serializers.SerializerMethodField()
    related_videos = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = '__all__'
        read_only_fields = ['slug', 'views_count', 'income', 'created_at', 'updated_at']
        extra_fields = ['related_videos']

    def get_related_videos(self, obj):
        related = Video.objects.filter(category=obj.category, status='published').exclude(pk=obj.pk)[:9]
        context = self.context
        return VideoListSerializer(related, many=True, context=context).data
    
    def get_duration_display(self, obj):
        return obj.duration_display

    def get_is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return VideoOrder.objects.filter(user=request.user, video=obj, payment_status='captured').exists()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        is_staff = request and request.user.is_authenticated and request.user.is_staff
        if is_staff:
            data.pop('is_unlocked', None)
        else:
            data.pop('income', None)
            data.pop('status', None)
            # data.pop('main_video', None)

        return data

    def _unique_slug(self, title, exclude_pk=None):
        base = slugify(title)
        slug, counter = base, 1
        qs = Video.objects.exclude(pk=exclude_pk) if exclude_pk else Video.objects.all()
        while qs.filter(slug=slug).exists():
            slug = f'{base}-{counter}'
            counter += 1
        return slug

    def create(self, validated_data):
        validated_data['slug'] = self._unique_slug(validated_data['title'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('title', instance.title) != instance.title:
            validated_data['slug'] = self._unique_slug(validated_data['title'], exclude_pk=instance.pk)
        return super().update(instance, validated_data)
