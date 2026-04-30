from rest_framework import serializers
from .models import BusinessSetting


class BusinessSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSetting
        fields = '__all__'