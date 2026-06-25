from rest_framework import serializers
from .models import Student, Group


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["id","name", "surname", "phone", "teacher"]


class GroupSerializer(serializers.ModelSerializer):
    students_count = serializers.SerializerMethodField()
    students = StudentSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = "__all__"

    def get_students_count(self, obj):
        return obj.students.count()
