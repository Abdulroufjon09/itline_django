from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("register_withvue", "0002_teacher_penalty_limit_studentpenalty"),
    ]

    operations = [
        # 1. Manager modeli
        migrations.CreateModel(
            name="Manager",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="Ism")),
                ("surname", models.CharField(blank=True, max_length=100, verbose_name="Familiya")),
                ("phone", models.CharField(max_length=20, unique=True, verbose_name="Telefon")),
                ("password", models.CharField(max_length=255, verbose_name="Parol (hash)")),
                ("is_active", models.BooleanField(default=True, verbose_name="Faol")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Menejer",
                "verbose_name_plural": "Menejerlar",
            },
        ),

        # 2. Student ga coin_balance maydoni
        migrations.AddField(
            model_name="student",
            name="coin_balance",
            field=models.IntegerField(default=0, verbose_name="Coin balansi"),
        ),

        # 3. CoinTransaction modeli
        migrations.CreateModel(
            name="CoinTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.IntegerField(verbose_name="Miqdor (+/-)")),
                ("reason", models.CharField(
                    choices=[
                        ("reward", "Mukofot"),
                        ("attendance", "Davomat uchun"),
                        ("homework", "Uy ishi uchun"),
                        ("behavior", "Xulq-atvor"),
                        ("penalty", "Jarima"),
                        ("manual", "Qo'lda kiritilgan"),
                        ("other", "Boshqa"),
                    ],
                    default="manual",
                    max_length=20,
                    verbose_name="Sabab",
                )),
                ("description", models.TextField(blank=True, verbose_name="Izoh")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coin_transactions",
                        to="register_withvue.student",
                        verbose_name="O'quvchi",
                    ),
                ),
                (
                    "given_by_teacher",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="coin_transactions_given",
                        to="register_withvue.teacher",
                        verbose_name="Bergan o'qituvchi",
                    ),
                ),
                (
                    "given_by_manager",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="coin_transactions_given",
                        to="register_withvue.manager",
                        verbose_name="Bergan menejer",
                    ),
                ),
            ],
            options={
                "verbose_name": "Coin tranzaksiyasi",
                "verbose_name_plural": "Coin tranzaksiyalari",
                "ordering": ["-created_at"],
            },
        ),
    ]
