"""
HR PDF document builder — professional employment contract & hiring order.

Uses ReportLab to produce properly formatted A4 PDFs with:
  • Company header block
  • Document title & number
  • Structured body (table-like key-value rows)
  • Signature lines
  • Thin decorative borders
"""
import io
import os
from datetime import date

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable,
)

PAGE_W, PAGE_H = A4

# ── Company defaults (override via settings) ──────────────────────────────
COMPANY_NAME = getattr(settings, 'HR_COMPANY_NAME', 'ТОО «Hi-Tech Group»')
COMPANY_ADDR = getattr(settings, 'HR_COMPANY_ADDRESS',
                       'Казахстан, г. Астана')
COMPANY_BIN  = getattr(settings, 'HR_COMPANY_BIN', '')
COMPANY_PHONE = getattr(settings, 'HR_COMPANY_PHONE', '')


# ── Font registration ─────────────────────────────────────────────────────

_FONT_CACHE: dict[str, str] = {}


def _register_fonts() -> tuple[str, str]:
    """Return (regular_font_name, bold_font_name)."""
    if _FONT_CACHE:
        return _FONT_CACHE['regular'], _FONT_CACHE['bold']

    custom = getattr(settings, 'HR_PDF_FONT_PATH', '')
    candidates = [
        custom,
        os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf'),
        os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'calibri.ttf'),
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    ]
    bold_candidates = [
        custom.replace('.ttf', 'bd.ttf') if custom else '',
        os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arialbd.ttf'),
        os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'calibrib.ttf'),
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    ]

    regular = 'Helvetica'
    bold = 'Helvetica-Bold'

    for path in candidates:
        if path and os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont('HRRegular', path))
                regular = 'HRRegular'
                break
            except Exception:
                continue

    for path in bold_candidates:
        if path and os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont('HRBold', path))
                bold = 'HRBold'
                break
            except Exception:
                continue

    # Fallback: use regular for bold if no bold found
    if bold == 'Helvetica-Bold' and regular != 'Helvetica':
        bold = regular

    _FONT_CACHE['regular'] = regular
    _FONT_CACHE['bold'] = bold
    return regular, bold


# ── Style factory ──────────────────────────────────────────────────────────

def _styles(regular: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        'company': ParagraphStyle(
            'company', parent=base['Normal'],
            fontName=bold, fontSize=13, leading=16,
            alignment=TA_CENTER, spaceAfter=2 * mm,
            textColor=colors.HexColor('#1a1a2e'),
        ),
        'company_sub': ParagraphStyle(
            'company_sub', parent=base['Normal'],
            fontName=regular, fontSize=9, leading=11,
            alignment=TA_CENTER, textColor=colors.HexColor('#555555'),
        ),
        'doc_title': ParagraphStyle(
            'doc_title', parent=base['Normal'],
            fontName=bold, fontSize=16, leading=20,
            alignment=TA_CENTER, spaceAfter=4 * mm,
            textColor=colors.HexColor('#1a1a2e'),
        ),
        'doc_number': ParagraphStyle(
            'doc_number', parent=base['Normal'],
            fontName=regular, fontSize=10, leading=12,
            alignment=TA_CENTER, textColor=colors.HexColor('#666666'),
            spaceAfter=6 * mm,
        ),
        'section': ParagraphStyle(
            'section', parent=base['Normal'],
            fontName=bold, fontSize=11, leading=14,
            spaceBefore=5 * mm, spaceAfter=2 * mm,
            textColor=colors.HexColor('#1a1a2e'),
            borderPadding=(0, 0, 1, 0),
        ),
        'body': ParagraphStyle(
            'body', parent=base['Normal'],
            fontName=regular, fontSize=10, leading=14,
            alignment=TA_JUSTIFY, spaceAfter=2 * mm,
        ),
        'label': ParagraphStyle(
            'label', parent=base['Normal'],
            fontName=bold, fontSize=10, leading=13,
            textColor=colors.HexColor('#333333'),
        ),
        'value': ParagraphStyle(
            'value', parent=base['Normal'],
            fontName=regular, fontSize=10, leading=13,
        ),
        'signature': ParagraphStyle(
            'signature', parent=base['Normal'],
            fontName=regular, fontSize=10, leading=13,
            spaceBefore=8 * mm,
        ),
        'footer': ParagraphStyle(
            'footer', parent=base['Normal'],
            fontName=regular, fontSize=8, leading=10,
            alignment=TA_CENTER, textColor=colors.HexColor('#999999'),
        ),
    }


# ── Reusable building blocks ──────────────────────────────────────────────

def _company_header(st: dict) -> list:
    """Company letterhead block."""
    elements = []
    elements.append(Paragraph(COMPANY_NAME, st['company']))
    sub_parts = [p for p in [COMPANY_ADDR, COMPANY_BIN, COMPANY_PHONE] if p]
    if sub_parts:
        elements.append(Paragraph(' | '.join(sub_parts), st['company_sub']))
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(
        width='100%', thickness=1.5, color=colors.HexColor('#1a1a2e'),
        spaceAfter=6 * mm,
    ))
    return elements


def _kv_table(rows: list[tuple[str, str]], st: dict) -> Table:
    """Key-value table with alternating row shading."""
    data = []
    for label, value in rows:
        data.append([
            Paragraph(label, st['label']),
            Paragraph(value or '—', st['value']),
        ])

    col_w = [55 * mm, 115 * mm]
    tbl = Table(data, colWidths=col_w, hAlign='LEFT')

    style_cmds = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (0, -1), 4),
        ('LEFTPADDING', (1, 0), (1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e0e0e0')),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#cccccc')),
    ]
    for i in range(0, len(data), 2):
        style_cmds.append(
            ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8f9fa'))
        )
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _signature_block(st: dict, left_role: str = 'Работодатель',
                     right_role: str = 'Работник') -> Table:
    """Two-column signature area."""
    sig_line = '_' * 28
    data = [[
        Paragraph(f'<b>{left_role}</b><br/><br/>{sig_line}<br/>(подпись / ФИО)', st['signature']),
        Paragraph(f'<b>{right_role}</b><br/><br/>{sig_line}<br/>(подпись / ФИО)', st['signature']),
    ]]
    tbl = Table(data, colWidths=[85 * mm, 85 * mm], hAlign='LEFT')
    tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    return tbl


def _page_border(canvas_obj, doc):
    """Draw a subtle page border on every page."""
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(colors.HexColor('#d0d0d0'))
    canvas_obj.setLineWidth(0.75)
    m = 12 * mm
    canvas_obj.rect(m, m, PAGE_W - 2 * m, PAGE_H - 2 * m)
    canvas_obj.restoreState()


# ── Public API ─────────────────────────────────────────────────────────────

def build_contract_pdf(
    *,
    candidate_name: str,
    candidate_email: str,
    vacancy_title: str,
    department_name: str,
    hire_date: date,
    application_id: int,
    work_conditions: str = 'Основное место работы',
    work_type: str = 'Постоянная',
    probation_period: str = '3 (три) месяца',
    work_schedule: str = '5/2, с 09:00 до 18:00',
) -> bytes:
    """Generate a professional employment contract PDF."""
    regular, bold = _register_fonts()
    st = _styles(regular, bold)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f'Трудовой договор — {candidate_name}',
        author=COMPANY_NAME,
    )

    elements = []

    # Header
    elements.extend(_company_header(st))

    # Title
    elements.append(Paragraph('ТРУДОВОЙ ДОГОВОР', st['doc_title']))
    elements.append(Paragraph(
        f'№ ТД-{application_id:04d} от {hire_date.strftime("%d.%m.%Y")} г.',
        st['doc_number'],
    ))

    # Preamble
    elements.append(Paragraph(
        f'{COMPANY_NAME}, именуемое в дальнейшем «Работодатель», в лице '
        f'уполномоченного представителя, действующего на основании Устава, с '
        f'одной стороны, и <b>{candidate_name}</b>, именуемый(ая) в дальнейшем '
        f'«Работник», с другой стороны, заключили настоящий трудовой договор '
        f'о нижеследующем:',
        st['body'],
    ))

    # Section 1
    elements.append(Paragraph('1. Предмет договора', st['section']))
    elements.append(Paragraph(
        f'Работодатель принимает Работника на должность, указанную в п. 2 '
        f'настоящего договора, а Работник обязуется лично выполнять '
        f'возложенные на него трудовые обязанности, соблюдать правила '
        f'внутреннего трудового распорядка.',
        st['body'],
    ))

    # Details table
    elements.append(Paragraph('2. Основные условия', st['section']))
    elements.append(_kv_table([
        ('ФИО работника:', candidate_name),
        ('Email:', candidate_email),
        ('Вакансия / должность:', vacancy_title),
        ('Отдел:', department_name),
        ('Дата приёма:', hire_date.strftime('%d.%m.%Y')),
        ('Вид договора:', 'Бессрочный'),
        ('Испытательный срок:', probation_period),
        ('Режим работы:', work_schedule),
    ], st))

    # Section 3
    elements.append(Paragraph('3. Права и обязанности сторон', st['section']))
    elements.append(Paragraph(
        'Работник обязуется добросовестно исполнять свои трудовые '
        'обязанности, соблюдать трудовую дисциплину, бережно относиться '
        'к имуществу Работодателя, незамедлительно сообщать о возникновении '
        'ситуации, представляющей угрозу жизни и здоровью людей.',
        st['body'],
    ))
    elements.append(Paragraph(
        'Работодатель обязуется предоставить Работнику работу, '
        'обусловленную настоящим договором, обеспечить условия труда, '
        'предусмотренные трудовым законодательством, своевременно и '
        'в полном размере выплачивать заработную плату.',
        st['body'],
    ))

    # Section 4
    elements.append(Paragraph('4. Оплата труда', st['section']))
    elements.append(Paragraph(
        'Размер заработной платы, порядок и сроки выплаты определяются '
        'в соответствии со штатным расписанием и внутренними нормативными '
        'актами Работодателя.',
        st['body'],
    ))

    # Section 5
    elements.append(Paragraph('5. Заключительные положения', st['section']))
    elements.append(Paragraph(
        'Настоящий договор составлен в двух экземплярах, имеющих одинаковую '
        'юридическую силу, по одному для каждой из сторон. Все споры '
        'разрешаются путём переговоров, а при недостижении согласия — '
        'в порядке, установленном трудовым законодательством Республики '
        'Казахстан.',
        st['body'],
    ))

    # Signatures
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(
        width='100%', thickness=0.5, color=colors.HexColor('#cccccc'),
        spaceAfter=2 * mm,
    ))
    elements.append(_signature_block(st))

    doc.build(elements, onFirstPage=_page_border, onLaterPages=_page_border)
    buf.seek(0)
    return buf.read()


def build_hiring_order_pdf(
    *,
    candidate_name: str,
    candidate_email: str,
    vacancy_title: str,
    department_name: str,
    hire_date: date,
    application_id: int,
    work_conditions: str = 'Основное место работы',
    work_type: str = 'Постоянная',
    probation_period: str = '3 (три) месяца',
    work_schedule: str = '5/2, с 09:00 до 18:00',
) -> bytes:
    """Generate a professional hiring order PDF."""
    regular, bold = _register_fonts()
    st = _styles(regular, bold)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f'Приказ о приёме — {candidate_name}',
        author=COMPANY_NAME,
    )

    elements = []

    # Header
    elements.extend(_company_header(st))

    # Title
    elements.append(Paragraph('ПРИКАЗ', st['doc_title']))
    elements.append(Paragraph(
        f'№ ПР-{application_id:04d} от {hire_date.strftime("%d.%m.%Y")} г.',
        st['doc_number'],
    ))
    elements.append(Paragraph(
        'О приёме на работу',
        ParagraphStyle(
            'order_sub', parent=st['body'],
            fontName=bold, fontSize=12, alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ),
    ))

    # Body
    elements.append(Paragraph(
        f'На основании заключённого трудового договора № ТД-{application_id:04d} '
        f'от {hire_date.strftime("%d.%m.%Y")} г.,',
        st['body'],
    ))

    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(
        '<b>ПРИКАЗЫВАЮ:</b>',
        ParagraphStyle('order_cmd', parent=st['body'], fontName=bold,
                       alignment=TA_CENTER, spaceAfter=4 * mm),
    ))

    # Details table
    elements.append(_kv_table([
        ('Принять на работу:', candidate_name),
        ('Email:', candidate_email),
        ('На должность:', vacancy_title),
        ('В отдел:', department_name),
        ('Дата приёма:', hire_date.strftime('%d.%m.%Y')),
        ('Условия приёма:', work_conditions),
        ('Характер работы:', work_type),
        ('Испытательный срок:', probation_period),
    ], st))

    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(
        'Основание: трудовой договор, заявление работника.',
        st['body'],
    ))

    # Signatures
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(
        width='100%', thickness=0.5, color=colors.HexColor('#cccccc'),
        spaceAfter=2 * mm,
    ))

    sig_data = [[
        Paragraph(
            '<b>Руководитель</b><br/><br/>'
            + '_' * 28 + '<br/>(подпись / ФИО)',
            st['signature'],
        ),
        Paragraph(
            '<b>С приказом ознакомлен(а)</b><br/><br/>'
            + '_' * 28 + '<br/>(подпись / дата)',
            st['signature'],
        ),
    ]]
    sig_tbl = Table(sig_data, colWidths=[85 * mm, 85 * mm], hAlign='LEFT')
    sig_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(sig_tbl)

    doc.build(elements, onFirstPage=_page_border, onLaterPages=_page_border)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════════
#  Personnel-history documents  (one builder, content varies by event type)
# ══════════════════════════════════════════════════════════════════════════

_EVENT_TITLES: dict[str, str] = {
    'hired':     'ПРИКАЗ О ПРИЁМЕ НА РАБОТУ',
    'dismissed': 'ПРИКАЗ ОБ УВОЛЬНЕНИИ',
    'transfer':  'ПРИКАЗ О ПЕРЕВОДЕ',
    'promotion': 'ПРИКАЗ О ПОВЫШЕНИИ',
    'demotion':  'ПРИКАЗ О ПОНИЖЕНИИ В ДОЛЖНОСТИ',
    'other':     'КАДРОВЫЙ ПРИКАЗ',
}

_EVENT_PREFIX: dict[str, str] = {
    'hired':     'ПР-П',
    'dismissed': 'ПР-У',
    'transfer':  'ПР-Т',
    'promotion': 'ПР-ПВ',
    'demotion':  'ПР-ПН',
    'other':     'ПР-К',
}


def _ph_safe(value) -> str:
    if value is None:
        return '—'
    s = str(value).strip()
    return s if s else '—'


def _employee_full_name(employee) -> str:
    """Best-effort full name for an Employee instance."""
    if employee.user:
        name = employee.user.get_full_name()
        if name and name.strip():
            return name.strip()
        return employee.user.username
    return str(employee)


def _created_by_name(user) -> str:
    if user is None:
        return 'Система'
    name = user.get_full_name()
    if name and name.strip():
        return name.strip()
    return user.username or user.email or 'Система'


def build_personnel_history_pdf(history) -> bytes:
    """
    Generate a professional A4 PDF for any PersonnelHistory event.

    Accepts a PersonnelHistory model instance (imported lazily to avoid
    circular imports).
    """
    regular, bold = _register_fonts()
    st = _styles(regular, bold)

    event = history.event_type          # e.g. 'hired', 'dismissed' …
    event_display = history.get_event_type_display()
    emp_name = _employee_full_name(history.employee)
    evt_date = history.event_date

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=f'{event_display} — {emp_name}',
        author=COMPANY_NAME,
    )

    elements: list = []

    # ── Company header ────────────────────────────────────────────────
    elements.extend(_company_header(st))

    # ── Document title ────────────────────────────────────────────────
    title_text = _EVENT_TITLES.get(event, 'КАДРОВЫЙ ПРИКАЗ')
    prefix = _EVENT_PREFIX.get(event, 'ПР')
    elements.append(Paragraph(title_text, st['doc_title']))
    elements.append(Paragraph(
        f'№ {prefix}-{history.id:04d} от '
        f'{evt_date.strftime("%d.%m.%Y") if evt_date else "—"} г.',
        st['doc_number'],
    ))

    # ── Dispatcher — event-specific body ──────────────────────────────
    if event == 'hired':
        _body_hired(elements, st, history, emp_name, bold)
    elif event == 'dismissed':
        _body_dismissed(elements, st, history, emp_name, bold)
    elif event == 'transfer':
        _body_transfer(elements, st, history, emp_name, bold)
    elif event == 'promotion':
        _body_promotion(elements, st, history, emp_name, bold)
    elif event == 'demotion':
        _body_demotion(elements, st, history, emp_name, bold)
    else:
        _body_other(elements, st, history, emp_name, bold)

    # ── Common footer: created-by, signatures ─────────────────────────
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(
        f'Ответственный: {_created_by_name(history.created_by)}',
        st['body'],
    ))

    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(
        width='100%', thickness=0.5, color=colors.HexColor('#cccccc'),
        spaceAfter=2 * mm,
    ))

    sig_data = [[
        Paragraph(
            '<b>Руководитель</b><br/><br/>'
            + '_' * 28 + '<br/>(подпись / ФИО)',
            st['signature'],
        ),
        Paragraph(
            '<b>С приказом ознакомлен(а)</b><br/><br/>'
            + '_' * 28 + '<br/>(подпись / дата)',
            st['signature'],
        ),
    ]]
    sig_tbl = Table(sig_data, colWidths=[85 * mm, 85 * mm], hAlign='LEFT')
    sig_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(sig_tbl)

    doc.build(elements, onFirstPage=_page_border, onLaterPages=_page_border)
    buf.seek(0)
    return buf.read()


# ── Event-type bodies ──────────────────────────────────────────────────


def _body_hired(el, st, h, emp_name, bold):
    el.append(Paragraph(
        'На основании трудового договора и заявления работника,',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph(
        '<b>ПРИКАЗЫВАЮ:</b>',
        ParagraphStyle('ph_cmd_h', parent=st['body'], fontName=bold,
                       alignment=TA_CENTER, spaceAfter=4 * mm),
    ))
    el.append(_kv_table([
        ('Принять на работу:', emp_name),
        ('На должность:', _ph_safe(h.to_position)),
        ('В отдел:', _ph_safe(h.to_department)),
        ('Дата приёма:', h.event_date.strftime('%d.%m.%Y') if h.event_date else '—'),
        ('Номер приказа:', _ph_safe(h.order_number)),
        ('Условия приёма:', 'Основное место работы'),
        ('Испытательный срок:', '3 (три) месяца'),
    ], st))
    if h.comment:
        el.append(Spacer(1, 3 * mm))
        el.append(Paragraph('Примечание', st['section']))
        el.append(Paragraph(h.comment, st['body']))


def _body_dismissed(el, st, h, emp_name, bold):
    el.append(Paragraph(
        'В соответствии с трудовым законодательством Республики Казахстан,',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph(
        '<b>ПРИКАЗЫВАЮ:</b>',
        ParagraphStyle('ph_cmd_d', parent=st['body'], fontName=bold,
                       alignment=TA_CENTER, spaceAfter=4 * mm),
    ))
    el.append(Paragraph(
        f'Уволить <b>{emp_name}</b> по следующим основаниям:',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(_kv_table([
        ('ФИО сотрудника:', emp_name),
        ('Должность:', _ph_safe(h.from_position)),
        ('Отдел:', _ph_safe(h.from_department)),
        ('Дата увольнения:', h.event_date.strftime('%d.%m.%Y') if h.event_date else '—'),
        ('Номер приказа:', _ph_safe(h.order_number)),
        ('Основание:', _ph_safe(h.comment) if h.comment else 'По собственному желанию'),
    ], st))

    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph('Обязательства', st['section']))
    el.append(Paragraph(
        'Бухгалтерии произвести окончательный расчёт с работником '
        'в сроки, установленные трудовым законодательством. '
        'Отделу кадров оформить трудовую книжку и выдать '
        'её работнику в день увольнения.',
        st['body'],
    ))


def _body_transfer(el, st, h, emp_name, bold):
    el.append(Paragraph(
        'На основании заявления работника и производственной необходимости,',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph(
        '<b>ПРИКАЗЫВАЮ:</b>',
        ParagraphStyle('ph_cmd_t', parent=st['body'], fontName=bold,
                       alignment=TA_CENTER, spaceAfter=4 * mm),
    ))
    el.append(Paragraph(
        f'Перевести <b>{emp_name}</b> согласно нижеследующим условиям:',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(_kv_table([
        ('ФИО сотрудника:', emp_name),
        ('Из отдела:', _ph_safe(h.from_department)),
        ('В отдел:', _ph_safe(h.to_department)),
        ('Из должности:', _ph_safe(h.from_position)),
        ('В должность:', _ph_safe(h.to_position)),
        ('Дата перевода:', h.event_date.strftime('%d.%m.%Y') if h.event_date else '—'),
        ('Номер приказа:', _ph_safe(h.order_number)),
    ], st))

    if h.comment:
        el.append(Spacer(1, 3 * mm))
        el.append(Paragraph('Основание перевода', st['section']))
        el.append(Paragraph(h.comment, st['body']))

    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph(
        'Условия оплаты труда на новой должности устанавливаются '
        'в соответствии со штатным расписанием.',
        st['body'],
    ))


def _body_promotion(el, st, h, emp_name, bold):
    el.append(Paragraph(
        'За высокие достижения в трудовой деятельности и в целях '
        'оптимального использования кадрового потенциала,',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph(
        '<b>ПРИКАЗЫВАЮ:</b>',
        ParagraphStyle('ph_cmd_p', parent=st['body'], fontName=bold,
                       alignment=TA_CENTER, spaceAfter=4 * mm),
    ))
    el.append(Paragraph(
        f'Повысить <b>{emp_name}</b> в должности:',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(_kv_table([
        ('ФИО сотрудника:', emp_name),
        ('Прежний отдел:', _ph_safe(h.from_department)),
        ('Новый отдел:', _ph_safe(h.to_department)),
        ('Прежняя должность:', _ph_safe(h.from_position)),
        ('Новая должность:', _ph_safe(h.to_position)),
        ('Дата повышения:', h.event_date.strftime('%d.%m.%Y') if h.event_date else '—'),
        ('Номер приказа:', _ph_safe(h.order_number)),
    ], st))

    if h.comment:
        el.append(Spacer(1, 3 * mm))
        el.append(Paragraph('Основание', st['section']))
        el.append(Paragraph(h.comment, st['body']))

    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph(
        'Установить оплату труда согласно штатному расписанию '
        'по новой должности с даты, указанной в настоящем приказе.',
        st['body'],
    ))


def _body_demotion(el, st, h, emp_name, bold):
    el.append(Paragraph(
        'На основании результатов аттестации / служебной проверки '
        'и в соответствии с трудовым законодательством,',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph(
        '<b>ПРИКАЗЫВАЮ:</b>',
        ParagraphStyle('ph_cmd_dm', parent=st['body'], fontName=bold,
                       alignment=TA_CENTER, spaceAfter=4 * mm),
    ))
    el.append(Paragraph(
        f'Перевести <b>{emp_name}</b> на нижестоящую должность:',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(_kv_table([
        ('ФИО сотрудника:', emp_name),
        ('Прежний отдел:', _ph_safe(h.from_department)),
        ('Новый отдел:', _ph_safe(h.to_department)),
        ('Прежняя должность:', _ph_safe(h.from_position)),
        ('Новая должность:', _ph_safe(h.to_position)),
        ('Дата перевода:', h.event_date.strftime('%d.%m.%Y') if h.event_date else '—'),
        ('Номер приказа:', _ph_safe(h.order_number)),
    ], st))

    if h.comment:
        el.append(Spacer(1, 3 * mm))
        el.append(Paragraph('Основание', st['section']))
        el.append(Paragraph(h.comment, st['body']))

    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph(
        'Оплату труда установить согласно штатному расписанию '
        'по новой должности. Работник уведомлен в установленном порядке.',
        st['body'],
    ))


def _body_other(el, st, h, emp_name, bold):
    el.append(Paragraph(
        'В соответствии с внутренними нормативными актами организации,',
        st['body'],
    ))
    el.append(Spacer(1, 2 * mm))
    el.append(Paragraph(
        '<b>ПРИКАЗЫВАЮ:</b>',
        ParagraphStyle('ph_cmd_o', parent=st['body'], fontName=bold,
                       alignment=TA_CENTER, spaceAfter=4 * mm),
    ))
    rows = [
        ('ФИО сотрудника:', emp_name),
        ('Тип события:', h.get_event_type_display()),
        ('Дата:', h.event_date.strftime('%d.%m.%Y') if h.event_date else '—'),
        ('Номер приказа:', _ph_safe(h.order_number)),
    ]
    if h.from_department:
        rows.append(('Из отдела:', _ph_safe(h.from_department)))
    if h.to_department:
        rows.append(('В отдел:', _ph_safe(h.to_department)))
    if h.from_position:
        rows.append(('Из должности:', _ph_safe(h.from_position)))
    if h.to_position:
        rows.append(('В должность:', _ph_safe(h.to_position)))

    el.append(_kv_table(rows, st))

    if h.comment:
        el.append(Spacer(1, 3 * mm))
        el.append(Paragraph('Содержание', st['section']))
        el.append(Paragraph(h.comment, st['body']))
