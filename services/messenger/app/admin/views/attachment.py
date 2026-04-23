from sqladmin import ModelView
from app.models.domain import MessageAttachment

class MessageAttachmentAdmin(ModelView, model=MessageAttachment):
    column_list = [MessageAttachment.id, MessageAttachment.message_id, MessageAttachment.name, MessageAttachment.size]
    name = "Attachment"
