from rest_framework import serializers
from .models import Student, Teacher, Group


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ["id", "name", "phone"]


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["id", "name", "surname", "phone", "stage"]


class GroupSerializer(serializers.ModelSerializer):
    teacher = TeacherSerializer(read_only=True)
    students = StudentSerializer(many=True, read_only=True)
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "teacher", "students", "students_count", "lesson_time"]

    def get_students_count(self, obj):
        return obj.students.count()
