from django.db import transaction
from django.utils import timezone
from .models import EmailMessage, EmailRecipientStatus, EmailAttachment
from .mta_connector import OAuthEmailConnector
from .dlp_scanner import OutboundDLPScanner

class EmailService:
    @staticmethod
    def send_email(sender, subject, body, recipients, attachments=None, external_recipients=None):
        """
        Creates an email message, its recipient statuses, and attachments inside an atomic transaction.
        If any part fails, the entire email creation is rolled back.
        """
        attachments = attachments or []
        external_recipients = external_recipients or []
        
        # Сканируем DLP перед любой транзакцией, если есть внешние адресаты
        if external_recipients:
            OutboundDLPScanner.check_and_raise(subject, body)
        
        with transaction.atomic():
            message = EmailMessage.objects.create(
                sender=sender,
                subject=subject,
                body=body,
                is_draft=False,
                sent_at=timezone.now(),
                external_recipients=external_recipients
            )

            # Create recipient statuses
            statuses = []
            for user in recipients:
                statuses.append(EmailRecipientStatus(
                    message=message,
                    user=user,
                    recipient_type=EmailRecipientStatus.RecipientType.TO,
                    folder=EmailRecipientStatus.Folder.INBOX
                ))
            
            EmailRecipientStatus.objects.bulk_create(statuses)

            for file_obj in attachments:
                EmailAttachment.objects.create(
                    message=message,
                    file=file_obj
                )

        # Отправка через OAuth API (Gmail API / Microsoft Graph)
        if external_recipients:
            connector = OAuthEmailConnector()
            success = connector.send_external_email(
                subject=subject,
                body=body,
                external_recipients=external_recipients,
                sender_user=sender,
            )
            if not success:
                # We raise an exception after the transaction is committed
                # so the record stays in DB as "sent" (or we could mark it as failed).
                # For now, raising ensures the user sees an error on the frontend.
                raise RuntimeError("Не удалось отправить письмо через внешний сервис. Проверьте подключение почты.")

        return message
