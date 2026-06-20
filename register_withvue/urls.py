from django.urls import path
from . import views

urlpatterns = [

    # ─────────────────────────────────────
    # MANAGER (eng yuqori daraja)
    # ─────────────────────────────────────
    path("managers/", views.get_managers),                          # GET  — barcha menejerlar
    path("managers/register/", views.manager_register),             # POST — yangi menejer
    path("managers/login/", views.manager_login),                   # POST — menejer login
    path("managers/update/<int:manager_id>/", views.update_manager),# PATCH
    path("managers/delete/<int:manager_id>/", views.delete_manager),# DELETE

    # ─────────────────────────────────────
    # COIN
    # ─────────────────────────────────────
    path("coins/", views.get_all_coin_balances),                            # GET  — hammaning balansi
    path("coins/add/", views.add_coin),                                     # POST — coin berish/olish
    path("coins/balance/<int:student_id>/", views.get_coin_balance),        # GET  — bitta student balansi
    path("coins/transactions/<int:student_id>/", views.get_coin_transactions),  # GET  — tarix
    path("coins/set/<int:student_id>/", views.set_coin_balance),            # PATCH — balansni to'g'ridan belgilash (faqat manager)
    path("coins/delete/<int:txn_id>/", views.delete_coin_transaction),      # DELETE — tranzaksiyani bekor qilish

    # ─────────────────────────────────────
    # TEACHERS
    # ─────────────────────────────────────
    path("teachers/", views.get_teachers),
    path("teachers/create/", views.create_teacher),
    path("teachers/delete/<int:teacher_id>/", views.delete_teacher),
    path("teachers/update/<int:teacher_id>/", views.update_teacher),
    path("teachers/reassign/", views.reassign_students),
    path("teachers/<int:teacher_id>/penalty-limit/", views.update_teacher_penalty_limit),

    # ─────────────────────────────────────
    # STAGE PRICES
    # ─────────────────────────────────────
    path("stage-prices/", views.get_stage_prices),
    path("stage-prices/update/<int:stage>/", views.update_stage_price),

    # ─────────────────────────────────────
    # STUDENTS
    # ─────────────────────────────────────
    path("students/", views.get_students),
    path("students/update/<int:student_id>/", views.update_student),
    path("register/", views.register_student),
    path("login/", views.login_student),

    # ─────────────────────────────────────
    # LESSONS
    # ─────────────────────────────────────
    path("lessons/", views.get_lessons),
    path("lessons/create/", views.create_lesson),

    # ─────────────────────────────────────
    # ATTENDANCE
    # ─────────────────────────────────────
    path("attendance/<int:lesson_id>/", views.get_attendance),
    path("attendance/update/<int:attendance_id>/", views.update_attendance),
    path("student-attendance/<int:student_id>/", views.get_student_attendance),
    path("monthly-absences/", views.get_monthly_absences),

    # ─────────────────────────────────────
    # PAYMENTS
    # ─────────────────────────────────────
    path("payments/<int:student_id>/", views.get_payments),
    path("payments/", views.get_all_payments),
    path("payments/generate/", views.generate_payments),
    path("payments/confirm/<int:payment_id>/", views.confirm_payment),
    path("payments/update/<int:payment_id>/", views.update_payment_amount),

    # ─────────────────────────────────────
    # STUDENT PENALTIES
    # ─────────────────────────────────────
    path("penalties/student/<int:student_id>/", views.get_student_penalties),
    path("penalties/by-teacher/<int:teacher_id>/", views.get_teacher_students_penalties),
    path("penalties/create/", views.create_student_penalty),
    path("penalties/<int:penalty_id>/delete/", views.delete_student_penalty),
]
