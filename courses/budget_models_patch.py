# Ajoute ce modèle à la FIN de ton models.py

class BudgetEntry(models.Model):
    """Entrée de budget (revenu ou dépense) par utilisateur."""
    TYPE_CHOICES = [
        ("in",  "Revenu"),
        ("out", "Dépense"),
    ]
    CATEGORY_CHOICES = [
        ("Alimentation", "🍕 Alimentation"),
        ("Transport",    "🚌 Transport"),
        ("Loyer",        "🏠 Loyer"),
        ("Scolarité",    "📚 Scolarité"),
        ("Loisirs",      "🎭 Loisirs"),
        ("Bourse",       "🎓 Bourse"),
        ("Job",          "💼 Job"),
        ("Famille",      "👨‍👩‍👧 Famille"),
        ("Autre",        "📦 Autre"),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budget_entries")
    type       = models.CharField(max_length=3, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=200)
    amount     = models.DecimalField(max_digits=10, decimal_places=2)
    category   = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="Autre")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.type == "in" else "-"
        return f"{self.user.username} | {sign}{self.amount}€ | {self.title}"