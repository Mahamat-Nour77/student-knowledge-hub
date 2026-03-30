from django.test import TestCase

def test_course_creation(self):
    course = Course.objects.create(name="Test", professor="Prof")
    self.assertEqual(course.name, "Test")