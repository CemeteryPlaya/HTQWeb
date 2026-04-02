import os
import django
import sys

# Настройка окружения Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HTQWeb.settings')
django.setup()

from django.contrib.auth import get_user_model
from internal_email.services import EmailService
from rest_framework.exceptions import ValidationError

User = get_user_model()

def run_tests():
    print("=== Запуск верификации почтовой системы ===\n")
    
    # 1. Подготовка тестового пользователя
    sender, _ = User.objects.get_or_create(username='test_sender', email='sender@company.com')
    recipient, _ = User.objects.get_or_create(username='test_recipient', email='recipient@company.com')
    
    # --- ТЕСТ 1: Блокировка DLP (Нарушение) ---
    print("Тест 1: Проверка DLP (Конфиденциальные данные)...")
    try:
        EmailService.send_email(
            sender=sender,
            subject="Секретный проект",
            body="Вот номер моей карты: 4276 1234 5678 9012. Строго конфиденциально!",
            recipients=[],
            external_recipients=["client@gmail.com"]
        )
        print("❌ ОШИБКА: Письмо с данными карты не было заблокировано!")
    except ValidationError as e:
        print(f"✅ УСПЕХ: DLP заблокировал письмо. Причина: {e.detail['error']}")

    # --- ТЕСТ 2: Гибридная отправка (Успех) ---
    print("\nТест 2: Гибридная отправка (Внутренний + Внешний)...")
    try:
        msg = EmailService.send_email(
            sender=sender,
            subject="Рабочая встреча",
            body="Приветствую, обсудим проект завтра в 10:00.",
            recipients=[recipient],
            external_recipients=["partner@external.com"]
        )
        print(f"✅ УСПЕХ: Письмо отправлено. ID: {msg.id}")
        print(f"   - Внутренних статусов в БД: {msg.recipient_statuses.count()}")
        print(f"   - Внешних адресатов в поле модели: {msg.external_recipients}")
    except Exception as e:
        print(f"❌ ОШИБКА при отправке: {e}")

    # --- ТЕСТ 3: Изоляция домена (Проверка логов/MTA) ---
    print("\nТест 3: Транзакционное письмо (Is Transactional)...")
    # Мы проверим это косвенно, в реальной среде нужно смотреть логи mta_connector.py
    print("   (Проверьте консоль на наличие лога 'EXTERNAL_EMAIL_API_KEY не установлен')")

    print("\n=== Верификация завершена ===")

if __name__ == "__main__":
    run_tests()
