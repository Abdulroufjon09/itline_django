from django.contrib import admin
from .models import (
    Manager,
    Student,
    Teacher,
    StagePrice,
    Lesson,
    Attendance,
    Payment,
    StudentPenalty,
    CoinTransaction,
    Group,
)


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "surname", "phone", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "phone")
    ordering = ("-created_at",)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "is_senior", "penalty_limit", "created_at")
    list_filter = ("is_senior",)
    search_fields = ("name", "phone")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "surname",
        "phone",
        "teacher",
        "stage",
        "schedule",
        "coin_balance",
        "is_admin",
        "is_excellence",
        "created_at",
    )
    list_filter = ("stage", "schedule", "is_admin", "is_excellence")
    search_fields = ("name", "surname", "phone")


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "amount", "reason", "given_by", "created_at")
    list_filter = ("reason",)
    search_fields = ("student__name", "student__phone")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(StagePrice)
class StagePriceAdmin(admin.ModelAdmin):
    list_display = ("id", "stage", "price")
    ordering = ("stage",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "teacher", "date")
    list_filter = ("teacher",)
    ordering = ("-date",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "lesson", "status")
    list_filter = ("status",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "month",
        "stage",
        "amount_due",
        "is_paid",
        "paid_at",
    )
    list_filter = ("is_paid", "month")
    search_fields = ("student__name",)


@admin.register(StudentPenalty)
class StudentPenaltyAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "reason", "amount", "given_by", "date")
    list_filter = ("reason",)
    search_fields = ("student__name",)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "get_teacher", "students_count")
    search_fields = ("name", "teacher__name")
    ordering = ("name",)

    def get_teacher(self, obj):
        return obj.teacher

    get_teacher.short_description = "O'qituvchi"

    def students_count(self, obj):
        return obj.students.count()

    students_count.short_description = "O'quvchilar soni"
