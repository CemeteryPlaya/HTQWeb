"""Serializers for department folder / file API."""
from rest_framework import serializers

from .department_files import DepartmentFolder, DepartmentFile


class DepartmentFileSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DepartmentFile
        fields = [
            'id', 'folder', 'name', 'file', 'file_url', 'file_size',
            'uploaded_by', 'uploaded_by_name', 'description', 'created_at',
        ]
        read_only_fields = [
            'id', 'file_url', 'file_size', 'uploaded_by',
            'uploaded_by_name', 'created_at',
        ]

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            full = obj.uploaded_by.get_full_name()
            return full if full else obj.uploaded_by.username
        return None

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class DepartmentFolderSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source='department.name', read_only=True,
    )
    files_count = serializers.SerializerMethodField()

    class Meta:
        model = DepartmentFolder
        fields = [
            'id', 'department', 'department_name',
            'files_count', 'created_at',
        ]
        read_only_fields = ['id', 'department_name', 'files_count', 'created_at']

    def get_files_count(self, obj):
        return obj.files.count()
