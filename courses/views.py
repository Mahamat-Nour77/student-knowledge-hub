from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.utils import timezone

from .models import (
    Course, Document, Comment, Rating, Favorite, Message,
    Quiz, QuizQuestion, QuizResult,
    Question, Answer, Vote,
    Resource, ResourceVote, Flashcard, Tip,
)
from .forms import CommentForm, DocumentForm, CourseForm

import google.generativeai as genai
import pdfplumber
import json
import os

# ══════════════════════════════════════════════════════════════════
#  CONFIG GEMINI
# ══════════════════════════════════════════════════════════════════

GEMINI_API_KEY = "AIzaSyC0bQaKi3SQxDbJpqswgvPXSP4q08PpesA"

CATEGORY_CHOICES = [
    ("cours",   "Cours"),
    ("td",      "TD / TP"),
    ("resume",  "Résumé"),
    ("examen",  "Examen / Annale"),
    ("autre",   "Autre"),
]


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def _get_model():
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-1.5-flash")


def _extract_pdf_text(file_path: str, max_chars: int = 8000) -> str:
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
                if len(text) >= max_chars:
                    break
    except Exception:
        pass
    return text[:max_chars]


def _generate_quiz_with_groq(text: str, num_questions: int = 10) -> list:
    """Génère un quiz QCM via Gemini."""
    model = _get_model()
    prompt = f"""Tu es un professeur expert. À partir du texte suivant, génère exactement {num_questions} questions QCM en français.

TEXTE :
\"\"\"
{text}
\"\"\"

RÈGLES STRICTES :
- Chaque question a exactement 4 choix (A, B, C, D)
- Une seule bonne réponse par question
- Les mauvais choix doivent être plausibles mais clairement incorrects
- Ajoute une courte explication de la bonne réponse
- Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après
- Format exact :
[
  {{
    "question": "...",
    "choices": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "answer": "A",
    "explanation": "..."
  }}
]"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _ai_answer_question(question) -> str:
    """Génère une réponse IA pour une question du forum via Gemini."""
    model = _get_model()
    prompt = f"""Tu es un assistant pédagogique pour étudiants. Réponds à cette question de manière claire et structurée en français.

Matière : {question.get_subject_display()}
Question : {question.title}
Détails : {question.content}

Donne une réponse complète avec des exemples si possible. Sois pédagogique."""
    response = model.generate_content(prompt)
    return response.text.strip()


def _generate_flashcards(text: str) -> list:
    """Génère des flashcards via Gemini."""
    model = _get_model()
    prompt = f"""À partir du texte suivant, génère 10 flashcards pédagogiques en français.
Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après :
[{{"question": "...", "answer": "..."}}]

TEXTE :
{text}"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _generate_resume(text: str) -> str:
    """Génère un résumé via Gemini."""
    model = _get_model()
    prompt = f"""Fais un résumé structuré et clair de ce texte en français.
Utilise des titres, sous-titres et points clés. Sois concis mais complet.

TEXTE :
{text}"""
    response = model.generate_content(prompt)
    return response.text.strip()


# ══════════════════════════════════════════════════════════════════
#  COURS & DOCUMENTS
# ══════════════════════════════════════════════════════════════════

@login_required
def student_space(request):
    return render(request, "courses/student_space.html")


@login_required
def course_list(request):
    courses = Course.objects.all().order_by("id")
    query = request.GET.get("q")
    if query:
        courses = courses.filter(name__icontains=query)
    paginator = Paginator(courses, 6)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "courses/course_list.html", {
        "courses": page_obj, "page_obj": page_obj,
        "total_courses": Course.objects.count(),
        "total_documents": Document.objects.count(),
        "total_comments": Comment.objects.count(),
    })


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    documents = course.document_set.annotate(avg_rating=Avg("rating__score"))
    form = CommentForm()
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid() and request.user.is_authenticated:
            comment = form.save(commit=False)
            comment.user = request.user
            comment.save()
            return redirect("course_detail", course_id=course.id)
    return render(request, "courses/course_detail.html", {
        "course": course, "documents": documents,
        "comments": Comment.objects.filter(document__course=course),
        "form": form,
    })


@login_required
def delete_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    if document.uploaded_by != request.user:
        return redirect("my_documents")
    document.delete()
    return redirect("my_documents")


@login_required
def add_course(request):
    if request.method == "POST":
        name        = request.POST.get("name", "").strip()
        professor   = request.POST.get("professor", "").strip()
        filiere     = request.POST.get("filiere", "")
        semester    = request.POST.get("semester", "")
        image       = request.FILES.get("image")
        pdf_file    = request.FILES.get("pdf_file")

        if not name:
            messages.error(request, "Le nom du cours est obligatoire.")
            return redirect("add_course")

        semester_display = f"{filiere} — {semester}" if filiere and semester else (filiere or semester or "")
        course = Course(name=name, professor=professor, semester=semester_display)
        if image:
            course.image = image
        course.save()

        if pdf_file:
            Document.objects.create(
                title=f"{name} — Document principal",
                description=f"Document principal du cours {name}",
                file=pdf_file,
                course=course,
                uploaded_by=request.user,
            )
            messages.success(request, f"✅ Cours « {name} » et document PDF ajoutés !")
        else:
            messages.success(request, f"✅ Cours « {name} » ajouté avec succès !")

        return redirect("course_detail", course_id=course.id)

    return render(request, "courses/add_course.html")


@login_required
def upload_document(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.course = course
            document.uploaded_by = request.user
            document.save()

            is_pdf = document.file.name.lower().endswith(".pdf")
            if is_pdf:
                text = _extract_pdf_text(document.file.path)
                if len(text.strip()) < 100:
                    messages.warning(request, "Document uploadé ✅ mais le PDF ne contient pas assez de texte.")
                    return redirect("course_detail", course_id=course.id)
                try:
                    num_questions = int(request.POST.get("num_questions", 10))
                    questions_data = _generate_quiz_with_groq(text, num_questions)
                    quiz = Quiz.objects.create(
                        document=document, created_by=request.user,
                        mode="qcm", num_questions=len(questions_data),
                        title=f"Quiz — {document.title}"
                    )
                    for i, q in enumerate(questions_data):
                        QuizQuestion.objects.create(
                            quiz=quiz, order=i + 1,
                            question=q["question"],
                            choice_a=q["choices"].get("A", ""),
                            choice_b=q["choices"].get("B", ""),
                            choice_c=q["choices"].get("C", ""),
                            choice_d=q["choices"].get("D", ""),
                            answer=q["answer"].upper(),
                            explanation=q.get("explanation", "")
                        )
                    messages.success(request, "✅ Document uploadé et quiz généré automatiquement !")
                    return redirect("take_quiz", quiz_id=quiz.id)
                except Exception as e:
                    messages.error(request, f"Document uploadé ✅ mais erreur quiz : {e}")
                    return redirect("course_detail", course_id=course.id)
            else:
                messages.success(request, "✅ Document uploadé !")
                return redirect("course_detail", course_id=course.id)
    else:
        form = DocumentForm()
    return render(request, "courses/upload_document.html", {"form": form, "course": course})


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user == request.user:
        comment.delete()
    return redirect("course_detail", course_id=comment.document.course.id)


@login_required
def my_documents(request):
    category_filter = request.GET.get("category")
    qs = Document.objects.filter(uploaded_by=request.user)
    if category_filter:
        qs = qs.filter(description__icontains=category_filter)
    return render(request, "courses/my_documents.html", {
        "documents": qs,
        "total": qs.count(),
        "category_choices": CATEGORY_CHOICES,
        "current_category": category_filter,
    })


# ══════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════

def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Bienvenue sur Student Knowledge Hub 🎓")
            return redirect("course_list")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Bienvenue sur Student Knowledge Hub 🎓")
        return response


# ══════════════════════════════════════════════════════════════════
#  FAVORIS & NOTES
# ══════════════════════════════════════════════════════════════════

@login_required
def rate_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id)
    score = request.POST.get(f"score_{doc_id}")
    if score:
        rating, created = Rating.objects.get_or_create(
            document=document, user=request.user, defaults={"score": int(score)}
        )
        if not created:
            rating.score = int(score)
            rating.save()
    return redirect("course_detail", course_id=document.course.id)


@login_required
def toggle_favorite(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    fav, created = Favorite.objects.get_or_create(user=request.user, document=document)
    if not created:
        fav.delete()
        return JsonResponse({"status": "removed"})
    return JsonResponse({"status": "added"})


@login_required
def my_favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related("document", "document__course")
    sort = request.GET.get("sort")
    if sort == "rating":
        favorites = favorites.annotate(avg=Avg("document__rating__score")).order_by("-avg")
    elif sort == "recent":
        favorites = favorites.order_by("-document__upload_date")
    return render(request, "courses/my_favorites.html", {
        "favorites": favorites,
        "total_favorites": favorites.count(),
        "total_courses": favorites.values("document__course").distinct().count(),
    })


@login_required
def add_message(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    if request.method == "POST" and request.POST.get("content"):
        Message.objects.create(document=document, user=request.user, content=request.POST["content"])
    return redirect("course_detail", course_id=document.course.id)


# ══════════════════════════════════════════════════════════════════
#  QUIZ IA
# ══════════════════════════════════════════════════════════════════

@login_required
def generate_quiz(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    if request.method == "POST":
        num_q = max(5, min(int(request.POST.get("num_questions", 10)), 20))
        text = _extract_pdf_text(document.file.path)
        if len(text.strip()) < 100:
            messages.error(request, "Le document ne contient pas assez de texte lisible.")
            return redirect("course_detail", course_id=document.course.id)
        try:
            questions_data = _generate_quiz_with_groq(text, num_q)
        except Exception as e:
            messages.error(request, f"Erreur lors de la génération du quiz : {e}")
            return redirect("course_detail", course_id=document.course.id)
        quiz = Quiz.objects.create(
            document=document, created_by=request.user,
            mode="qcm", num_questions=len(questions_data),
            title=f"Quiz — {document.title}"
        )
        for i, q in enumerate(questions_data):
            QuizQuestion.objects.create(
                quiz=quiz, order=i + 1,
                question=q["question"],
                choice_a=q["choices"].get("A", ""),
                choice_b=q["choices"].get("B", ""),
                choice_c=q["choices"].get("C", ""),
                choice_d=q["choices"].get("D", ""),
                answer=q["answer"].upper(),
                explanation=q.get("explanation", "")
            )
        return redirect("take_quiz", quiz_id=quiz.id)
    return render(request, "courses/generate_quiz.html", {"document": document})


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    if request.method == "POST":
        answers = {}
        score = 0
        for q in questions:
            user_answer = request.POST.get(f"q_{q.id}", "")
            answers[str(q.id)] = user_answer
            if user_answer.upper() == q.answer.upper():
                score += 1
        result = QuizResult.objects.create(
            quiz=quiz, user=request.user,
            score=score, total=questions.count(), answers=answers
        )
        return redirect("quiz_result", result_id=result.id)
    return render(request, "courses/take_quiz.html", {"quiz": quiz, "questions": questions})


@login_required
def quiz_result(request, result_id):
    result = get_object_or_404(QuizResult, id=result_id, user=request.user)
    questions_with_answers = []
    for q in result.quiz.questions.all():
        user_ans = result.answers.get(str(q.id), "")
        questions_with_answers.append({
            "question": q,
            "user_answer": user_ans,
            "is_correct": user_ans.upper() == q.answer.upper(),
        })
    return render(request, "courses/quiz_result.html", {
        "result": result,
        "questions_with_answers": questions_with_answers,
    })


@login_required
def quiz_history(request):
    results = QuizResult.objects.filter(user=request.user).select_related(
        "quiz", "quiz__document", "quiz__document__course"
    ).order_by("-completed_at")

    best_score = 0
    if results:
        best_score = max(r.percentage() for r in results)

    courses = Course.objects.all().order_by("name")
    courses_with_docs = []
    for course in courses:
        docs = list(Document.objects.filter(course=course))
        courses_with_docs.append({"course": course, "documents": docs})
    courses_with_docs.sort(key=lambda x: len(x["documents"]), reverse=True)

    return render(request, "courses/quiz_history.html", {
        "results": results,
        "best_score": best_score,
        "courses_with_docs": courses_with_docs,
    })


@login_required
def document_quizzes(request, document_id):
    document = get_object_or_404(Document, id=document_id)
    return render(request, "courses/document_quizzes.html", {
        "document": document,
        "quizzes": Quiz.objects.filter(document=document).order_by("-created_at"),
    })


# ══════════════════════════════════════════════════════════════════
#  FORUM D'ENTRAIDE
# ══════════════════════════════════════════════════════════════════

@login_required
def forum_list(request):
    qs = Question.objects.annotate(nb_answers=Count("answers"), nb_votes=Sum("votes__value"))
    if s := request.GET.get("subject"):
        qs = qs.filter(subject=s)
    if st := request.GET.get("status"):
        qs = qs.filter(is_resolved=(st == "resolved"))
    if q := request.GET.get("q"):
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
    sort = request.GET.get("sort", "recent")
    qs = qs.order_by("-nb_votes" if sort == "votes" else "-nb_answers" if sort == "answers" else "-created_at")
    paginator = Paginator(qs, 10)
    return render(request, "courses/forum_list.html", {
        "questions": paginator.get_page(request.GET.get("page")),
        "page_obj": paginator.get_page(request.GET.get("page")),
        "subject_choices": Question.SUBJECT_CHOICES,
        "current_subject": request.GET.get("subject"),
        "current_status": request.GET.get("status"),
        "current_sort": sort,
        "total_questions": Question.objects.count(),
        "total_resolved": Question.objects.filter(is_resolved=True).count(),
    })


@login_required
def forum_ask(request):
    if request.method == "POST":
        title   = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        if not title or not content:
            messages.error(request, "Titre et contenu sont obligatoires.")
            return redirect("forum_ask")
        course_id = request.POST.get("course_id")
        course = Course.objects.filter(id=course_id).first() if course_id else None
        question = Question.objects.create(
            author=request.user, title=title, content=content,
            subject=request.POST.get("subject", "autre"), course=course
        )
        messages.success(request, "Question publiée ! 🙌")
        return redirect("forum_detail", question_id=question.id)
    return render(request, "courses/forum_ask.html", {
        "subject_choices": Question.SUBJECT_CHOICES,
        "courses": Course.objects.all(),
    })


@login_required
def forum_detail(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    Question.objects.filter(id=question_id).update(views=question.views + 1)

    if (
        question.answers.count() == 0
        and question.created_at < timezone.now() - timezone.timedelta(hours=24)
        and not question.answers.filter(is_ai=True).exists()
    ):
        try:
            ai_user, _ = User.objects.get_or_create(
                username="AI_Assistant", defaults={"first_name": "Assistant IA"}
            )
            Answer.objects.create(
                question=question, author=ai_user,
                content=_ai_answer_question(question), is_ai=True
            )
        except Exception:
            pass

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            Answer.objects.create(question=question, author=request.user, content=content)
            messages.success(request, "Réponse publiée !")
            return redirect("forum_detail", question_id=question.id)

    user_vote = Vote.objects.filter(user=request.user, question=question).first()
    return render(request, "courses/forum_detail.html", {
        "question": question,
        "answers": question.answers.all(),
        "user_vote": user_vote,
    })


@login_required
def forum_vote(request, target, target_id):
    value = int(request.POST.get("value", 1))
    if target == "question":
        obj = get_object_or_404(Question, id=target_id)
        vote, created = Vote.objects.get_or_create(user=request.user, question=obj, defaults={"value": value})
    elif target == "answer":
        obj = get_object_or_404(Answer, id=target_id)
        vote, created = Vote.objects.get_or_create(user=request.user, answer=obj, defaults={"value": value})
    else:
        return JsonResponse({"error": "invalide"}, status=400)
    if not created:
        if vote.value == value:
            vote.delete()
            return JsonResponse({"status": "removed", "count": obj.vote_count()})
        vote.value = value
        vote.save()
    return JsonResponse({"status": "ok", "count": obj.vote_count()})


@login_required
def forum_mark_best(request, answer_id):
    answer = get_object_or_404(Answer, id=answer_id)
    if answer.question.author != request.user:
        return JsonResponse({"error": "Non autorisé"}, status=403)
    answer.question.answers.update(is_best=False)
    answer.is_best = True
    answer.save()
    answer.question.is_resolved = True
    answer.question.save()
    return JsonResponse({"status": "ok"})


# ══════════════════════════════════════════════════════════════════
#  ESPACE RESSOURCES
# ══════════════════════════════════════════════════════════════════

@login_required
def resources_list(request):
    qs = Resource.objects.select_related("author", "course")
    if t := request.GET.get("type"):
        qs = qs.filter(type=t)
    if s := request.GET.get("subject"):
        qs = qs.filter(subject=s)
    if q := request.GET.get("q"):
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
    sort = request.GET.get("sort", "recent")
    if sort == "popular":
        qs = qs.annotate(total_votes=Sum("resource_votes__value")).order_by("-total_votes")
    else:
        qs = qs.order_by("-created_at")
    paginator = Paginator(qs, 9)
    return render(request, "courses/resources_list.html", {
        "resources": paginator.get_page(request.GET.get("page")),
        "page_obj": paginator.get_page(request.GET.get("page")),
        "tips": Tip.objects.order_by("-created_at")[:5],
        "type_choices": Resource.TYPE_CHOICES,
        "subject_choices": Resource.SUBJECT_CHOICES,
        "current_type": request.GET.get("type"),
        "current_subject": request.GET.get("subject"),
        "current_sort": sort,
    })


@login_required
def resource_create(request):
    if request.method == "POST":
        title   = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        rtype   = request.POST.get("type", "resume")
        if not title or not content:
            messages.error(request, "Titre et contenu sont obligatoires.")
            return redirect("resource_create")
        course_id = request.POST.get("course_id")
        course = Course.objects.filter(id=course_id).first() if course_id else None
        resource = Resource.objects.create(
            author=request.user, type=rtype, title=title, content=content,
            subject=request.POST.get("subject", "autre"), course=course
        )
        if rtype == "flashcard":
            for i, block in enumerate(request.POST.get("flashcards_data", "").split("---")):
                lines = block.strip().splitlines()
                q_line = next((l for l in lines if l.startswith("Q:")), None)
                a_line = next((l for l in lines if l.startswith("R:")), None)
                if q_line and a_line:
                    Flashcard.objects.create(
                        resource=resource, order=i,
                        question=q_line[2:].strip(), answer=a_line[2:].strip()
                    )
        messages.success(request, "Ressource partagée 🎉")
        return redirect("resource_detail", resource_id=resource.id)
    return render(request, "courses/resource_create.html", {
        "type_choices": Resource.TYPE_CHOICES,
        "subject_choices": Resource.SUBJECT_CHOICES,
        "courses": Course.objects.all(),
    })


@login_required
def resource_detail(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    return render(request, "courses/resource_detail.html", {
        "resource": resource,
        "flashcards": resource.flashcards.all() if resource.type == "flashcard" else [],
        "user_vote": ResourceVote.objects.filter(user=request.user, resource=resource).first(),
        "vote_count": resource.vote_count(),
    })


@login_required
def resource_vote(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)
    value = int(request.POST.get("value", 1))
    vote, created = ResourceVote.objects.get_or_create(
        user=request.user, resource=resource, defaults={"value": value}
    )
    if not created:
        if vote.value == value:
            vote.delete()
            return JsonResponse({"status": "removed", "count": resource.vote_count()})
        vote.value = value
        vote.save()
    return JsonResponse({"status": "ok", "count": resource.vote_count()})


@login_required
def tips_list(request):
    category = request.GET.get("category")
    qs = Tip.objects.all()
    if category:
        qs = qs.filter(category=category)
    return render(request, "courses/tips_list.html", {
        "tips": qs,
        "category_choices": Tip.CATEGORY_CHOICES,
        "current_category": category,
    })


@login_required
def tip_like(request, tip_id):
    tip = get_object_or_404(Tip, id=tip_id)
    if request.user in tip.likes.all():
        tip.likes.remove(request.user)
        status = "removed"
    else:
        tip.likes.add(request.user)
        status = "added"
    return JsonResponse({"status": status, "count": tip.like_count()})


@login_required
def tip_create(request):
    if request.method == "POST":
        title   = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        if not title or not content:
            messages.error(request, "Titre et contenu sont obligatoires.")
            return redirect("tip_create")
        Tip.objects.create(
            author=request.user, title=title, content=content,
            category=request.POST.get("category", "autre")
        )
        messages.success(request, "Conseil partagé 💡 Merci !")
        return redirect("tips_list")
    return render(request, "courses/tip_create.html", {"category_choices": Tip.CATEGORY_CHOICES})


# ══════════════════════════════════════════════════════════════════
#  BIBLIOTHÈQUE PERSONNELLE — FONCTIONNALITÉS IA (Gemini)
# ══════════════════════════════════════════════════════════════════

@login_required
def personal_quiz(request, document_id):
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    if request.method == "POST":
        num_q = max(5, min(int(request.POST.get("num_questions", 10)), 20))
        text = _extract_pdf_text(document.file.path)
        if len(text.strip()) < 100:
            messages.error(request, "Le PDF ne contient pas assez de texte lisible.")
            return redirect("my_documents")
        try:
            questions_data = _generate_quiz_with_groq(text, num_q)
            quiz = Quiz.objects.create(
                document=document, created_by=request.user,
                mode="qcm", num_questions=len(questions_data),
                title=f"Quiz — {document.title}"
            )
            for i, q in enumerate(questions_data):
                QuizQuestion.objects.create(
                    quiz=quiz, order=i + 1,
                    question=q["question"],
                    choice_a=q["choices"].get("A", ""),
                    choice_b=q["choices"].get("B", ""),
                    choice_c=q["choices"].get("C", ""),
                    choice_d=q["choices"].get("D", ""),
                    answer=q["answer"].upper(),
                    explanation=q.get("explanation", "")
                )
            return redirect("take_quiz", quiz_id=quiz.id)
        except Exception as e:
            messages.error(request, f"Erreur lors de la génération : {e}")
            return redirect("my_documents")
    return render(request, "courses/personal_quiz.html", {"document": document})


@login_required
def personal_flashcards(request, document_id):
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    flashcards = []
    error = None
    if request.method == "POST":
        text = _extract_pdf_text(document.file.path)
        if len(text.strip()) < 100:
            messages.error(request, "Le PDF ne contient pas assez de texte.")
            return redirect("my_documents")
        try:
            flashcards = _generate_flashcards(text)
        except Exception as e:
            error = str(e)
    return render(request, "courses/personal_flashcards.html", {
        "document": document, "flashcards": flashcards, "error": error
    })


@login_required
def personal_resume(request, document_id):
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    resume = None
    error = None
    if request.method == "POST":
        text = _extract_pdf_text(document.file.path)
        if len(text.strip()) < 100:
            messages.error(request, "Le PDF ne contient pas assez de texte.")
            return redirect("my_documents")
        try:
            resume = _generate_resume(text)
        except Exception as e:
            error = str(e)
    return render(request, "courses/personal_resume.html", {
        "document": document, "resume": resume, "error": error
    })


@login_required
def personal_chat(request, document_id):
    document = get_object_or_404(Document, id=document_id, uploaded_by=request.user)
    answer = None
    question_text = None
    error = None
    if request.method == "POST":
        question_text = request.POST.get("question", "").strip()
        if question_text:
            text = _extract_pdf_text(document.file.path)
            try:
                model = _get_model()
                prompt = f"""Tu es un assistant pédagogique. Réponds à la question en te basant sur le document.

DOCUMENT :
{text}

QUESTION : {question_text}"""
                response = model.generate_content(prompt)
                answer = response.text.strip()
            except Exception as e:
                error = str(e)
    return render(request, "courses/personal_chat.html", {
        "document": document, "answer": answer, "question": question_text, "error": error
    })