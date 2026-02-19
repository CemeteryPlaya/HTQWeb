from rest_framework import serializers
from .models import Item

from media_manager.models import News

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        # Какие поля отдаются в API
        fields = ['id', 'title', 'description', 'owner', 'created_at']
        # Эти поля нельзя менять с frontend
        read_only_fields = ['id', 'owner', 'created_at']


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ['id', 'title', 'slug', 'summary', 'content', 'image', 'category', 'published', 'published_at', 'created_at']
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Return relative image URL so it works through Vite proxy from any host
        if instance.image:
            data['image'] = instance.image.url  # e.g. /media/news_images/photo.jpg
        return data

from django.contrib.auth.models import User
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    firstName = serializers.CharField(source='user.first_name', read_only=True)
    lastName = serializers.CharField(source='user.last_name', read_only=True)
    avatarUrl = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'email', 'firstName', 'lastName', 'display_name', 'bio', 'avatar', 'avatarUrl', 'settings', 'roles', 'created_at', 'updated_at']
        read_only_fields = ['id', 'email', 'firstName', 'lastName', 'avatarUrl', 'created_at', 'updated_at', 'roles']

    def get_avatarUrl(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_roles(self, obj):
        roles = ['user']
        if obj.user.is_staff:
            roles.append('staff')
        # Add group-based roles
        group_names = obj.user.groups.values_list('name', flat=True)
        for name in group_names:
            role = name.lower()  # e.g. HR_Manager -> hr_manager, Editors -> editors
            if role not in roles:
                roles.append(role)
        return roles

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept email + password for JWT login only."""
    username_field = 'email'

    def validate(self, attrs):
        email = attrs.get('email', '').strip()
        password = attrs.get('password', '')

        if not email:
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed(
                'Email is required for login',
                'email_required',
            )

        user = None
        try:
            user_obj = User.objects.get(email__iexact=email)
            user = authenticate(self.context['request'], username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
        except User.MultipleObjectsReturned:
            # Multiple users with same email — attempt exact match on username
            user = authenticate(self.context['request'], username=email, password=password)

        if user is None or not user.is_active:
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed(
                'No active account found with the given credentials',
                'no_active_account',
            )

        refresh = self.get_token(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(write_only=True)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name')

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('User with this email already exists.')
        return value

    def validate_full_name(self, value):
        name = value.strip()
        if len(name.split()) < 2:
            raise serializers.ValidationError('Please enter full name (at least first and last).')
        return name

    def create(self, validated_data):
        full_name = validated_data['full_name'].strip()
        parts = full_name.split()
        first_name = parts[0]
        last_name = ' '.join(parts[1:])

        email = validated_data['email'].strip()
        user = User.objects.create_user(
            username=email,
            password=validated_data['password'],
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False,  # Requires admin approval
        )
        return user

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff', 'is_active', 'date_joined')
        read_only_fields = ('id', 'username', 'date_joined')


class PendingUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'full_name', 'username', 'email', 'date_joined')
        read_only_fields = fields

    def get_full_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name


from media_manager.models import ContactRequest

class ContactRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactRequest
        fields = ['id', 'first_name', 'last_name', 'email', 'message', 'handled', 'created_at']
        read_only_fields = ['id', 'created_at']
