from sqladmin import ModelView
from app.models.domain import ChatAttachment

class ChatAttachmentAdmin(ModelView, model=ChatAttachment):
    column_list = [ChatAttachment.id, ChatAttachment.message_id, ChatAttachment.filename, ChatAttachment.size]
    name = "Attachment"
