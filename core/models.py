from django.db import models

class BusinessSetting(models.Model):
    about_us = models.TextField(blank=True, null=True)
    privacy_policy = models.TextField(blank=True, null=True)
    terms_of_service = models.TextField(blank=True, null=True)
    refund_policy = models.TextField(blank=True, null=True)
    shipping_policy = models.TextField(blank=True, null=True)

    # Contact info
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    # Social media links
    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return "Business Settings"
