"""
Department-based file storage models.

Each Department gets one virtual folder. Only employees of that department
(+ superuser/staff) may access the folder and its files.
"""
from django.conf import settings
from django.db import models


class DepartmentFolder(models.Model):
    """Virtual folder tied 1-to-1 to a Department."""

    department = models.OneToOneField(
        'hr.Department',
        on_delete=models.CASCADE,
        related_name='folder',
        verbose_name='Отдел',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Папка отдела'
        verbose_name_plural = 'Папки отделов'
        ordering = ['department__name']

    def __str__(self):
        return f'📁 {self.department.name}'


def _department_file_path(instance, filename):
    """Upload to  department_files/<dept_name>/<filename>."""
    dept_name = instance.folder.department.name.replace(' ', '_')
    return f'department_files/{dept_name}/{filename}'


class DepartmentFile(models.Model):
    """A file stored inside a department folder."""

    folder = models.ForeignKey(
        DepartmentFolder,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='Папка',
    )
    name = models.CharField('Имя файла', max_length=500)
    file = models.FileField('Файл', upload_to=_department_file_path)
    file_size = models.PositiveBigIntegerField('Размер (байт)', default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_department_files',
        verbose_name='Загрузил',
    )
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Файл отдела'
        verbose_name_plural = 'Файлы отделов'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
