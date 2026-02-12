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
        if obj.user.is_staff:
            return ['staff', 'user']
        return ['user']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff', 'is_active', 'date_joined')
        read_only_fields = ('id', 'username', 'date_joined')


from media_manager.models import ContactRequest

class ContactRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactRequest
        fields = ['id', 'first_name', 'last_name', 'email', 'message', 'handled', 'created_at']
        read_only_fields = ['id', 'created_at']
