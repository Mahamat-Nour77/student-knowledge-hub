# ══════════════════════════════════════════════════════════════
# Ajoute ces 3 vues dans views.py
# Et ajoute BudgetEntry dans l'import des models en haut :
# from .models import (..., BudgetEntry)
# ══════════════════════════════════════════════════════════════

@login_required
def student_space(request):
    entries = BudgetEntry.objects.filter(user=request.user)
    return render(request, "courses/student_space.html", {
        "budget_entries": entries,
    })


@login_required
def budget_add(request):
    if request.method == "POST":
        entry_type = request.POST.get("type", "out")
        title      = request.POST.get("title", "").strip()
        amount     = request.POST.get("amount", "0")
        category   = request.POST.get("category", "Autre")

        try:
            amount = float(amount)
            if title and amount > 0:
                BudgetEntry.objects.create(
                    user=request.user,
                    type=entry_type,
                    title=title,
                    amount=amount,
                    category=category,
                )
        except ValueError:
            pass

    return redirect("student_space")


@login_required
def budget_delete(request, entry_id):
    entry = get_object_or_404(BudgetEntry, id=entry_id, user=request.user)
    entry.delete()
    return redirect("student_space")


@login_required
def budget_clear(request):
    if request.method == "POST":
        BudgetEntry.objects.filter(user=request.user).delete()
    return redirect("student_space")