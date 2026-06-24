import json
from datetime import datetime

from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.db import models as db_models
from .models import Group
from .serializers import GroupSerializer

from .models import (
    Student, Teacher, Lesson, Attendance, Payment,
    StagePrice, StudentPenalty, Manager, CoinTransaction,
    Product, Order,
)

ADMIN_PASSWORD = "excel2024"
EXCELLENCE_PASSWORD = "excellence2024"

ODD_DAYS = {0, 2, 4}
EVEN_DAYS = {1, 3, 5}

# Attendance status o'zgarganda avtomatik beriladigan coinlar
ATTENDANCE_COINS = {
    "present": 10,
    "late": 5,
    "absent": -10,
}
ATTENDANCE_REASON = {
    "present": "present",
    "late": "late",
    "absent": "absent",
}

EXAM_PASS_COINS = 80
HOMEWORK_DONE_COINS = 20
HOMEWORK_MISSED_COINS = -20


def get_stage_price(stage):
    sp = StagePrice.objects.filter(stage=stage).first()
    return sp.price if sp else 0


def get_schedule_for_day(weekday):
    if weekday in ODD_DAYS:
        return "odd"
    elif weekday in EVEN_DAYS:
        return "even"
    return None


def apply_coin_transaction(student, amount, reason, given_by=None, note="", attendance=None):
    """
    Coin tranzaksiyasini yozadi. Student.coin_balance ni CoinTransaction.save()
    o'zi avtomatik (F() orqali) yangilaydi, shuning uchun bu yerda qo'lda
    mavjud bo'lmagan "coins" maydonini yangilashga urinmaymiz.
    amount musbat yoki manfiy bo'lishi mumkin.
    """
    CoinTransaction.objects.create(
        student=student,
        given_by=given_by,
        reason=reason,
        amount=amount,
        note=note,
        attendance=attendance,
    )
    student.refresh_from_db(fields=["coin_balance"])
    return student.coin_balance


# ─────────────────────────────────────────
# MANAGER (eng yuqori daraja)
# ─────────────────────────────────────────

@csrf_exempt
def manager_register(request):
    """
    Yangi menejer yaratish.
    Faqat mavjud menejer yoki boshlang'ich sozlash uchun.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        phone = data.get("phone", "").strip()

        if Manager.objects.filter(phone=phone).exists():
            return JsonResponse({"error": "Bu telefon raqam allaqachon ro'yxatdan o'tgan"}, status=400)

        manager = Manager.objects.create(
            name=data.get("name", "").strip(),
            surname=data.get("surname", "").strip(),
            phone=phone,
            password=make_password(data.get("password", "")),
        )
        return JsonResponse({
            "id": manager.id,
            "name": manager.name,
            "surname": manager.surname,
            "phone": manager.phone,
            "role": "manager",
        }, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def manager_login(request):
    """Menejer login."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        phone = data.get("phone", "")
        password = data.get("password", "")

        manager = Manager.objects.filter(phone=phone, is_active=True).first()
        if not manager:
            return JsonResponse({"error": "Menejer topilmadi"}, status=404)

        if not check_password(password, manager.password):
            return JsonResponse({"error": "Parol noto'g'ri"}, status=401)

        return JsonResponse({
            "id": manager.id,
            "name": manager.name,
            "surname": manager.surname,
            "phone": manager.phone,
            "role": "manager",
            "is_active": manager.is_active,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def get_managers(request):
    """Barcha menejerlar ro'yxati."""
    managers = list(
        Manager.objects.filter(is_active=True).values(
            "id", "name", "surname", "phone", "is_active", "created_at"
        )
    )
    return JsonResponse(managers, safe=False)


@csrf_exempt
def update_manager(request, manager_id):
    """Menejer ma'lumotlarini yangilash."""
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        manager = Manager.objects.filter(id=manager_id).first()
        if not manager:
            return JsonResponse({"error": "Menejer topilmadi"}, status=404)

        if "name" in data:
            manager.name = data["name"]
        if "surname" in data:
            manager.surname = data["surname"]
        if "phone" in data:
            manager.phone = data["phone"]
        if "password" in data and data["password"]:
            manager.password = make_password(data["password"])
        if "is_active" in data:
            manager.is_active = data["is_active"]
        manager.save()
        return JsonResponse({"message": "Menejer ma'lumotlari yangilandi!"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def delete_manager(request, manager_id):
    """Menejerni o'chirish (deaktivatsiya)."""
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    manager = Manager.objects.filter(id=manager_id).first()
    if not manager:
        return JsonResponse({"error": "Menejer topilmadi"}, status=404)
    manager.is_active = False
    manager.save()
    return JsonResponse({"message": "Menejer deaktivatsiya qilindi!"})


# ─────────────────────────────────────────
# COIN
# ─────────────────────────────────────────

def get_coin_balance(request, student_id):
    """Student coin balansini ko'rish."""
    student = Student.objects.filter(id=student_id).first()
    if not student:
        return JsonResponse({"error": "Student topilmadi"}, status=404)
    return JsonResponse({
        "student_id": student.id,
        "student_name": f"{student.name} {student.surname}",
        "coin_balance": student.coin_balance,
    })


def get_all_coin_balances(request):
    """
    Barcha studentlarning coin balansini ko'rish.
    ?teacher_id=X filter qo'llab-quvvatlanadi.
    """
    teacher_id = request.GET.get("teacher_id", "")
    qs = Student.objects.select_related("teacher").filter(
        is_admin=False, is_excellence=False
    ).order_by("-coin_balance")

    if teacher_id:
        try:
            qs = qs.filter(teacher_id=int(teacher_id))
        except ValueError:
            pass

    data = [
        {
            "student_id": s.id,
            "name": s.name,
            "surname": s.surname,
            "teacher_name": s.teacher.name if s.teacher else "Biriktirilmagan",
            "coin_balance": s.coin_balance,
        }
        for s in qs
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def add_coin(request):
    """
    Studentga coin berish yoki olish.
    Teacher yoki Manager tomonidan chaqiriladi.

    Eslatma: CoinTransaction.given_by faqat Teacher'ga bog'langan (model
    shunday yaratilgan), shu sabab Manager bergan coin uchun "given_by"
    bo'sh qoldiriladi, lekin menejer ismi "note" ichida yoziladi.

    Body:
    {
        "student_id": 5,
        "amount": 10,          # manfiy bo'lishi ham mumkin (jarima)
        "reason": "manual",
        "description": "...",
        "teacher_id": 2,       # teacher chaqirsa
        "manager_id": 1        # manager chaqirsa
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)

        student = Student.objects.filter(id=data.get("student_id")).first()
        if not student:
            return JsonResponse({"error": "Student topilmadi"}, status=404)

        amount = data.get("amount")
        if amount is None:
            return JsonResponse({"error": "amount kiritilmadi"}, status=400)

        amount = int(amount)

        # Balans manfiy bo'lmasligi tekshiruvi (ixtiyoriy)
        if student.coin_balance + amount < 0:
            return JsonResponse({
                "error": f"Yetarli coin yo'q. Joriy balans: {student.coin_balance}"
            }, status=400)

        given_by_teacher = None
        note = data.get("description", "")

        if data.get("manager_id"):
            manager = Manager.objects.filter(
                id=data["manager_id"], is_active=True
            ).first()
            if manager:
                note = f"[Menejer: {manager.name} {manager.surname}] {note}".strip()

        elif data.get("teacher_id"):
            given_by_teacher = Teacher.objects.filter(id=data["teacher_id"]).first()

        new_balance = apply_coin_transaction(
            student,
            amount,
            data.get("reason", "manual"),
            given_by=given_by_teacher,
            note=note,
        )

        return JsonResponse({
            "message": "Coin qo'shildi!" if amount >= 0 else "Coin ayirildi!",
            "amount": amount,
            "new_balance": new_balance,
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def delete_coin_transaction(request, txn_id):
    """
    Coin tranzaksiyasini bekor qilish (faqat Manager).
    Balans qayta hisoblanadi.
    """
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    txn = CoinTransaction.objects.filter(id=txn_id).first()
    if not txn:
        return JsonResponse({"error": "Tranzaksiya topilmadi"}, status=404)

    # Balansni teskari qaytaramiz
    Student.objects.filter(pk=txn.student_id).update(
        coin_balance=db_models.F("coin_balance") - txn.amount
    )
    txn.delete()
    return JsonResponse({"message": "Tranzaksiya bekor qilindi va balans qayta hisoblandi!"})


@csrf_exempt
def set_coin_balance(request, student_id):
    """
    Faqat Manager: student coin balansini to'g'ridan-to'g'ri belgilash.
    Farqni CoinTransaction sifatida saqlaydi.
    """
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        new_balance = data.get("coin_balance")
        manager_id = data.get("manager_id")

        if new_balance is None:
            return JsonResponse({"error": "coin_balance kiritilmadi"}, status=400)

        student = Student.objects.filter(id=student_id).first()
        if not student:
            return JsonResponse({"error": "Student topilmadi"}, status=404)

        diff = int(new_balance) - student.coin_balance
        if diff == 0:
            return JsonResponse({"message": "Balans o'zgarmadi", "coin_balance": student.coin_balance})

        note = f"Balans to'g'ridan-to'g'ri {new_balance} ga o'rnatildi"
        if manager_id:
            manager = Manager.objects.filter(id=manager_id, is_active=True).first()
            if manager:
                note = f"[Menejer: {manager.name} {manager.surname}] {note}"

        updated_balance = apply_coin_transaction(
            student,
            diff,
            "manual",
            note=note,
        )

        return JsonResponse({
            "message": "Balans yangilandi!",
            "coin_balance": updated_balance,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ─────────────────────────────────────────
# TEACHERS
# ─────────────────────────────────────────

def get_teachers(request):
    try:
        teachers = list(
            Teacher.objects.all().values("id", "name", "phone", "is_senior", "penalty_limit")
        )
        return JsonResponse(teachers, safe=False)
    except Exception as e:
        # Return JSON error (prevents frontend JSON.parse errors when server
        # returns HTML error pages). Keep field names unchanged for Vue.
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def create_teacher(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        teacher = Teacher.objects.create(
            name=data.get("name"),
            phone=data.get("phone", ""),
            is_senior=data.get("is_senior", False),
        )
        return JsonResponse({"id": teacher.id, "name": teacher.name}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def delete_teacher(request, teacher_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    Teacher.objects.filter(id=teacher_id).delete()
    return JsonResponse({"message": "O'chirildi!"})


@csrf_exempt
def update_teacher(request, teacher_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        teacher = Teacher.objects.filter(id=teacher_id).first()
        if not teacher:
            return JsonResponse({"error": "Teacher topilmadi"}, status=404)
        if "name" in data:
            teacher.name = data["name"]
        if "phone" in data:
            teacher.phone = data["phone"]
        if "is_senior" in data:
            teacher.is_senior = data["is_senior"]
        if "penalty_limit" in data:
            teacher.penalty_limit = data["penalty_limit"]
        teacher.save()
        return JsonResponse({"message": "Yangilandi!"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def update_teacher_penalty_limit(request, teacher_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        teacher = Teacher.objects.filter(id=teacher_id).first()
        if not teacher:
            return JsonResponse({"error": "Teacher topilmadi"}, status=404)
        teacher.penalty_limit = data.get("penalty_limit", 0)
        teacher.save()
        return JsonResponse({"penalty_limit": teacher.penalty_limit})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def reassign_students(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        Student.objects.filter(teacher_id=data.get("from_teacher_id")).update(
            teacher_id=data.get("to_teacher_id")
        )
        return JsonResponse({"message": "O'quvchilar o'tkazildi!"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ─────────────────────────────────────────
# STAGE PRICES
# ─────────────────────────────────────────

def get_stage_prices(request):
    prices = list(
        StagePrice.objects.all().order_by("stage").values("id", "stage", "price")
    )
    return JsonResponse(prices, safe=False)


@csrf_exempt
def update_stage_price(request, stage):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        price = data.get("price")
        if price is None:
            return JsonResponse({"error": "price kiritilmadi"}, status=400)
        sp, _ = StagePrice.objects.get_or_create(stage=stage, defaults={"price": price})
        sp.price = price
        sp.save()
        return JsonResponse({"stage": stage, "price": sp.price})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ─────────────────────────────────────────
# STUDENTS
# ─────────────────────────────────────────

def get_students(request):
    teacher_id = request.GET.get("teacher_id")
    qs = Student.objects.select_related("teacher").filter(
        is_admin=False, is_excellence=False
    )
    if teacher_id and teacher_id != "null":
        try:
            qs = qs.filter(teacher_id=int(teacher_id))
        except ValueError:
            pass
    data = [
        {
            "id": s.id,
            "name": s.name,
            "surname": s.surname,
            "phone": s.phone,
            "teacher_id": s.teacher_id,
            "teacher_name": s.teacher.name if s.teacher else "Biriktirilmagan",
            "stage": s.stage,
            "schedule": s.schedule,
            "coin_balance": s.coin_balance,
        }
        for s in qs
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def update_student(request, student_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        student = Student.objects.select_related("teacher").filter(id=student_id).first()
        if not student:
            return JsonResponse({"error": "Student topilmadi"}, status=404)

        if "stage" in data:
            student.stage = data["stage"]
            if data["stage"] == 5:
                senior_teacher = Teacher.objects.filter(is_senior=True).first()
                if senior_teacher:
                    student.teacher = senior_teacher

        if "schedule" in data:
            student.schedule = data["schedule"]

        student.save()
        return JsonResponse({
            "message": "Yangilandi!",
            "stage": student.stage,
            "schedule": student.schedule,
            "teacher_id": student.teacher_id,
            "teacher_name": student.teacher.name if student.teacher else "",
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def register_student(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        phone = data.get("phone")

        if Student.objects.filter(phone=phone).exists():
            return JsonResponse({"error": "Bu telefon mavjud"}, status=400)

        admin_password = data.get("admin_password", "")
        excellence_password = data.get("excellence_password", "")

        is_admin = admin_password == ADMIN_PASSWORD
        is_excellence = excellence_password == EXCELLENCE_PASSWORD

        teacher = None
        if not is_admin and not is_excellence:
            teacher = Teacher.objects.filter(id=data.get("teacher_id")).first()

        student = Student.objects.create(
            name=data.get("name"),
            surname=data.get("surname", ""),
            phone=phone,
            password=make_password(data.get("password", "")),
            teacher=teacher,
            is_admin=is_admin,
            is_excellence=is_excellence,
            schedule=data.get("schedule", "odd"),
        )

        if is_admin or is_excellence:
            new_teacher = Teacher.objects.create(
                name=f"{data.get('name')} {data.get('surname', '')}".strip(),
                phone=phone,
                is_senior=is_excellence,
            )
            student.teacher = new_teacher
            student.save()

        return JsonResponse({
            "message": "Muvaffaqiyatli!",
            "id": student.id,
            "name": student.name,
            "surname": student.surname,
            "phone": student.phone,
            "teacher_id": student.teacher_id,
            "teacher_name": student.teacher.name if student.teacher else "",
            "stage": student.stage,
            "schedule": student.schedule,
            "is_admin": student.is_admin,
            "is_excellence": student.is_excellence,
            "coin_balance": student.coin_balance,
        }, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def login_student(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        phone = data.get("phone")
        password = data.get("password")

        student = Student.objects.select_related("teacher").filter(phone=phone).first()

        if password is None:
            return JsonResponse({"exists": bool(student)})

        if not student:
            return JsonResponse({"exists": False, "error": "Foydalanuvchi topilmadi"}, status=404)

        if not check_password(password, student.password):
            return JsonResponse({"exists": False, "error": "Parol noto'g'ri"}, status=401)

        return JsonResponse({
            "exists": True,
            "id": student.id,
            "name": student.name,
            "surname": student.surname,
            "phone": student.phone,
            "teacher_id": student.teacher_id,
            "teacher_name": student.teacher.name if student.teacher else "",
            "is_admin": student.is_admin,
            "is_excellence": student.is_excellence,
            "stage": student.stage,
            "schedule": student.schedule,
            "coin_balance": student.coin_balance,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ─────────────────────────────────────────
# LESSONS
# ─────────────────────────────────────────

def get_lessons(request):
    teacher_id = request.GET.get("teacher_id", "")
    qs = Lesson.objects.select_related("teacher").order_by("-date")
    if teacher_id:
        qs = qs.filter(teacher_id=teacher_id)
    data = [
        {
            "id": lesson.id,
            "title": lesson.title,
            "date": str(lesson.date),
            "teacher_name": lesson.teacher.name if lesson.teacher else "",
        }
        for lesson in qs
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def create_lesson(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        teacher = Teacher.objects.filter(id=data.get("teacher_id")).first()
        if not teacher:
            return JsonResponse({"error": "Teacher topilmadi"}, status=404)

        lesson_date = data.get("date")
        parsed_date = datetime.strptime(lesson_date, "%Y-%m-%d").date()
        weekday = parsed_date.weekday()
        schedule_for_day = get_schedule_for_day(weekday)

        lesson = Lesson.objects.create(
            title=data.get("title"),
            teacher=teacher,
            date=lesson_date,
        )

        students_qs = teacher.students.filter(is_admin=False, is_excellence=False)
        if schedule_for_day:
            students_qs = students_qs.filter(schedule=schedule_for_day)

        for student in students_qs:
            Attendance.objects.get_or_create(
                student=student,
                lesson=lesson,
                defaults={"status": "absent"},
            )

        return JsonResponse({
            "id": lesson.id,
            "message": "Dars yaratildi!",
            "schedule": schedule_for_day,
        }, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ─────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────

def get_attendance(request, lesson_id):
    attendances = Attendance.objects.filter(lesson_id=lesson_id).select_related("student")
    data = [
        {
            "id": a.id,
            "student_id": a.student.id,
            "student_name": f"{a.student.name} {a.student.surname}",
            "schedule": a.student.schedule,
            "status": a.status,
        }
        for a in attendances
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def update_attendance(request, attendance_id):
    """
    Status yangilanganda avtomatik coin beriladi/ayiriladi:
    present +10, late +5, absent -10.
    Agar status avval ham xuddi shu bo'lsa, qayta coin berilmaydi (idempotent).
    Status o'zgarsa, eski statusning coini bekor qilinib, yangisi qo'llanadi.
    """
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        attendance = Attendance.objects.select_related("student").filter(id=attendance_id).first()
        if not attendance:
            return JsonResponse({"error": "Attendance topilmadi"}, status=404)

        new_status = data.get("status")
        old_status = attendance.status

        if new_status not in dict(Attendance.STATUS_CHOICES):
            return JsonResponse({"error": "Noto'g'ri status"}, status=400)

        with transaction.atomic():
            if new_status != old_status:
                student = attendance.student

                # Eski statusga berilgan coinni bekor qilamiz (agar bor bo'lsa)
                if old_status in ATTENDANCE_COINS:
                    apply_coin_transaction(
                        student,
                        -ATTENDANCE_COINS[old_status],
                        ATTENDANCE_REASON.get(old_status, "manual"),
                        note=f"Status '{old_status}' bekor qilindi",
                        attendance=attendance,
                    )

                # Yangi statusga coin beramiz
                if new_status in ATTENDANCE_COINS:
                    apply_coin_transaction(
                        student,
                        ATTENDANCE_COINS[new_status],
                        ATTENDANCE_REASON.get(new_status, "manual"),
                        note=f"Status: {new_status}",
                        attendance=attendance,
                    )

            attendance.status = new_status
            attendance.save()

        return JsonResponse({"message": "Yangilandi!", "coin_balance": attendance.student.coin_balance})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def get_student_attendance(request, student_id):
    month = request.GET.get("month", "")
    qs = (
        Attendance.objects.filter(student_id=student_id)
        .select_related("lesson")
        .order_by("lesson__date")
    )
    if month:
        year, mon = month.split("-")
        qs = qs.filter(lesson__date__year=year, lesson__date__month=mon)
    data = [
        {
            "id": a.id,
            "lesson_id": a.lesson.id,
            "lesson_title": a.lesson.title,
            "lesson_date": str(a.lesson.date),
            "status": a.status,
        }
        for a in qs
    ]
    return JsonResponse(data, safe=False)


def get_monthly_absences(request):
    month = request.GET.get("month", datetime.now().strftime("%Y-%m"))
    teacher_id = request.GET.get("teacher_id", "")

    qs = Student.objects.filter(is_admin=False, is_excellence=False)
    if teacher_id:
        qs = qs.filter(teacher_id=teacher_id)

    year, mon = month.split("-")
    result = {}
    for student in qs:
        count = Attendance.objects.filter(
            student=student,
            status="absent",
            lesson__date__year=year,
            lesson__date__month=mon,
        ).count()
        result[student.id] = count

    return JsonResponse(result)


# ─────────────────────────────────────────
# STUDENT PENALTIES
# ─────────────────────────────────────────

def get_student_penalties(request, student_id):
    penalties = StudentPenalty.objects.filter(student_id=student_id).order_by("-date")
    data = [
        {
            "id": p.id,
            "reason": p.reason,
            "reason_display": p.get_reason_display(),
            "description": p.description,
            "amount": p.amount,
            "date": str(p.date),
            "given_by": p.given_by.name if p.given_by else "",
        }
        for p in penalties
    ]
    return JsonResponse(data, safe=False)


def get_teacher_students_penalties(request, teacher_id):
    """Teacher o'z studentlarining ja'zolarini ko'radi"""
    penalties = StudentPenalty.objects.filter(
        student__teacher_id=teacher_id
    ).select_related("student").order_by("-date")
    data = [
        {
            "id": p.id,
            "student_id": p.student.id,
            "student_name": f"{p.student.name} {p.student.surname}",
            "reason": p.reason,
            "reason_display": p.get_reason_display(),
            "description": p.description,
            "amount": p.amount,
            "date": str(p.date),
        }
        for p in penalties
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def create_student_penalty(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        student = Student.objects.filter(id=data.get("student_id")).first()
        if not student:
            return JsonResponse({"error": "Student topilmadi"}, status=404)

        given_by = None
        if data.get("teacher_id"):
            given_by = Teacher.objects.filter(id=data["teacher_id"]).first()

        penalty = StudentPenalty.objects.create(
            student=student,
            given_by=given_by,
            reason=data.get("reason", "other"),
            description=data.get("description", ""),
            amount=data.get("amount", 0),
        )
        return JsonResponse({"id": penalty.id, "message": "Ja'zo qo'shildi"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def delete_student_penalty(request, penalty_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    penalty = StudentPenalty.objects.filter(id=penalty_id).first()
    if not penalty:
        return JsonResponse({"error": "Topilmadi"}, status=404)
    penalty.delete()
    return JsonResponse({"message": "O'chirildi!"})


# ─────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────

def get_payments(request, student_id):
    payments = Payment.objects.filter(student_id=student_id).order_by("-month")
    data = [
        {
            "id": p.id,
            "month": p.month,
            "stage": p.stage,
            "amount_due": p.amount_due,
            "is_paid": p.is_paid,
            "paid_at": p.paid_at.strftime("%Y-%m-%d") if p.paid_at else None,
        }
        for p in payments
    ]
    return JsonResponse(data, safe=False)


def get_all_payments(request):
    month = request.GET.get("month", "")
    teacher_id = request.GET.get("teacher_id", "")
    qs = Payment.objects.select_related("student", "student__teacher").order_by(
        "-month", "student__name"
    )
    if month:
        qs = qs.filter(month=month)
    if teacher_id:
        qs = qs.filter(student__teacher_id=teacher_id)
    data = [
        {
            "id": p.id,
            "student_id": p.student.id,
            "student_name": f"{p.student.name} {p.student.surname}",
            "student_phone": p.student.phone,
            "teacher_name": p.student.teacher.name if p.student.teacher else "",
            "month": p.month,
            "stage": p.stage,
            "amount_due": p.amount_due,
            "is_paid": p.is_paid,
            "paid_at": str(p.paid_at) if p.paid_at else None,
        }
        for p in qs
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def generate_payments(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        month = data.get("month")
        if not month:
            return JsonResponse({"error": "month kiritilmadi"}, status=400)

        students = Student.objects.filter(is_admin=False, is_excellence=False)
        created_count = 0
        skipped_count = 0

        for student in students:
            price = get_stage_price(student.stage)
            _, created = Payment.objects.get_or_create(
                student=student,
                month=month,
                defaults={"stage": student.stage, "amount_due": price},
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        return JsonResponse({
            "message": f"{created_count} ta yangi to'lov yaratildi, {skipped_count} ta mavjud edi.",
            "month": month,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def confirm_payment(request, payment_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        payment = Payment.objects.filter(id=payment_id).first()
        if not payment:
            return JsonResponse({"error": "To'lov topilmadi"}, status=404)
        payment.is_paid = data.get("is_paid", True)
        payment.paid_at = datetime.now() if payment.is_paid else None
        payment.save()
        return JsonResponse({"message": "Yangilandi!", "is_paid": payment.is_paid})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def update_payment_amount(request, payment_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        payment = Payment.objects.filter(id=payment_id).first()
        if not payment:
            return JsonResponse({"error": "To'lov topilmadi"}, status=404)
        if "amount_due" in data:
            payment.amount_due = data["amount_due"]
        payment.save()
        return JsonResponse({
            "message": "Summa yangilandi!",
            "amount_due": payment.amount_due,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ─────────────────────────────────────────
# GROUPS
# ─────────────────────────────────────────


def get_groups(request):
    groups = Group.objects.select_related(
        "teacher"
    ).prefetch_related(
        "students"
    )

    serializer = GroupSerializer(groups, many=True)

    return JsonResponse(serializer.data, safe=False)


def get_group(request, group_id):
    group = Group.objects.filter(id=group_id).first()

    if not group:
        return JsonResponse(
            {"error": "Group topilmadi"},
            status=404
        )

    serializer = GroupSerializer(group)

    return JsonResponse(serializer.data, safe=False)


@csrf_exempt
def create_group(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "Method not allowed"},
            status=405
        )

    try:
        data = json.loads(request.body)

        teacher = None

        if data.get("teacher_id"):
            teacher = Teacher.objects.filter(
                id=data.get("teacher_id")
            ).first()

        group = Group.objects.create(
            name=data.get("name"),
            teacher=teacher,
            lesson_time=data.get("lesson_time") or "09:00",
            schedule=data.get("schedule", "odd"),
        )

        student_ids = data.get("students", [])

        if student_ids:
            group.students.set(student_ids)

        serializer = GroupSerializer(group)

        return JsonResponse(
            serializer.data,
            status=201
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=400
        )


@csrf_exempt
def update_group(request, group_id):
    if request.method != "PATCH":
        return JsonResponse(
            {"error": "Method not allowed"},
            status=405
        )

    try:
        data = json.loads(request.body)

        group = Group.objects.filter(
            id=group_id
        ).first()

        if not group:
            return JsonResponse(
                {"error": "Group topilmadi"},
                status=404
            )

        if "name" in data:
            group.name = data["name"]

        if "teacher_id" in data:
            group.teacher = Teacher.objects.filter(
                id=data["teacher_id"]
            ).first()

        if "lesson_time" in data:
            group.lesson_time = data["lesson_time"]

        if "schedule" in data:
            group.schedule = data["schedule"]

        group.save()

        if "students" in data:
            group.students.set(
                data["students"]
            )

        serializer = GroupSerializer(group)

        return JsonResponse(
            serializer.data,
            safe=False
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=400
        )


@csrf_exempt
def delete_group(request, group_id):
    if request.method != "DELETE":
        return JsonResponse(
            {"error": "Method not allowed"},
            status=405
        )

    group = Group.objects.filter(
        id=group_id
    ).first()

    if not group:
        return JsonResponse(
            {"error": "Group topilmadi"},
            status=404
        )

    group.delete()

    return JsonResponse({
        "message": "Group o'chirildi!"
    })


# ─────────────────────────────────────────
# COINS (qo'shimcha - student/teacher uchun)
# ─────────────────────────────────────────

def get_student_coins(request, student_id):
    """Student faqat o'z coinini ko'rishi uchun (frontend 'faqat coins ko'rinishi' talabi)."""
    student = Student.objects.filter(id=student_id).first()
    if not student:
        return JsonResponse({"error": "Student topilmadi"}, status=404)
    return JsonResponse({"student_id": student.id, "coin_balance": student.coin_balance})


def get_coin_transactions(request, student_id):
    """Student/teacher uchun coin tarixi."""
    qs = CoinTransaction.objects.filter(student_id=student_id).select_related(
        "given_by"
    ).order_by("-created_at")
    data = [
        {
            "id": t.id,
            "reason": t.reason,
            "reason_display": t.get_reason_display(),
            "amount": t.amount,
            "note": t.note,
            "given_by": t.given_by.name if t.given_by else "Tizim",
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for t in qs
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def give_manual_coins(request):
    """
    Teacher o'z studentiga hohlagan miqdorda coin beradi.
    Sabab: imtihon (+80 default), vazifa (+/-20 default) yoki erkin 'manual' miqdor.
    Body: { student_id, teacher_id, reason, amount (optional), note (optional) }
    Agar reason='exam_pass' yoki 'homework_done'/'homework_missed' bo'lsa va amount
    berilmasa, default qiymatlar ishlatiladi. Aks holda amount majburiy.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        student = Student.objects.filter(id=data.get("student_id")).first()
        if not student:
            return JsonResponse({"error": "Student topilmadi"}, status=404)

        teacher = None
        if data.get("teacher_id"):
            teacher = Teacher.objects.filter(id=data["teacher_id"]).first()

        reason = data.get("reason", "manual")
        amount = data.get("amount")

        defaults = {
            "exam_pass": EXAM_PASS_COINS,
            "homework_done": HOMEWORK_DONE_COINS,
            "homework_missed": HOMEWORK_MISSED_COINS,
        }
        if amount is None:
            amount = defaults.get(reason)
        if amount is None:
            return JsonResponse({"error": "amount kiritilmadi"}, status=400)

        new_balance = apply_coin_transaction(
            student,
            amount,
            reason,
            given_by=teacher,
            note=data.get("note", ""),
        )

        return JsonResponse({
            "message": "Coin berildi!",
            "student_id": student.id,
            "coin_balance": new_balance,
        }, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def get_leaderboard(request):
    """
    Eng ko'p coin to'plagan studentlar reytingi.
    Ixtiyoriy: ?teacher_id= bilan faqat shu teacher studentlari orasida reyting.
    """
    teacher_id = request.GET.get("teacher_id", "")
    qs = Student.objects.select_related("teacher").filter(
        is_admin=False, is_excellence=False
    )
    if teacher_id:
        qs = qs.filter(teacher_id=teacher_id)

    qs = qs.order_by("-coin_balance", "name")[:100]

    data = [
        {
            "rank": i + 1,
            "id": s.id,
            "name": s.name,
            "surname": s.surname,
            "teacher_name": s.teacher.name if s.teacher else "",
            "coin_balance": s.coin_balance,
        }
        for i, s in enumerate(qs)
    ]
    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────
# MAGAZINE (DO'KON)
# ─────────────────────────────────────────

def get_products(request):
    """Student/umumiy ko'rinish uchun: faqat aktiv mahsulotlar."""
    qs = Product.objects.filter(is_active=True).order_by("price_coins")
    data = [
        {
            "id": p.id,
            "name": p.name,
            "image": p.image,
            "price_coins": p.price_coins,
            "description": p.description,
            "stock": p.stock,
        }
        for p in qs
    ]
    return JsonResponse(data, safe=False)


def get_all_products(request):
    """Admin uchun: faol va nofaol barcha mahsulotlar."""
    qs = Product.objects.all().order_by("-created_at")
    data = [
        {
            "id": p.id,
            "name": p.name,
            "image": p.image,
            "price_coins": p.price_coins,
            "description": p.description,
            "is_active": p.is_active,
            "stock": p.stock,
        }
        for p in qs
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def create_product(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        product = Product.objects.create(
            name=data.get("name"),
            image=data.get("image", ""),
            price_coins=data.get("price_coins", 0),
            description=data.get("description", ""),
            is_active=data.get("is_active", True),
            stock=data.get("stock"),
        )
        return JsonResponse({"id": product.id, "message": "Mahsulot qo'shildi!"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def update_product(request, product_id):
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        product = Product.objects.filter(id=product_id).first()
        if not product:
            return JsonResponse({"error": "Mahsulot topilmadi"}, status=404)

        if "name" in data:
            product.name = data["name"]
        if "image" in data:
            product.image = data["image"]
        if "price_coins" in data:
            product.price_coins = data["price_coins"]
        if "description" in data:
            product.description = data["description"]
        if "is_active" in data:
            product.is_active = data["is_active"]
        if "stock" in data:
            product.stock = data["stock"]
        product.save()
        return JsonResponse({"message": "Mahsulot yangilandi!"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def delete_product(request, product_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    Product.objects.filter(id=product_id).delete()
    return JsonResponse({"message": "O'chirildi!"})


# ─────────────────────────────────────────
# ORDERS (Magazindan xarid)
# ─────────────────────────────────────────

@csrf_exempt
def create_order(request):
    """
    Student coin sarflab mahsulot buyurtma qiladi.
    Coin darhol ayiriladi (rezerv qilinadi), status='pending' bo'lib qoladi.
    Admin/teacher keyin approve yoki reject qiladi (reject bo'lsa coin qaytariladi).
    Body: { student_id, product_id }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        student = Student.objects.filter(id=data.get("student_id")).first()
        if not student:
            return JsonResponse({"error": "Student topilmadi"}, status=404)

        product = Product.objects.filter(id=data.get("product_id"), is_active=True).first()
        if not product:
            return JsonResponse({"error": "Mahsulot topilmadi yoki faol emas"}, status=404)

        if product.stock is not None and product.stock <= 0:
            return JsonResponse({"error": "Mahsulot tugagan"}, status=400)

        if student.coin_balance < product.price_coins:
            return JsonResponse({"error": "Coin yetarli emas"}, status=400)

        with transaction.atomic():
            order = Order.objects.create(
                student=student,
                product=product,
                product_name=product.name,
                price_coins=product.price_coins,
                status="pending",
            )

            apply_coin_transaction(
                student,
                -product.price_coins,
                "purchase",
                note=f"Buyurtma #{order.id}: {product.name}",
            )

            if product.stock is not None:
                product.stock -= 1
                product.save(update_fields=["stock"])

        return JsonResponse({
            "id": order.id,
            "message": "Buyurtma yaratildi!",
            "coin_balance": student.coin_balance,
        }, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def get_student_orders(request, student_id):
    qs = Order.objects.filter(student_id=student_id).order_by("-created_at")
    data = [
        {
            "id": o.id,
            "product_name": o.product_name,
            "price_coins": o.price_coins,
            "status": o.status,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for o in qs
    ]
    return JsonResponse(data, safe=False)


def get_all_orders(request):
    """Admin uchun: barcha buyurtmalar (kerak bo'lsa status bo'yicha filter)."""
    status = request.GET.get("status", "")
    qs = Order.objects.select_related("student").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    data = [
        {
            "id": o.id,
            "student_id": o.student.id,
            "student_name": f"{o.student.name} {o.student.surname}",
            "product_name": o.product_name,
            "price_coins": o.price_coins,
            "status": o.status,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for o in qs
    ]
    return JsonResponse(data, safe=False)


@csrf_exempt
def resolve_order(request, order_id):
    """
    Admin buyurtmani tasdiqlaydi (approved) yoki rad etadi (rejected).
    Rad etilsa, sarflangan coin studentga qaytariladi.
    Body: { status: 'approved' | 'rejected' }
    """
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        new_status = data.get("status")
        if new_status not in ("approved", "rejected"):
            return JsonResponse({"error": "Noto'g'ri status"}, status=400)

        order = Order.objects.select_related("student").filter(id=order_id).first()
        if not order:
            return JsonResponse({"error": "Buyurtma topilmadi"}, status=404)

        if order.status != "pending":
            return JsonResponse({"error": "Bu buyurtma allaqachon hal qilingan"}, status=400)

        with transaction.atomic():
            if new_status == "rejected":
                apply_coin_transaction(
                    order.student,
                    order.price_coins,
                    "purchase_cancel",
                    note=f"Buyurtma #{order.id} bekor qilindi, coin qaytarildi",
                )
                if order.product and order.product.stock is not None:
                    order.product.stock += 1
                    order.product.save(update_fields=["stock"])

            order.status = new_status
            order.resolved_at = datetime.now()
            order.save()

        return JsonResponse({"message": "Yangilandi!", "status": order.status})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)