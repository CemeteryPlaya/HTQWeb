import re
import logging
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

class OutboundDLPScanner:
    """
    Модуль Data Loss Prevention (DLP).
    Предотвращает утечку конфиденциальных данных во внешнюю (публичную) сеть.
    Срабатывает перед отправкой во внешний API Gateway.
    """
    
    PATTERNS = {
        'credit_card': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|[25][1-7][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})\b',
        'confidential_marker': r'(строго\s+конфиденциально|коммерческая\s+тайна|internal\s+use\s+only|не\s+для\s+пересылки)',
        'passport_ru': r'\b\d{4}\s\d{6}\b'
    }

    @classmethod
    def scan(cls, content):
        """
        Сканирует содержимое на наличие паттернов.
        """
        if not content:
            return False, []
            
        violations = []
        # Удаляем HTML теги для сканирования чистого текста
        clean_text = re.sub(r'<[^>]+>', ' ', content.lower())
        
        for name, pattern in cls.PATTERNS.items():
            if re.search(pattern, clean_text):
                violations.append(name)
                
        if violations:
            logger.warning(f"SECURITY INCIDENT (DLP): Попытка отправки запрещенных данных во внешнюю сеть. Триггеры: {violations}")
            return True, violations
            
        return False, []

    @classmethod
    def check_and_raise(cls, subject, body):
        """
        Удобный метод для валидации. Вызывает исключение если DLP сработал.
        """
        has_violations, triggers = cls.scan(f"{subject} {body}")
        if has_violations:
            trigger_names = ", ".join(triggers)
            raise ValidationError({
                'error': f'Политика безопасности DLP заблокировала отправку. Обнаружены запрещенные данные ({trigger_names}).'
            })
