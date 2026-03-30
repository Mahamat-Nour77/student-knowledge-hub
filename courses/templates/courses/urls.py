# ══════════════════════════════════════════════════════════════════
#  AJOUTE CES LIGNES DANS ton courses/urls.py (dans urlpatterns)
# ══════════════════════════════════════════════════════════════════

# -- Import à ajouter en haut --
# from .views import (generate_quiz, take_quiz, quiz_result,
#                     quiz_history, document_quizzes)

# -- Paths à ajouter dans urlpatterns --
# path("document/<int:document_id>/generate-quiz/", views.generate_quiz, name="generate_quiz"),
# path("quiz/<int:quiz_id>/take/",                  views.take_quiz,      name="take_quiz"),
# path("quiz/result/<int:result_id>/",              views.quiz_result,    name="quiz_result"),
# path("quiz/history/",                             views.quiz_history,   name="quiz_history"),
# path("document/<int:document_id>/quizzes/",       views.document_quizzes, name="document_quizzes"),


# ══════════════════════════════════════════════════════════════════
#  FICHIER COMPLET PRÊT À REMPLACER ton courses/urls.py
# ══════════════════════════════════════════════════════════════════
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import CustomLoginView

urlpatterns = [
    # ── Cours ──
    path("",                                            views.course_list,       name="course_list"),
    path("course/<int:course_id>/",                     views.course_detail,     name="course_detail"),
    path("course/<int:course_id>/upload/",              views.upload_document,   name="upload_document"),
    path("add/",                                        views.add_course,        name="add_course"),

    # ── Auth ──
    path("signup/",                                     views.signup,            name="signup"),
    path("login/",                                      CustomLoginView.as_view(), name="login"),

    # ── Documents ──
    path("my-documents/",                               views.my_documents,      name="my_documents"),
    path("document/<int:document_id>/delete/",          views.delete_document,   name="delete_document"),

    # ── Commentaires ──
    path("comment/<int:comment_id>/delete/",            views.delete_comment,    name="delete_comment"),

    # ── Notes ──
    path("document/<int:doc_id>/rate/",                 views.rate_document,     name="rate_document"),

    # ── Dépenses ──
    path("expenses/",                                   views.expenses,          name="expenses"),

    # ── Favoris ──
    path("document/<int:document_id>/favorite/",        views.toggle_favorite,   name="toggle_favorite"),
    path("favorites/",                                  views.my_favorites,      name="my_favorites"),

    # ── Social ──
    path("add-friend/",                                 views.add_friend,        name="add_friend"),
    path("message/<int:document_id>/",                  views.add_message,       name="add_message"),

    # ── QUIZ IA ──
    path("document/<int:document_id>/generate-quiz/",   views.generate_quiz,     name="generate_quiz"),
    path("quiz/<int:quiz_id>/take/",                    views.take_quiz,         name="take_quiz"),
    path("quiz/result/<int:result_id>/",                views.quiz_result,       name="quiz_result"),
    path("quiz/history/",                               views.quiz_history,      name="quiz_history"),
    path("document/<int:document_id>/quizzes/",         views.document_quizzes,  name="document_quizzes"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)