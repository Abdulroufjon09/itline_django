from django.contrib import admin

# Register your models here.

from .models import Student, Teacher, StagePrice, Lesson


admin.site.register(Student)
admin.site.register(Teacher)
admin.site.register(Lesson)
admin.site.register(StagePrice)
