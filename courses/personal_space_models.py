# ══════════════════════════════════════════════════════
# Ajoute ces modèles à la FIN de ton models.py
# ══════════════════════════════════════════════════════

class PersonalFile(models.Model):
    """Fichier personnel d'un étudiant (pas lié aux cours partagés)."""
    CATEGORY_CHOICES = [
        ("maths",      "Mathématiques"),
        ("physique",   "Physique"),
        ("info",       "Informatique"),
        ("chimie",     "Chimie"),
        ("biologie",   "Biologie"),
        ("histoire",   "Histoire & Géo"),
        ("langue",     "Langues"),
        ("medecine",   "Médecine"),
        ("autre",      "Autre"),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="personal_files")
    title       = models.CharField(max_length=200)
    file        = models.FileField(upload_to="personal/")
    category    = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="autre")
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.user.username} — {self.title}"

    def is_pdf(self):
        return self.file.name.lower().endswith('.pdf')

    def extension(self):
        return self.file.name.split('.')[-1].upper()


class PersonalNote(models.Model):
    """Résumé ou flashcard généré par l'IA pour un fichier personnel."""
    TYPE_CHOICES = [
        ("resume",    "Résumé IA"),
        ("flashcard", "Flashcards IA"),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="personal_notes")
    file        = models.ForeignKey(PersonalFile, on_delete=models.CASCADE, related_name="notes", null=True, blank=True)
    type        = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title       = models.CharField(max_length=300)
    content     = models.TextField()  # JSON pour flashcards, texte pour résumé
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} — {self.title}"