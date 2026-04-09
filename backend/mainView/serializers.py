"""
mainView/serializers.py
Сериализаторы основного модуля: элементы контента, профили пользователей,
аутентификация (JWT), регистрация и административные операции.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from media_manager.models import ContactRequest, News
from .models import Item, Profile


# ---------------------------------------------------------------------------
# Контент
# ---------------------------------------------------------------------------

class ItemSerializer(serializers.ModelSerializer):
    """Сериализатор элемента контента (Item).

    Поля owner и created_at заполняются автоматически и не доступны
    для изменения через API.
    """

    class Meta:
        model = Item
        fields = ['id', 'title', 'description', 'owner', 'created_at']
        read_only_fields = ['id', 'owner', 'created_at']


class NewsSerializer(serializers.ModelSerializer):
    """Сериализатор новостей.

    При отдаче данных преобразует путь к изображению в относительный URL,
    чтобы корректно работать через Vite-прокси с любого хоста.
    """

    class Meta:
        model = News
        fields = [
            'id', 'title', 'slug', 'summary', 'content',
            'image', 'category', 'published', 'published_at', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Возвращаем относительный URL изображения (например, /media/news_images/photo.jpg)
        if instance.image:
            data['image'] = instance.image.url
        return data


# ---------------------------------------------------------------------------
# Профиль пользователя
# ---------------------------------------------------------------------------

def _get_employee_or_none(user):
    """Возвращает связанный объект Employee или None.

    Используется в сериализаторе профиля, чтобы избежать дублирования
    проверки hasattr(user, 'employee') в нескольких get_*-методах.
    """
    employee = getattr(user, 'employee', None)
    return employee


class ProfileSerializer(serializers.ModelSerializer):
    """Расширенный сериализатор профиля.

    Объединяет данные из моделей Profile и User (имя, фамилия, e-mail),
    а также подтягивает информацию из HR-модуля (отдел, должность).
    """

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
        fields = [
            'id', 'email', 'firstName', 'lastName', 'patronymic', 'phone',
            'fio', 'display_name', 'bio', 'avatar', 'avatarUrl', 'settings',
            'roles', 'department', 'department_id', 'position',
            'must_change_password', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'email', 'avatarUrl', 'created_at', 'updated_at',
            'roles', 'fio', 'department', 'department_id', 'position',
            'must_change_password',
        ]

    def update(self, instance, validated_data):
        """Обновляет профиль и вложенные поля User (имя, фамилия)."""
        user_nested = validated_data.pop('user', {})
        if user_nested:
            user = instance.user
            for attr, value in user_nested.items():
                setattr(user, attr, value)
            user.save(update_fields=list(user_nested.keys()))

        return super().update(instance, validated_data)

    def get_fio(self, obj):
        """Формирует строку «Фамилия Имя Отчество» или display_name как запасной вариант."""
        parts = [obj.user.last_name, obj.user.first_name, obj.patronymic]
        return ' '.join(filter(None, parts)).strip() or obj.display_name

    def get_avatarUrl(self, obj):
        """Возвращает относительный URL аватара или None."""
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_department(self, obj):
        """Название отдела сотрудника из HR-модуля."""
        employee = _get_employee_or_none(obj.user)
        if employee and employee.department:
            return employee.department.name
        return None

    def get_department_id(self, obj):
        """ID отдела сотрудника из HR-модуля."""
        employee = _get_employee_or_none(obj.user)
        if employee and employee.department:
            return employee.department.id
        return None

    def get_position(self, obj):
        """Название должности сотрудника из HR-модуля."""
        employee = _get_employee_or_none(obj.user)
        if employee and employee.position:
            return employee.position.title
        return None

    def get_roles(self, obj):
        """Собирает список ролей: базовая 'user', 'staff' и роли из групп Django."""
        roles = ['user']
        if obj.user.is_staff:
            roles.append('staff')
        # Роли на основе групп пользователя
        group_names = obj.user.groups.values_list('name', flat=True)
        for name in group_names:
            role = name.lower().replace(' ', '_').replace('-', '_')
            if role not in roles:
                roles.append(role)
        return roles


# ---------------------------------------------------------------------------
# Аутентификация и регистрация
# ---------------------------------------------------------------------------

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT-аутентификация по e-mail или телефону (вместо стандартного username).

    Алгоритм поиска пользователя:
    1. Ищем по точному совпадению email (регистронезависимо) или по телефону в профиле.
    2. Если найдено несколько совпадений — пробуем аутентификацию по username.
    3. Неактивные аккаунты отклоняются.
    """

    username_field = 'email'

    def validate(self, attrs):
        login_id = attrs.get('email', '').strip()
        password = attrs.get('password', '')

        if not login_id:
            raise exceptions.AuthenticationFailed(
                'Для входа необходим e-mail или телефон.',
                'login_required',
            )

        user = None
        try:
            user_obj = User.objects.get(
                Q(email__iexact=login_id) | Q(profile__phone=login_id)
            )
            user = authenticate(
                self.context['request'],
                username=user_obj.username,
                password=password,
            )
        except User.DoesNotExist:
            user = None
        except User.MultipleObjectsReturned:
            # Если по телефону/email нашлось несколько — пробуем по username
            user = authenticate(
                self.context['request'],
                username=login_id,
                password=password,
            )

        if user is None or not user.is_active:
            raise exceptions.AuthenticationFailed(
                'Активный аккаунт с указанными данными не найден.',
                'no_active_account',
            )

        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор регистрации нового пользователя.

    Принимает e-mail, пароль и полное имя (минимум имя + фамилия).
    Новый аккаунт создаётся неактивным — требуется подтверждение администратора.
    """

    password = serializers.CharField(write_only=True)
    full_name = serializers.CharField(write_only=True)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ('email', 'password', 'full_name')

    def validate_email(self, value):
        """Проверяет уникальность e-mail (регистронезависимо)."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Пользователь с таким e-mail уже существует.')
        return value

    def validate_full_name(self, value):
        """Проверяет, что указано минимум два слова (имя и фамилия)."""
        name = value.strip()
        if len(name.split()) < 2:
            raise serializers.ValidationError('Укажите полное имя (минимум имя и фамилия).')
        return name

    def create(self, validated_data):
        """Создаёт пользователя с is_active=False (ожидает одобрения администратора)."""
        full_name = validated_data['full_name'].strip()
        parts = full_name.split()
        first_name = parts[0]
        last_name = ' '.join(parts[1:])

        email = validated_data['email'].strip()
        return User.objects.create_user(
            username=email,
            password=validated_data['password'],
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )


# ---------------------------------------------------------------------------
# Административные сериализаторы
# ---------------------------------------------------------------------------

class AdminUserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя для административной панели."""

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff', 'is_active', 'date_joined')
        read_only_fields = ('id', 'username', 'date_joined')


class PendingUserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователей, ожидающих одобрения (is_active=False)."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'full_name', 'username', 'email', 'date_joined')
        read_only_fields = fields

    def get_full_name(self, obj):
        """Возвращает имя и фамилию через пробел."""
        return f'{obj.first_name} {obj.last_name}'.strip()


class ContactRequestSerializer(serializers.ModelSerializer):
    """Сериализатор заявки обратной связи (форма «Связаться с нами»)."""

    class Meta:
        model = ContactRequest
        fields = ['id', 'first_name', 'last_name', 'email', 'message', 'handled', 'created_at']
        read_only_fields = ['id', 'created_at']
