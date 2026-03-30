from django.urls import path
from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.conf.urls.static import static
from courses import views
from courses.views import CustomLoginView

urlpatterns = [

    # ── Cours ──
    path("",                                            views.course_list,       name="course_list"),
    path("course/<int:course_id>/",                     views.course_detail,     name="course_detail"),
    path("course/<int:course_id>/upload/",              views.upload_document,   name="upload_document"),
    path("add/",                                        views.add_course,        name="add_course"),

    # ── Auth ──
    path("signup/",                                     views.signup,            name="signup"),
    path("login/",                                      CustomLoginView.as_view(), name="login"),
path("logout/", LogoutView.as_view(), name="logout"),
    # ── Documents ──
    path("my-documents/",                               views.my_documents,      name="my_documents"),
    path("document/<int:document_id>/delete/",          views.delete_document,   name="delete_document"),

    # ── Commentaires ──
    path("comment/<int:comment_id>/delete/",            views.delete_comment,    name="delete_comment"),

    # ── Notes & Favoris ──
    path("document/<int:doc_id>/rate/",                 views.rate_document,     name="rate_document"),
    path("document/<int:document_id>/favorite/",        views.toggle_favorite,   name="toggle_favorite"),
    path("favorites/",                                  views.my_favorites,      name="my_favorites"),

    # ── Messages ──
    path("message/<int:document_id>/",                  views.add_message,       name="add_message"),

    # ── Espace Étudiant ──
    path("espace-etudiant/",                            views.student_space,     name="student_space"),

    # ── Quiz IA ──
    path("document/<int:document_id>/generate-quiz/",   views.generate_quiz,     name="generate_quiz"),
    path("quiz/<int:quiz_id>/take/",                    views.take_quiz,         name="take_quiz"),
    path("quiz/result/<int:result_id>/",                views.quiz_result,       name="quiz_result"),
    path("quiz/history/",                               views.quiz_history,      name="quiz_history"),
    path("document/<int:document_id>/quizzes/",         views.document_quizzes,  name="document_quizzes"),

    # ── Forum d'entraide ──
    path("forum/",                                      views.forum_list,        name="forum_list"),
    path("forum/poser/",                                views.forum_ask,         name="forum_ask"),
    path("forum/<int:question_id>/",                    views.forum_detail,      name="forum_detail"),
    path("forum/vote/<str:target>/<int:target_id>/",    views.forum_vote,        name="forum_vote"),
    path("forum/best/<int:answer_id>/",                 views.forum_mark_best,   name="forum_mark_best"),

    # ── Espace Ressources ──
    path("ressources/",                                 views.resources_list,    name="resources_list"),
    path("ressources/creer/",                           views.resource_create,   name="resource_create"),
    path("ressources/<int:resource_id>/",               views.resource_detail,   name="resource_detail"),
    path("ressources/<int:resource_id>/vote/",          views.resource_vote,     name="resource_vote"),

    # ── Conseils ──
    path("conseils/",                                   views.tips_list,         name="tips_list"),
    path("conseils/creer/",                             views.tip_create,        name="tip_create"),
    path("conseils/<int:tip_id>/like/",                 views.tip_like,          name="tip_like"),

    # ── Bibliothèque personnelle — Fonctionnalités IA ✅ NOUVEAU ──
    path("my-documents/<int:document_id>/quiz/",        views.personal_quiz,         name="personal_quiz"),
    path("my-documents/<int:document_id>/flashcards/",  views.personal_flashcards,   name="personal_flashcards"),
    path("my-documents/<int:document_id>/resume/",      views.personal_resume,       name="personal_resume"),
    path("my-documents/<int:document_id>/chat/",        views.personal_chat,         name="personal_chat"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)