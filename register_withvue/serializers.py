from rest_framework import serializers
from .models import Student, Group


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
<<<<<<< HEAD
        fields = ['name', 'surname', 'phone', 'teacher']

class GroupSerializer(serializers.ModelSerializer):
    students_count = serializers.SerializerMethodField()
    students = StudentSerializer(many=True, read_only=True)
    class Meta:
        model = Group
        fields = "__all__"

    def get_students_count(self, obj):
        return obj.students.count()
=======
        fields = ["name", "surname", "phone", "teacher"]
>>>>>>> 1e950e7008cec6d3adea7146ad4b7f5bb4019d9d
