"""Google Sheets ma'lumotlarini (sheet_data.json) mavjud modellarga moslab yuklaydi.

Mapping:
  • Guruh varaqlari (K/S, SMM, G/D, ADV ...) → Teacher + Course + Group + Student + Payment
  • Leadlar (Computers, Umumiy ro'yxat, Javob bermaganlar) → Lead
  • Bitiruvchilar 01/02 → Student(is_graduate=True)
  • TG reklamalar → AdChannel

Barcha import qilingan yozuvlarda source="sheet" belgisi bo'ladi — shu tufayli
mavjud real ma'lumotlarga tegmaydi va qayta ishga tushirilsa dublikat bo'lmaydi.

Ishlatish:
    python manage.py load_sheet_data
"""

import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from register_withvue.models import (
    Teacher, Course, Group, Student, Payment, Lead, AdChannel,
)

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "sheet_data.json"
SOURCE = "sheet"

# Varaq nomidan o'qituvchi nomi
TEACHER_NAMES = {
    "husabdulloh": "HusAbdulloh",
    "ibrosam": "Ibrohim / Samandar",
    "valijon": "Valijon",
    "yoqutxon": "Yoqutxon",
    "xasan": "Xasan",
    "aziz": "Aziz",
    "abdulaziz-bahtiyor": "Abdulaziz / Bahtiyor",
    "xusmer": "Xusmer",
}

# Import versiyasi — mapping o'zgarsa oshiriladi, server qayta import qiladi
DATA_VERSION = "4"

# Guruh kodidan kurs: (regex, to'liq nom, qisqa nom)
# Tartib muhim: FR "DASTURLASH FR 18" kabi holatlarda DASTURLASHdan ustun
COURSE_DEFS = [
    (r"\bK[\.\/\\]?S\b|\bK[\.\/\\]?S\d|KS\s*#", "Kompyuter savodxonligi", "K/S"),
    (r"\bFR\b|\bFR\d", "Frontend", "FR"),
    (r"\bSMM\b", "SMM", "SMM"),
    (r"\bADV\b", "Advanced", "ADV"),
    (r"\bG[\.\/\\]?D\b|\bG[\.\/\\]?D\d", "Grafik dizayn", "G/D"),
    (r"DASTURLASH", "Dasturlash", "Dasturlash"),
    (r"BOSHLANG", "Boshlang'ich savodxonlik", "Savodxonlik"),
    (r"INGLIZ", "Ingliz tili", "Ingliz tili"),
]

# Guruh raqami: K/S 81, K/S #85, ks99, KS# 100, FR20, DASTURLASH22, G/D#12 ...
NUM_RE = re.compile(
    r"(?:K[\.\/\\]?S|KS|FR|G[\.\/\\]?D|ADV|SMM|DASTURLASH)\s*#?\s*\/?\s*(\d{1,3})\b",
    re.I,
)

MONTH_TOKENS = {
    "sen": 9, "sent": 9, "sentabr": 9, "sentyabr": 9,
    "okt": 10, "oktabr": 10, "oktyabr": 10,
    "noy": 11, "noyabr": 11,
    "dek": 12, "dekabr": 12,
    "yan": 1, "yanvar": 1,
    "fev": 2, "fevral": 2,
    "mar": 3, "mart": 3,
    "apr": 4, "aprel": 4,
    "may": 5,
    "iyun": 6,
    "iyul": 7,
    "avg": 8, "avgust": 8,
}

# To'lov ustunlari uchun standart oylar ketma-ketligi (o'quv yili 2025-09 → 2026-08)
DEFAULT_MONTHS = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]


def month_str(m):
    """Oy raqamidan 'YYYY-MM'. 9-12 → 2025, 1-8 → 2026 (o'quv yili)."""
    year = 2025 if m >= 9 else 2026
    return f"{year}-{m:02d}"


def fmt9(d):
    return f"{d[:2]} {d[2:5]} {d[5:7]} {d[7:]}"


def extract_phone(cell):
    """Katakdan 9 xonali telefonni ajratib, chiroyli formatga keltiradi."""
    if not cell:
        return None
    d = re.sub(r"\D", "", str(cell))
    if len(d) == 9:
        return fmt9(d)
    if len(d) == 12 and d.startswith("998"):
        return fmt9(d[3:])
    return None


def is_amount(cell):
    """Katak faqat to'lov summasi (100-2000) bo'lsa raqamni qaytaradi."""
    s = str(cell).strip()
    if re.fullmatch(r"\d{3,4}", s):
        v = int(s)
        if 100 <= v <= 2000:
            return v
    return None


def parse_course(header):
    """Sarlavhadan kursni aniqlaydi → (to'liq nom, qisqa nom) yoki None."""
    up = str(header).upper()
    for pat, name, short in COURSE_DEFS:
        if re.search(pat, up):
            return name, short
    return None


def parse_schedule(header):
    """Dars kunlarini aniqlaydi → 'odd' / 'even' / None.

    Formatlar: D/CH/J, D.CH.J., D;CH;J;, D,ch,j, D /CH/JU  → odd
               S/P/SH, S.P.SH., SE/PAY/SHAN, SE/PE/SH(A), S/SH → even
               D/J → odd
    """
    up = str(header).upper()
    letters = re.sub(r"[^A-Z]", "", up)
    for token in ("SEPAYSHAN", "SEPESHA", "SEPESH", "SPSH"):
        if token in letters:
            return "even"
    if "DCHJ" in letters:
        return "odd"
    if re.search(r"\bS\s*[\/,\.]\s*SH\b", up):
        return "even"
    if re.search(r"\bD\s*[\/,\.]\s*J\b", up):
        return "odd"
    return None


def looks_like_header(cell):
    """Guruh sarlavhasi qatorimi (K/S #85 S/P/SH 9:30 ..., SMM #16 D/J ...)."""
    s = str(cell)
    if re.search(r"#\s*\d", s):
        return True
    course = parse_course(s)
    if course is not None:
        # "ingliz mental yoshda" kabi izohlar guruh bo'lib ketmasligi uchun:
        # zaif kalit so'zli kurslarda kun yoki soat ham bo'lishi shart
        if course[0] in ("Ingliz tili", "Boshlang'ich savodxonlik"):
            return (
                parse_schedule(s) is not None
                or re.search(r"\d{1,2}[:;]\d{2}", s) is not None
            )
        return True
    if parse_schedule(s) is not None:
        return True
    return False


def parse_time(header):
    """Sarlavhadan dars vaqtini ajratadi.

    Formatlar: '9:00', '16;00', '10:30', '8;30' hamda '1700' (K/S 95 1700).
    '14.01.2026' kabi sanalar vaqt sifatida olinmaydi.
    """
    for m in re.finditer(r"(\d{1,2})[:;](\d{2})", str(header)):
        h, mi = int(m.group(1)), int(m.group(2))
        if 7 <= h <= 20 and mi <= 59:
            return timezone.datetime.min.time().replace(hour=h, minute=mi)
    # 4 xonali '1700' ko'rinishi — yillar (2025/2026) minut tekshiruvidan o'tmaydi
    for m in re.finditer(r"\b(\d{4})\b", str(header)):
        h, mi = int(m.group(1)[:2]), int(m.group(1)[2:])
        if 7 <= h <= 20 and mi in (0, 15, 30, 45):
            return timezone.datetime.min.time().replace(hour=h, minute=mi)
    return timezone.datetime.min.time().replace(hour=9, minute=0)


def parse_group_number(header):
    m = NUM_RE.search(str(header))
    return m.group(1) if m else None


def split_name(full):
    parts = str(full).strip().split()
    if len(parts) >= 2:
        return parts[0], " ".join(parts[1:])
    return full.strip(), ""


# Ism emasligini bildiruvchi kalit so'zlar (jadval/izoh qoldiqlari)
_NON_NAME_KW = re.compile(
    r"dasturlash|guru[hx]|komp[iy]|kampiy|s\s*,\s*p\s*,\s*s|d\s*,\s*ch\s*,\s*j|"
    r"febral|yuksalish",
    re.I,
)


def valid_person_name(s):
    """Katak haqiqiy ism-familiyaga o'xshaydimi (jadval/izoh qoldig'i emas)."""
    s = str(s).strip()
    if len(s) < 3:
        return False
    if re.match(r"^\d", s):  # raqamdan boshlanadi
        return False
    if re.search(r"\d{1,2}:\d{2}", s):  # vaqt bor
        return False
    if len(re.sub(r"[^A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʻʼ'`]", "", s)) < 3:
        return False  # 3 tadan kam harf
    if _NON_NAME_KW.search(s):
        return False
    return True


class Command(BaseCommand):
    help = "sheet_data.json → Teacher/Course/Group/Student/Payment/Lead/AdChannel"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DATA_FILE))

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Fayl topilmadi: {path}")

        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        tabs = payload.get("tabs", [])
        if not tabs:
            raise CommandError("JSON faylda 'tabs' bo'sh")

        self._syn = 0
        self._course_amounts = {}  # course_id → [to'lov summalari]

        stats = {"teachers": 0, "courses": 0, "groups": 0,
                 "students": 0, "payments": 0, "leads": 0, "ads": 0, "graduates": 0}

        with transaction.atomic():
            self._clear_previous()

            # DB'da band bo'lgan telefonlar — MUHIM: eski import
            # o'chirilgandan KEYIN yig'iladi, aks holda barcha telefonlar
            # "band" bo'lib sintetik raqam berilib ketadi
            self.used_student_phones = set(
                Student.objects.values_list("phone", flat=True)
            )
            self.used_teacher_phones = set(
                Teacher.objects.values_list("phone", flat=True)
            )

            for tab in tabs:
                cat = tab.get("category")
                if cat == "groups":
                    self._import_group(tab, stats)
                elif cat == "leads":
                    self._import_leads(tab, stats)
                elif cat == "alumni":
                    self._import_alumni(tab, stats)
                elif cat == "ads":
                    self._import_ads(tab, stats)

            # Kurs oylik narxi — eng ko'p uchraydigan to'lov summasi
            from collections import Counter

            for course_id, amounts in self._course_amounts.items():
                if amounts:
                    fee = Counter(amounts).most_common(1)[0][0]
                    Course.objects.filter(id=course_id).update(monthly_fee=fee)

            # Import versiyasini saqlaymiz — server startida solishtiriladi
            from register_withvue.models import SheetImportMeta

            SheetImportMeta.objects.update_or_create(
                pk=1, defaults={"version": DATA_VERSION}
            )

        self.stdout.write(self.style.SUCCESS("Import yakunlandi:"))
        for k, v in stats.items():
            self.stdout.write(f"  {k:12}: {v}")

    # ── Eski import ma'lumotlarini o'chirish (idempotent) ──
    def _clear_previous(self):
        Payment.objects.filter(source=SOURCE).delete()
        Student.objects.filter(source=SOURCE).delete()
        Group.objects.filter(source=SOURCE).delete()
        Course.objects.filter(source=SOURCE).delete()
        Teacher.objects.filter(source=SOURCE).delete()
        Lead.objects.filter(source=SOURCE).delete()
        AdChannel.objects.filter(source=SOURCE).delete()

    # ── Unikal telefon generatori ──
    def _uniq_student_phone(self, primary):
        if primary and primary not in self.used_student_phones:
            self.used_student_phones.add(primary)
            return primary
        while True:
            self._syn += 1
            cand = f"—{self._syn:04d}"
            if cand not in self.used_student_phones:
                self.used_student_phones.add(cand)
                return cand

    def _uniq_teacher_phone(self):
        while True:
            self._syn += 1
            cand = f"t{self._syn:04d}"
            if cand not in self.used_teacher_phones:
                self.used_teacher_phones.add(cand)
                return cand

    # ── GURUH varag'i ──
    # Har bir varaqda bir nechta guruh bo'ladi. Har bir sarlavha qatori
    # ("K/S #85 S/P/SH 9:30 12.05.2026") yangi guruhni boshlaydi — kurs,
    # dars kunlari va soati aynan shu sarlavhadan olinadi.
    def _import_group(self, tab, stats):
        rows = tab["rows"]
        slug = tab["slug"]

        teacher_name = TEACHER_NAMES.get(slug, tab["title"])
        teacher = Teacher.objects.create(
            name=teacher_name, phone=self._uniq_teacher_phone(), source=SOURCE
        )
        stats["teachers"] += 1

        current = None  # {"group","schedule","month_cols"}

        def month_hits_of(r):
            return {
                i: MONTH_TOKENS[str(c).strip().lower()]
                for i, c in enumerate(r)
                if str(c).strip().lower() in MONTH_TOKENS
            }

        def start_group(header_text):
            course_info = parse_course(header_text)
            if course_info:
                course_name, short = course_info
            else:
                course_name, short = "Umumiy kurs", "Guruh"

            course, created = Course.objects.get_or_create(
                name=course_name, source=SOURCE, defaults={"monthly_fee": 0}
            )
            if created:
                stats["courses"] += 1

            num = parse_group_number(header_text)
            gname = f"{short} #{num}" if num else f"{short} — {teacher_name}"
            schedule = parse_schedule(header_text) or "odd"
            lesson_time = parse_time(header_text)

            # Ayni o'qituvchida bir xil nomli guruh takror kelsa — qayta ishlatamiz
            group, g_created = Group.objects.get_or_create(
                name=gname[:100],
                teacher=teacher,
                source=SOURCE,
                defaults={
                    "lesson_time": lesson_time,
                    "schedule": schedule,
                    "course": course,
                },
            )
            if g_created:
                stats["groups"] += 1
            return {"group": group, "schedule": schedule, "month_cols": {}}

        for r in rows:
            first = str(r[0]).strip() if r else ""
            hits = month_hits_of(r)

            if first and looks_like_header(first):
                current = start_group(first)
                if len(hits) >= 2:
                    current["month_cols"] = hits
                continue

            # alohida oy sarlavhasi qatori (sent/okt/noy...)
            if len(hits) >= 2:
                if current:
                    current["month_cols"] = hits
                continue

            if not (valid_person_name(first) and not extract_phone(first)):
                continue

            # sarlavhadan oldingi qatorlar: faqat telefoni bo'lsa olamiz
            row_has_phone = any(extract_phone(str(c)) for c in r[1:])
            if current is None:
                if not row_has_phone:
                    continue
                current = start_group("")

            self._add_group_student(r, teacher, current, stats)

    def _add_group_student(self, r, teacher, current, stats):
        group = current["group"]
        schedule = current["schedule"]
        month_cols = current["month_cols"]

        name_raw = str(r[0]).strip()
        phones, amounts, notes = [], [], []
        for ci, c in enumerate(r):
            if ci == 0:
                continue
            c = str(c).strip()
            if not c:
                continue
            ph = extract_phone(c)
            if ph and len(phones) < 2:
                phones.append(ph)
                continue
            amt = is_amount(c)
            if amt is not None:
                amounts.append((ci, amt))
                continue
            notes.append(c)

        name, surname = split_name(name_raw)
        note_text = " · ".join(notes)
        is_grad = (
            "BITIRUVCHI" in name_raw.upper() or "BITIRUVCHI" in note_text.upper()
        )

        student = Student.objects.create(
            name=name[:100],
            surname=surname[:100],
            phone=self._uniq_student_phone(phones[0] if phones else ""),
            phone2=(phones[1] if len(phones) > 1 else "")[:50],
            teacher=teacher,
            schedule=schedule,
            note=note_text,
            is_graduate=is_grad,
            source=SOURCE,
        )
        group.students.add(student)
        stats["students"] += 1

        # To'lovlar: oy ustuni aniq bo'lsa u bo'yicha, aks holda sentabrdan ketma-ket
        used_months = set()
        seq_i = 0
        for ci, amt in amounts:
            if month_cols and ci in month_cols:
                m = month_cols[ci]
            else:
                m = DEFAULT_MONTHS[seq_i % 12]
                seq_i += 1
            ms = month_str(m)
            if ms in used_months:
                continue
            used_months.add(ms)
            Payment.objects.create(
                student=student,
                month=ms,
                stage=1,
                amount_due=amt,
                is_paid=True,
                paid_amount=amt,
                paid_at=timezone.now(),
                source=SOURCE,
            )
            stats["payments"] += 1
            # kurs oylik narxini aniqlash uchun yig'amiz
            self._course_amounts.setdefault(group.course_id, []).append(amt)

    # ── LEADLAR ──
    def _import_leads(self, tab, stats):
        interest_kw = re.compile(
            r"html|css|javascript|js|tailwind|react|vue|vyuj|python|frontend|"
            r"\bfr\b|smm|\bks\b|dizayn|grafik|backend",
            re.I,
        )
        for r in tab["rows"]:
            first = str(r[0]).strip() if r else ""
            # Leadlarda faqat aniq guruh-sarlavhalarni tashlaymiz (#12, D/CH/J...)
            # — "dasturlashga qiziqadi" kabi kurs so'zli leadlar qolsin
            if not first or re.search(r"#\s*\d", first) or parse_schedule(first):
                continue
            name = first if not extract_phone(first) else ""
            phones, notes, interest = [], [], ""
            start = 0 if name else 0
            for c in (r if name == "" else r[1:]):
                c = str(c).strip()
                if not c or c == name:
                    continue
                ph = extract_phone(c)
                if ph and len(phones) < 2:
                    phones.append(ph)
                    continue
                if not interest and interest_kw.search(c):
                    interest = c
                    continue
                notes.append(c)
            if name == "" and phones:
                name = "(nomsiz)"
            if not name and not phones:
                continue
            note_text = " · ".join(notes)
            Lead.objects.create(
                name=(name or "(nomsiz)")[:200],
                phone=(phones[0] if phones else "")[:50],
                phone2=(phones[1] if len(phones) > 1 else "")[:50],
                status=(notes[0] if notes else "")[:200],
                interest=interest[:200],
                note=note_text,
                source_sheet=tab["title"][:100],
                source=SOURCE,
            )
            stats["leads"] += 1

    # ── BITIRUVCHILAR ──
    def _import_alumni(self, tab, stats):
        for r in tab["rows"]:
            first = str(r[0]).strip() if r else ""
            if not valid_person_name(first) or extract_phone(first):
                continue
            phones, notes = [], []
            for c in r[1:]:
                c = str(c).strip()
                if not c:
                    continue
                ph = extract_phone(c)
                if ph and len(phones) < 2:
                    phones.append(ph)
                    continue
                notes.append(c)
            name, surname = split_name(first)
            Student.objects.create(
                name=name[:100],
                surname=surname[:100],
                phone=self._uniq_student_phone(phones[0] if phones else ""),
                phone2=(phones[1] if len(phones) > 1 else "")[:50],
                is_graduate=True,
                note=" · ".join(notes),
                source=SOURCE,
            )
            stats["graduates"] += 1
            stats["students"] += 1

    # ── REKLAMA KANALLARI ──
    def _import_ads(self, tab, stats):
        for r in tab["rows"]:
            first = str(r[0]).strip() if r else ""
            if not first:
                continue
            username = first if first.startswith("@") else first
            notes = [str(c).strip() for c in r[1:] if str(c).strip()]
            title = notes[0] if notes else ""
            AdChannel.objects.create(
                username=username[:150],
                title=title[:200],
                note=" · ".join(notes[1:]),
                source=SOURCE,
            )
            stats["ads"] += 1
