from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────
# MANAGER (eng yuqori daraja: admin va teacher dan ham baland)
# ─────────────────────────────────────────

class Manager(models.Model):
    """
    Tizimning eng yuqori darajadagi foydalanuvchisi.
    Admin va Teacher dan ham baland — hamma narsaga to'liq ruxsat.
    """
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
        return f"{self.name} {self.surname}".strip()


# ─────────────────────────────────────────
# TEACHER
# ─────────────────────────────────────────

class Teacher(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    is_senior = models.BooleanField(default=False)
    penalty_limit = models.IntegerField(default=0)  # 0 = limitsiz
    created_at = models.DateTimeField(auto_now_add=True)

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
<<<<<<< HEAD

    # Coin balans (tezkor ko'rish uchun kesh — asosiy manba CoinTransaction)
    coin_balance = models.IntegerField(default=0, verbose_name="Coin balansi")

=======
    coins = models.IntegerField(default=0)
>>>>>>> 1e950e7008cec6d3adea7146ad4b7f5bb4019d9d
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} {self.surname}"


# ─────────────────────────────────────────
# COIN
# ─────────────────────────────────────────

class CoinTransaction(models.Model):
    """
    Har bir coin operatsiyasi (berish yoki olish) shu yerda saqlanadi.
    amount > 0  → coin berildi
    amount < 0  → coin olindi / jarima
    """
    REASON_CHOICES = [
        ("reward", "Mukofot"),
        ("attendance", "Davomat uchun"),
        ("homework", "Uy ishi uchun"),
        ("behavior", "Xulq-atvor"),
        ("penalty", "Jarima"),
        ("manual", "Qo'lda kiritilgan"),
        ("other", "Boshqa"),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="coin_transactions",
        verbose_name="O'quvchi",
    )
    amount = models.IntegerField(verbose_name="Miqdor (+/-)")
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default="manual",
        verbose_name="Sabab",
    )
    description = models.TextField(blank=True, verbose_name="Izoh")

    # Kim berdi: teacher yoki manager
    given_by_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coin_transactions_given",
        verbose_name="Bergan o'qituvchi",
    )
    given_by_manager = models.ForeignKey(
        Manager,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coin_transactions_given",
        verbose_name="Bergan menejer",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Coin tranzaksiyasi"
        verbose_name_plural = "Coin tranzaksiyalari"

    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"{self.student} — {sign}{self.amount} coin ({self.get_reason_display()})"

    def save(self, *args, **kwargs):
        """
        Tranzaksiya saqlanganda student.coin_balance ni avtomatik yangilaydi.
        Yangi tranzaksiya bo'lsa (id yo'q) balansga qo'shadi.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Student.objects.filter(pk=self.student_id).update(
                coin_balance=models.F("coin_balance") + self.amount
            )


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

    def __str__(self):
        return f"{self.student} — {self.get_reason_display()} — {self.amount}"


# ─────────────────────────────────────────
# STAGE PRICE
# ─────────────────────────────────────────

class StagePrice(models.Model):
    stage = models.IntegerField(unique=True)
    price = models.IntegerField(default=0)

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

    def __str__(self):
        return self.title


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

    def __str__(self):
        return f"{self.student} — {self.lesson} — {self.status}"


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "month")

    def __str__(self):
        return f"{self.student} — {self.month} — {self.amount_due}"


<<<<<<< HEAD


class Group(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        related_name="groups"
    )
    students = models.ManyToManyField(
        Student,
        related_name="groups"
=======
# ─────────────────────────────────────────
# COINS
# ─────────────────────────────────────────

class CoinTransaction(models.Model):
    """
    Har bir coin o'zgarishi shu yerda log qilinadi (audit / tarix uchun).
    Student.coins maydoni har doim shu tranzaksiyalar yig'indisiga teng bo'lib turadi.
    """

    REASON_CHOICES = [
        ("exam_pass", "Imtihondan o'tdi"),
        ("homework_done", "Vazifa qilingan"),
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
        Teacher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="coin_transactions_given",
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default="manual")
    amount = models.IntegerField(default=0)  # musbat yoki manfiy bo'lishi mumkin
    note = models.CharField(max_length=255, blank=True)
    # Agar shu tranzaksiya ma'lum bir attendance yozuviga bog'liq bo'lsa
    attendance = models.ForeignKey(
        Attendance, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="coin_transactions",
>>>>>>> 1e950e7008cec6d3adea7146ad4b7f5bb4019d9d
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
<<<<<<< HEAD
        return self.name
=======
        return f"{self.student} — {self.get_reason_display()} — {self.amount}"


# ─────────────────────────────────────────
# MAGAZINE (DO'KON)
# ─────────────────────────────────────────

class Product(models.Model):
    name = models.CharField(max_length=200)
    image = models.URLField(max_length=500, blank=True)
    price_coins = models.IntegerField(default=0)  # nechta coin turadi
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)  # do'konda ko'rinadimi
    stock = models.IntegerField(null=True, blank=True)  # None = cheksiz
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.price_coins} coin"


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
    product_name = models.CharField(max_length=200)  # mahsulot o'chirilsa ham nomi qolishi uchun
    price_coins = models.IntegerField(default=0)  # xarid vaqtidagi narx
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} — {self.product_name} — {self.status}"
>>>>>>> 1e950e7008cec6d3adea7146ad4b7f5bb4019d9d
