from django.db import models
from django.contrib.auth.models import User


# ══════════════════════════════════════
#  EXISTANTS
# ══════════════════════════════════════

class Course(models.Model):
    name = models.CharField(max_length=200)
    professor = models.CharField(max_length=200)
    semester = models.CharField(max_length=50)
    image = models.ImageField(upload_to="courses/", blank=True, null=True)

    def __str__(self):
        return self.name


class Rating(models.Model):
    document = models.ForeignKey("Document", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField()

    def __str__(self):
        return f"{self.user.username} - {self.score}"


class Document(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    file = models.FileField(upload_to="documents/")
    upload_date = models.DateTimeField(auto_now_add=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    @property
    def is_pdf(self):
        return self.file.name.lower().endswith('.pdf')

    @property
    def extension(self):
        return self.file.name.split('.')[-1].upper()
class Comment(models.Model):
    document = models.ForeignKey("Document", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.document.title}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey("Document", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "document")

    def __str__(self):
        return f"{self.user.username} ❤️ {self.document.title}"


class Friend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friends")
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_of")

    def __str__(self):
        return f"{self.user.username} ↔ {self.friend.username}"


class Message(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.document.title}"


# ══════════════════════════════════════
#  QUIZ IA
# ══════════════════════════════════════

class Quiz(models.Model):
    MODE_CHOICES = [
        ("qcm",       "QCM"),
        ("exam",      "Examen blanc"),
        ("flashcard", "Flash cards"),
    ]
    document      = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="quizzes")
    created_by    = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at    = models.DateTimeField(auto_now_add=True)
    mode          = models.CharField(max_length=20, choices=MODE_CHOICES, default="qcm")
    num_questions = models.IntegerField(default=10)
    title         = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"Quiz — {self.document.title} ({self.mode})"

    def avg_score(self):
        results = self.results.all()
        if not results:
            return None
        return round(sum(r.score for r in results) / len(results), 1)


class QuizQuestion(models.Model):
    quiz        = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    order       = models.IntegerField(default=0)
    question    = models.TextField()
    choice_a    = models.CharField(max_length=400)
    choice_b    = models.CharField(max_length=400)
    choice_c    = models.CharField(max_length=400)
    choice_d    = models.CharField(max_length=400)
    answer      = models.CharField(max_length=1)
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Q{self.order} — {self.quiz}"


class QuizResult(models.Model):
    quiz         = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="results")
    user         = models.ForeignKey(User, on_delete=models.CASCADE)
    score        = models.IntegerField()
    total        = models.IntegerField()
    answers      = models.JSONField(default=dict)
    completed_at = models.DateTimeField(auto_now_add=True)

    def percentage(self):
        return round((self.score / self.total) * 100) if self.total else 0

    def __str__(self):
        return f"{self.user.username} — {self.score}/{self.total}"


# ══════════════════════════════════════
#  FORUM D'ENTRAIDE
# ══════════════════════════════════════

class Question(models.Model):
    """Question posée par un étudiant sur le forum."""
    SUBJECT_CHOICES = [
        ("maths",      "Mathématiques"),
        ("physique",   "Physique"),
        ("info",       "Informatique"),
        ("histoire",   "Histoire"),
        ("langue",     "Langues"),
        ("autre",      "Autre"),
    ]
    author      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="questions")
    course      = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions")
    subject     = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default="autre")
    title       = models.CharField(max_length=300)
    content     = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    is_resolved = models.BooleanField(default=False)
    views       = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def vote_count(self):
        return self.votes.aggregate(total=models.Sum("value"))["total"] or 0

    def answer_count(self):
        return self.answers.count()


class Answer(models.Model):
    """Réponse à une question du forum."""
    question   = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="answers")
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_best    = models.BooleanField(default=False)  # meilleure réponse sélectionnée
    is_ai      = models.BooleanField(default=False)  # réponse générée par Claude

    class Meta:
        ordering = ["-is_best", "-created_at"]

    def __str__(self):
        return f"Réponse de {self.author.username} à '{self.question.title}'"

    def vote_count(self):
        return self.votes.aggregate(total=models.Sum("value"))["total"] or 0


class Vote(models.Model):
    """Vote +1 / -1 sur une question ou une réponse."""
    VALUE_CHOICES = [(1, "👍"), (-1, "👎")]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="votes")
    value        = models.IntegerField(choices=VALUE_CHOICES)
    # Relations génériques : on peut voter sur une Question ou une Answer
    question     = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="votes", null=True, blank=True)
    answer       = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="votes", null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un user ne peut voter qu'une fois par question ou réponse
        constraints = [
            models.UniqueConstraint(fields=["user", "question"], condition=models.Q(question__isnull=False), name="unique_vote_question"),
            models.UniqueConstraint(fields=["user", "answer"],   condition=models.Q(answer__isnull=False),   name="unique_vote_answer"),
        ]

    def __str__(self):
        target = self.question or self.answer
        return f"{self.user.username} vote {self.value} sur {target}"


# ══════════════════════════════════════
#  ESPACE RESSOURCES
# ══════════════════════════════════════

class Resource(models.Model):
    """Résumé, flashcard deck ou conseil partagé par un étudiant."""
    TYPE_CHOICES = [
        ("resume",    "Résumé"),
        ("flashcard", "Flashcards"),
        ("conseil",   "Conseil"),
    ]
    SUBJECT_CHOICES = [
        ("maths",    "Mathématiques"),
        ("physique", "Physique"),
        ("info",     "Informatique"),
        ("histoire", "Histoire"),
        ("langue",   "Langues"),
        ("autre",    "Autre"),
    ]
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resources")
    course     = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="resources")
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subject    = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default="autre")
    title      = models.CharField(max_length=300)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.type}] {self.title}"

    def vote_count(self):
        return self.resource_votes.aggregate(total=models.Sum("value"))["total"] or 0


class ResourceVote(models.Model):
    """Vote +1 / -1 sur une ressource partagée."""
    VALUE_CHOICES = [(1, "👍"), (-1, "👎")]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resource_votes")
    resource   = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="resource_votes")
    value      = models.IntegerField(choices=VALUE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "resource")

    def __str__(self):
        return f"{self.user.username} vote {self.value} sur '{self.resource.title}'"


class Flashcard(models.Model):
    """Une carte dans un deck de flashcards (lié à une Resource de type flashcard)."""
    resource  = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="flashcards")
    question  = models.TextField()
    answer    = models.TextField()
    order     = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Flashcard {self.order} — {self.resource.title}"


class Tip(models.Model):
    """Conseil rapide pour les nouveaux étudiants."""
    CATEGORY_CHOICES = [
        ("methode",   "Méthode de travail"),
        ("exam",      "Conseils d'examen"),
        ("vie",       "Vie étudiante"),
        ("outils",    "Outils & apps"),
        ("autre",     "Autre"),
    ]
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tips")
    category   = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="autre")
    title      = models.CharField(max_length=200)
    content    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    likes      = models.ManyToManyField(User, blank=True, related_name="liked_tips")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def like_count(self):
        return self.likes.count()