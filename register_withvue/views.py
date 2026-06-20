import json
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password

from .models import Student, Teacher, Lesson, Attendance, Payment, StagePrice, StudentPenalty

ADMIN_PASSWORD = "excel2024"
EXCELLENCE_PASSWORD = "excellence2024"

ODD_DAYS = {0, 2, 4}
EVEN_DAYS = {1, 3, 5}


def get_stage_price(stage):
    sp = StagePrice.objects.filter(stage=stage).first()
    return sp.price if sp else 0


def get_schedule_for_day(weekday):
    if weekday in ODD_DAYS:
        return "odd"
    elif weekday in EVEN_DAYS:
        return "even"
    return None


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
    if request.method != "PATCH":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        attendance = Attendance.objects.filter(id=attendance_id).first()
        if not attendance:
            return JsonResponse({"error": "Attendance topilmadi"}, status=404)
        attendance.status = data.get("status")
        attendance.save()
        return JsonResponse({"message": "Yangilandi!"})
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
