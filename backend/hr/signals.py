import io
import os
from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Document, PersonnelHistory
from .pdf import build_personnel_history_pdf


@receiver(post_save, sender=PersonnelHistory)
def create_personnel_history_pdf(sender, instance: PersonnelHistory, created: bool, **kwargs):
    if not created:
        return

    if not getattr(settings, 'HR_AUTO_PDF', True):
        return

    event_display = instance.get_event_type_display()
    title = f'{event_display} #{instance.id}'
    filename = f'personnel_history_{instance.id}.pdf'

    pdf_bytes = build_personnel_history_pdf(instance)
    document = Document(
        employee=instance.employee,
        title=title,
        doc_type=Document.DocType.ORDER,
        description=f'Автоматический документ по событию: {event_display}',
        uploaded_by=instance.created_by,
    )
    document.file.save(filename, ContentFile(pdf_bytes), save=True)


# ---------------------------------------------------------------------------
#  Audit: log any changes to financial / sensitive Employee fields
# ---------------------------------------------------------------------------

FINANCIAL_FIELDS = ('salary', 'bonus', 'passport_data', 'bank_account')


@receiver(post_save, sender='hr.Employee')
def audit_financial_fields(sender, instance, created, **kwargs):
    """
    При сохранении Employee записывает в HRActionLog изменение
    любого финансового/конфиденциального поля.
    """
    if created:
        # Новый объект — нет «предыдущих» значений для сравнения
        return

    # Django не предоставляет out-of-the-box diff.
    # Используем update_fields, если задан; иначе пропускаем
    # (полные save() из форм admin — update_fields = None).
    update_fields = kwargs.get('update_fields')
    if update_fields is not None:
        changed_financial = set(update_fields) & set(FINANCIAL_FIELDS)
    else:
        # Если update_fields не задан — проверим через _loaded_values
        # (трекер не встроен, поэтому логируем факт сохранения при наличии полей).
        changed_financial = set()
        for field in FINANCIAL_FIELDS:
            if getattr(instance, field, None):
                changed_financial.add(field)

    if not changed_financial:
        return

    from .models import HRActionLog

    details = ', '.join(sorted(changed_financial))
    HRActionLog.objects.create(
        user=None,  # Пользователь не доступен из сигнала; обогащается через ViewSet-логирование
        employee=instance,
        department=instance.department,
        position=instance.position,
        action=HRActionLog.ActionType.UPDATE,
        target_type=HRActionLog.TargetType.EMPLOYEE,
        target_id=instance.pk,
        target_repr=str(instance),
        details=f'Изменены финансовые поля: {details}',
        module=HRActionLog.Module.HR,
    )
