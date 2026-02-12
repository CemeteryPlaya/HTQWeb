from rest_framework import serializers

from .models import News, ContactRequest


class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = [
            'id', 'title', 'slug', 'summary', 'content',
            'image', 'category', 'published', 'published_at', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            data['image'] = instance.image.url
        return data


class ContactRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactRequest
        fields = [
            'id', 'first_name', 'last_name', 'email', 'message',
            'handled', 'reply_message', 'replied_at', 'replied_by', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'reply_message', 'replied_at', 'replied_by']
