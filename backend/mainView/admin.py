from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django import forms
from .models import Item, Profile


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
	list_display = ('title', 'owner', 'created_at')


class CustomUserChangeForm(BaseUserAdmin.form):
    """Extended User change form with Profile fields injected."""
    patronymic = forms.CharField(label='Отчество', max_length=100, required=False)
    phone = forms.CharField(label='Телефон', max_length=30, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields['patronymic'].initial = profile.patronymic or ''
                self.fields['phone'].initial = profile.phone or ''
            except Profile.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and user.pk:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.patronymic = self.cleaned_data.get('patronymic', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save(update_fields=['patronymic', 'phone'])
        return user


class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

    # Override fieldsets to inject patronymic & phone into "Personal info"
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'patronymic', 'phone', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

# Re-register User with our custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
