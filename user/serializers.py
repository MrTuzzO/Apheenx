from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from .models import OTP, User
from .utils import send_otp_email
from .models import PasswordResetToken

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("name", "email", "password", "password_confirm")

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            name=validated_data["name"],
            password=validated_data["password"],
        )
        send_otp_email(user, OTP.PURPOSE_EMAIL_VERIFICATION)
        return user


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        if user.is_email_verified:
            raise serializers.ValidationError({"email": "Email is already verified."})

        otp_obj = (
            OTP.objects
            .filter(user=user, code=attrs["otp"], purpose=OTP.PURPOSE_EMAIL_VERIFICATION, is_used=False)
            .last()
        )
        if not otp_obj or otp_obj.is_expired:
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."})

        attrs["user"] = user
        attrs["otp_obj"] = otp_obj
        return attrs



class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(choices=OTP.PURPOSE_CHOICES)

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        if attrs["purpose"] == OTP.PURPOSE_EMAIL_VERIFICATION and user.is_email_verified:
            raise serializers.ValidationError({"email": "Email is already verified."})

        attrs["user"] = user
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError({"detail": "Invalid credentials."})
        if not user.is_email_verified:
            raise serializers.ValidationError({"detail": "Email not verified. Please verify your email first."})
        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account is disabled."})

        refresh = RefreshToken.for_user(user)
        return {
            "user": user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()


    class Meta:
        model = User
        fields = ("id", "name", "email", "profile_image", "role", "is_email_verified", "created_at")
        read_only_fields = ("id", "email", "role", "is_email_verified", "created_at")

    def update(self, instance, validated_data):
        profile_image = self.context["request"].FILES.get("profile_image")
        if profile_image is not None:
            instance.profile_image = profile_image
        elif "profile_image" in self.context["request"].data and not self.context["request"].FILES.get("profile_image"):
            instance.profile_image = None
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def get_role(self, obj):
        if obj.is_superuser or obj.is_staff:
            return "admin"
        return "user"

    def get_profile_image(self, obj):
        request = self.context.get('request')
        if obj.profile_image:
            url = obj.profile_image.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return attrs



class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()



class VerifyPasswordResetOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        generic_error = {"otp": "Invalid or expired OTP."}

        try:
            user = User.objects.get(email=attrs["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError(generic_error)

        otp_obj = (
            OTP.objects
            .filter(user=user, purpose=OTP.PURPOSE_PASSWORD_RESET, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not otp_obj or otp_obj.is_expired or otp_obj.attempts_exceeded:
            raise serializers.ValidationError(generic_error)

        if otp_obj.code != attrs["otp"]:
            otp_obj.attempts += 1
            update_fields = ["attempts"]
            if otp_obj.attempts >= getattr(settings, "OTP_MAX_ATTEMPTS", 5):
                otp_obj.is_used = True
                update_fields.append("is_used")
            otp_obj.save(update_fields=update_fields)
            raise serializers.ValidationError(generic_error)

        attrs["user"] = user
        attrs["otp_obj"] = otp_obj
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})

        token_obj = (
            PasswordResetToken.objects
            .select_related("user")
            .filter(
                token_hash=PasswordResetToken.hash_token(attrs["reset_token"]),
                is_used=False,
            )
            .first()
        )
        if not token_obj or token_obj.is_expired:
            raise serializers.ValidationError({"reset_token": "Invalid or expired reset token."})

        attrs["user"] = token_obj.user
        attrs["token_obj"] = token_obj
        return attrs