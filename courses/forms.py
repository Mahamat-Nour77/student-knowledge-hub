from django import forms
from .models import Document, Comment, Course


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "description", "file"]


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "professor", "semester", "image"]