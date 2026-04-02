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
    firstName = serializers.CharField(source='user.first_name', required=False)
    lastName = serializers.CharField(source='user.last_name', required=False)
    avatarUrl = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    fio = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    department_id = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'email', 'firstName', 'lastName', 'patronymic', 'phone', 'fio', 'display_name', 'bio', 'avatar', 'avatarUrl', 'settings', 'roles', 'department', 'department_id', 'position', 'must_change_password', 'created_at', 'updated_at']
        read_only_fields = ['id', 'email', 'avatarUrl', 'created_at', 'updated_at', 'roles', 'fio', 'department', 'department_id', 'position', 'must_change_password']

    def update(self, instance, validated_data):
        user_data = {}
        if 'user' in validated_data:
            user_nested = validated_data.pop('user')
            if 'first_name' in user_nested:
                user_data['first_name'] = user_nested['first_name']
            if 'last_name' in user_nested:
                user_data['last_name'] = user_nested['last_name']
        
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
            
        return super().update(instance, validated_data)

    def get_fio(self, obj):
        parts = [
            obj.user.last_name,
            obj.user.first_name,
            obj.patronymic
        ]
        return " ".join(filter(None, parts)).strip() or obj.display_name

    def get_avatarUrl(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_department(self, obj):
        if hasattr(obj.user, 'employee') and obj.user.employee.department:
            return obj.user.employee.department.name
        return None

    def get_department_id(self, obj):
        if hasattr(obj.user, 'employee') and obj.user.employee.department:
            return obj.user.employee.department.id
        return None

    def get_position(self, obj):
        if hasattr(obj.user, 'employee') and obj.user.employee.position:
            return obj.user.employee.position.title
        return None

    def get_roles(self, obj):
        roles = ['user']
        if obj.user.is_staff:
            roles.append('staff')
        # Add group-based roles
        group_names = obj.user.groups.values_list('name', flat=True)
        for name in group_names:
            role = name.lower().replace(' ', '_').replace('-', '_')
            if role not in roles:
                roles.append(role)
        return roles

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Accept email + password for JWT login only."""
    username_field = 'email'

    def validate(self, attrs):
        login_id = attrs.get('email', '').strip()
        password = attrs.get('password', '')

        if not login_id:
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed(
                'Email or phone is required for login',
                'login_required',
            )

        from django.db.models import Q
        user = None
        try:
            # Try to find a user by their exact email, or by their profile's phone (exact match)
            user_obj = User.objects.get(Q(email__iexact=login_id) | Q(profile__phone=login_id))
            user = authenticate(self.context['request'], username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
        except User.MultipleObjectsReturned:
            # If phone or email matches multiple (edge case), try direct username authentication
            user = authenticate(self.context['request'], username=login_id, password=password)

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
