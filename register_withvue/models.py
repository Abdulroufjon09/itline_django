from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# ─────────────────────────────────────────
# MANAGER
# ─────────────────────────────────────────


class Manager(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ism")
    surname = models.CharField(max_length=100, blank=True, verbose_name="Familiya")
    phone = models.CharField(max_length=20, unique=True, verbose_name="Telefon")
    password = models.CharField(max_length=255, verbose_name="Parol (hash)")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Menejer"
        verbose_name_plural = "Menejerlar"

    def __str__(self):
        return f"{self.name} {self.surname}"


# ─────────────────────────────────────────
# TEACHER
# ─────────────────────────────────────────


class Teacher(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, unique=True)
    password = models.CharField(max_length=255, blank=True)
    is_senior = models.BooleanField(default=False)
    penalty_limit = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "O'qituvchi"
        verbose_name_plural = "O'qituvchilar"

    def __str__(self):
        return self.name


# ─────────────────────────────────────────
# STUDENT
# ─────────────────────────────────────────


class Student(models.Model):
    SCHEDULE_CHOICES = [
        ("odd", "Du-Chor-Juma"),
        ("even", "Se-Pay-Shan"),
    ]

    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=255, blank=True)

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    stage = models.IntegerField(default=1)
    schedule = models.CharField(
        max_length=10,
        choices=SCHEDULE_CHOICES,
        default="odd",
    )
    is_admin = models.BooleanField(default=False)
    is_excellence = models.BooleanField(default=False)

    coin_balance = models.IntegerField(default=0, verbose_name="Coin balansi")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "O'quvchi"
        verbose_name_plural = "O'quvchilar"

    def __str__(self):
        return f"{self.name} {self.surname}"

    @property
    def effective_schedule(self):
        """Agar group bo'lsa, guruh schedule-idan olib, aks xolda student schedule-dan olib."""
        if self.group:
            return self.group.schedule
        return self.schedule


# ─────────────────────────────────────────
# STAGE PRICE
# ─────────────────────────────────────────


class StagePrice(models.Model):
    stage = models.IntegerField(unique=True)
    price = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Etap narxi"
        verbose_name_plural = "Etap narxlari"

    def __str__(self):
        return f"{self.stage}-etap: {self.price}"


# ─────────────────────────────────────────
# LESSON
# ─────────────────────────────────────────


class Lesson(models.Model):
    title = models.CharField(max_length=200)
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, related_name="lessons"
    )
    date = models.DateField()

    class Meta:
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"

    def __str__(self):
        return f"{self.title} ({self.date})"


# ─────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────


class Attendance(models.Model):
    STATUS_CHOICES = [
        ("present", "Keldi"),
        ("absent", "Kelmadi"),
        ("late", "Kech keldi"),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="attendances"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="attendances"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="absent")

    class Meta:
        unique_together = ("student", "lesson")
        verbose_name = "Davomat"
        verbose_name_plural = "Davomatlar"

    def __str__(self):
        return f"{self.student} — {self.lesson} — {self.status}"


# ─────────────────────────────────────────
# STUDENT PENALTY
# ─────────────────────────────────────────


class StudentPenalty(models.Model):
    REASON_CHOICES = [
        ("late", "Kech kelish"),
        ("absent", "Darsga kelmadi"),
        ("behavior", "Xulq-atvor"),
        ("other", "Boshqa"),
    ]
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="penalties",
    )
    given_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        related_name="given_penalties",
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default="other")
    description = models.TextField(blank=True)
    amount = models.IntegerField(default=0)
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "O'quvchi ja'zosi"
        verbose_name_plural = "O'quvchi ja'zolari"

    def __str__(self):
        return f"{self.student} — {self.get_reason_display()} — {self.amount}"


# ─────────────────────────────────────────
# PAYMENT
# ─────────────────────────────────────────


class Payment(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="payments"
    )
    month = models.CharField(max_length=7)
    stage = models.IntegerField()
    amount_due = models.IntegerField()
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_amount = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "month")
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"

    def __str__(self):
        return f"{self.student} — {self.month} — {self.amount_due}"


# ─────────────────────────────────────────
# COURSE
# ─────────────────────────────────────────


class Course(models.Model):
    name = models.CharField(max_length=100)
    # ✅ FIX: IntegerField faqat bitta ta'rif
    monthly_fee = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"

    def __str__(self):
        return self.name


# ─────────────────────────────────────────
# GROUP
# ─────────────────────────────────────────


class Group(models.Model):
    SCHEDULE_CHOICES = [
        ("odd", "Du-Chor-Juma"),
        ("even", "Se-Pay-Shan"),
    ]

    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, related_name="groups"
    )
    students = models.ManyToManyField(Student, related_name="groups")
    lesson_time = models.TimeField(null=False, blank=False)
    room = models.CharField(max_length=50, blank=True, default="", verbose_name="Xona")
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="groups",
        verbose_name=_("Course"),
    )

    schedule = models.CharField(
        max_length=10,
        choices=SCHEDULE_CHOICES,
        default="odd",
    )

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"

    def __str__(self):
        return self.name


# ─────────────────────────────────────────
# COIN TRANSACTION
# ─────────────────────────────────────────


class CoinTransaction(models.Model):
    REASON_CHOICES = [
        ("exam_pass", "Imtihondan o'tdi"),
        ("homework_done", "Vazifa qilingan"),
        ("homework_partial", "Vazifa chala qilingan"),
        ("homework_missed", "Vazifa qilinmagan"),
        ("present", "Darsga keldi"),
        ("late", "Kech keldi"),
        ("absent", "Darsga kelmadi"),
        ("manual", "Teacher tomonidan qo'lda"),
        ("purchase", "Magazindan xarid"),
        ("purchase_cancel", "Xarid bekor qilindi (qaytarildi)"),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="coin_transactions"
    )
    given_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coin_transactions_given",
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default="manual")
    amount = models.IntegerField(default=0)
    note = models.CharField(max_length=255, blank=True)
    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coin_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Coin tranzaksiyasi"
        verbose_name_plural = "Coin tranzaksiyalari"

    def __str__(self):
        return f"{self.student} — {self.get_reason_display()} — {self.amount}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Student.objects.filter(pk=self.student_id).update(
                coin_balance=models.F("coin_balance") + self.amount
            )

    def delete(self, *args, **kwargs):
        Student.objects.filter(pk=self.student_id).update(
            coin_balance=models.F("coin_balance") - self.amount
        )
        super().delete(*args, **kwargs)


# ─────────────────────────────────────────
# ATTENDANCE COIN SETTINGS
# ─────────────────────────────────────────


class AttendanceCoinSettings(models.Model):
    present = models.IntegerField(default=5, verbose_name="Keldi")
    late = models.IntegerField(default=2, verbose_name="Kech keldi")
    absent = models.IntegerField(default=-10, verbose_name="Kelmadi")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Davomat coin sozlamasi"
        verbose_name_plural = "Davomat coin sozlamalari"

    def __str__(self):
        return f"Keldi:{self.present} Kech:{self.late} Kelmadi:{self.absent}"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1, defaults={"present": 5, "late": 2, "absent": -10}
        )
        return obj


# ─────────────────────────────────────────
# PRODUCT (DO'KON)
# ─────────────────────────────────────────


class Product(models.Model):
    name = models.CharField(max_length=200)
    image = models.URLField(max_length=500, blank=True)
    price_coins = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    stock = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

    def __str__(self):
        return f"{self.name} — {self.price_coins} coin"


# ─────────────────────────────────────────
# ORDER
# ─────────────────────────────────────────


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Kutilmoqda"),
        ("approved", "Berildi"),
        ("rejected", "Bekor qilindi"),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="orders"
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, related_name="orders"
    )
    product_name = models.CharField(max_length=200)
    price_coins = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"

    def __str__(self):
        return f"{self.student} — {self.product_name} — {self.status}"

class News(models.Model):
    PRIORITY_CHOICES = [
        ("normal", "Oddiy"),
        ("important", "Muhim"),
        ("urgent", "Shoshilinch"),
    ]

    title = models.CharField(max_length=200, verbose_name="Sarlavha")
    content = models.TextField(verbose_name="Matn")
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="normal",
        verbose_name="Muhimlik",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")

    # ✅ Manager emas — Student (is_excellence=True bo'lgan)
    created_by = models.ForeignKey(
        "Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_posts",
        verbose_name="Kim yaratdi",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Muddati")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Yangilik"
        verbose_name_plural = "Yangiliklar"

    def __str__(self):
        return self.title