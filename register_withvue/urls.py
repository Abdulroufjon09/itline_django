from django.urls import path
from . import views

urlpatterns = [
    # ─────────────────────────────────────
    # MANAGER
    # ─────────────────────────────────────
    path("managers/", views.get_managers),
    path("managers/register/", views.manager_register),
    path("managers/login/", views.manager_login),
    path("managers/update/<int:manager_id>/", views.update_manager),
    path("managers/delete/<int:manager_id>/", views.delete_manager),
    # ─────────────────────────────────────
    # TEACHERS
    # ─────────────────────────────────────
    path("teachers/", views.get_teachers),
    path("teachers/create/", views.create_teacher),
    path("teachers/reassign/", views.reassign_students),
    path("teachers/update/<int:teacher_id>/", views.update_teacher),
    path("teachers/delete/<int:teacher_id>/", views.delete_teacher),
    path(
        "teachers/<int:teacher_id>/penalty-limit/", views.update_teacher_penalty_limit
    ),
    # ─────────────────────────────────────
    # STUDENTS
    # ─────────────────────────────────────
    path("students/", views.get_students),
    path("students/update/<int:student_id>/", views.update_student),
    path("register/", views.register_student),
    path("login/", views.login_student),
    # ─────────────────────────────────────
    # STAGE PRICES
    # ─────────────────────────────────────
    path("stage-prices/", views.get_stage_prices),
    path("stage-prices/update/<int:stage>/", views.update_stage_price),
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
    path("payments/", views.get_all_payments),
    path("payments/generate/", views.generate_payments),
    path("payments/confirm/<int:payment_id>/", views.confirm_payment),
    path("payments/update/<int:payment_id>/", views.update_payment_amount),
    path("payments/<int:student_id>/", views.get_payments),
    # ─────────────────────────────────────
    # STUDENT PENALTIES
    # ─────────────────────────────────────
    path("penalties/create/", views.create_student_penalty),
    path("penalties/student/<int:student_id>/", views.get_student_penalties),
    path(
        "penalties/by-teacher/<int:teacher_id>/", views.get_teacher_students_penalties
    ),
    path("penalties/<int:penalty_id>/delete/", views.delete_student_penalty),
    # ─────────────────────────────────────
    # COINS
    # ─────────────────────────────────────
    path("coins/", views.get_all_coin_balances),
    path("coins/add/", views.add_coin),
    path("coins/give/", views.give_manual_coins),
    path("coins/set/<int:student_id>/", views.set_coin_balance),
    path("coins/balance/<int:student_id>/", views.get_coin_balance),
    path("coins/student/<int:student_id>/", views.get_student_coins),
    path("coins/transactions/<int:student_id>/", views.get_coin_transactions),
    path("coins/delete/<int:txn_id>/", views.delete_coin_transaction),
    path("leaderboard/", views.get_leaderboard),
    # ─────────────────────────────────────
    # PRODUCTS (MAGAZINE)
    # ─────────────────────────────────────
    path("products/", views.get_products),
    path("products/all/", views.get_all_products),
    path("products/create/", views.create_product),
    path("products/update/<int:product_id>/", views.update_product),
    path("products/delete/<int:product_id>/", views.delete_product),
    # ─────────────────────────────────────
    # ORDERS
    # ─────────────────────────────────────
    path("orders/", views.get_all_orders),
    path("orders/create/", views.create_order),
    path("orders/resolve/<int:order_id>/", views.resolve_order),
    path("orders/student/<int:student_id>/", views.get_student_orders),
    # ─────────────────────────────────────
    # GROUPS
    # ─────────────────────────────────────
    path("groups/", views.get_groups),
    path("groups/create/", views.create_group),
    path("groups/update/<int:group_id>/", views.update_group),
    path("groups/delete/<int:group_id>/", views.delete_group),
    path("groups/<int:group_id>/", views.get_group),
]
