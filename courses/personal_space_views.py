# ══════════════════════════════════════════════════════
# Ajoute ces vues dans views.py
# Et ajoute dans l'import en haut :
# from .models import (..., PersonalFile, PersonalNote)
# ══════════════════════════════════════════════════════

@login_required
def my_documents(request):
    """Espace personnel — bibliothèque de fichiers IA."""
    files = PersonalFile.objects.filter(user=request.user)
    category = request.GET.get("category")
    if category:
        files = files.filter(category=category)
    return render(request, "courses/my_documents.html", {
        "files": files,
        "category_choices": PersonalFile.CATEGORY_CHOICES,
        "current_category": category,
        "total": PersonalFile.objects.filter(user=request.user).count(),
    })


@login_required
def personal_upload(request):
    """Upload d'un fichier personnel."""
    if request.method == "POST":
        title       = request.POST.get("title", "").strip()
        category    = request.POST.get("category", "autre")
        description = request.POST.get("description", "").strip()
        file        = request.FILES.get("file")

        if not title or not file:
            messages.error(request, "Titre et fichier sont obligatoires.")
            return redirect("my_documents")

        PersonalFile.objects.create(
            user=request.user,
            title=title,
            file=file,
            category=category,
            description=description,
        )
        messages.success(request, f"✅ Fichier « {title} » ajouté à ta bibliothèque !")
    return redirect("my_documents")


@login_required
def personal_delete(request, file_id):
    """Supprime un fichier personnel."""
    file = get_object_or_404(PersonalFile, id=file_id, user=request.user)
    file.file.delete()  # supprime aussi le fichier physique
    file.delete()
    messages.success(request, "Fichier supprimé.")
    return redirect("my_documents")


@login_required
def personal_generate_quiz(request, file_id):
    """Génère un quiz IA depuis un fichier personnel."""
    personal_file = get_object_or_404(PersonalFile, id=file_id, user=request.user)

    if not personal_file.is_pdf():
        messages.error(request, "Le Quiz IA fonctionne uniquement avec les PDFs.")
        return redirect("my_documents")

    num_q = int(request.POST.get("num_questions", 10))
    text = _extract_pdf_text(personal_file.file.path)

    if len(text.strip()) < 100:
        messages.error(request, "Le document ne contient pas assez de texte lisible.")
        return redirect("my_documents")

    try:
        questions_data = _generate_quiz_with_claude(text, num_q)
    except Exception as e:
        messages.error(request, f"Erreur IA : {e}")
        return redirect("my_documents")

    # Créer un Document temporaire lié au premier cours disponible
    # ou utiliser un quiz standalone
    # On crée un quiz sans document de cours — on le stocke via un "faux" document
    # Solution : créer un quiz rattaché à un cours fictif ou utiliser PersonalNote

    # Stocker le quiz en session pour le faire passer
    request.session["personal_quiz"] = {
        "title": f"Quiz — {personal_file.title}",
        "questions": questions_data,
        "file_id": file_id,
    }
    return redirect("personal_take_quiz")


@login_required
def personal_take_quiz(request):
    """Fait passer un quiz généré depuis un fichier personnel."""
    quiz_data = request.session.get("personal_quiz")
    if not quiz_data:
        messages.error(request, "Aucun quiz en cours.")
        return redirect("my_documents")

    if request.method == "POST":
        questions = quiz_data["questions"]
        score = 0
        results = []
        for i, q in enumerate(questions):
            user_ans = request.POST.get(f"q_{i}", "")
            correct = user_ans.upper() == q["answer"].upper()
            if correct:
                score += 1
            results.append({
                "question": q["question"],
                "choices": q["choices"],
                "user_answer": user_ans,
                "correct_answer": q["answer"],
                "explanation": q.get("explanation", ""),
                "is_correct": correct,
            })
        request.session["personal_quiz_result"] = {
            "title": quiz_data["title"],
            "score": score,
            "total": len(questions),
            "results": results,
        }
        del request.session["personal_quiz"]
        return redirect("personal_quiz_result")

    return render(request, "courses/personal_take_quiz.html", {
        "quiz": quiz_data,
        "questions": quiz_data["questions"],
    })


@login_required
def personal_quiz_result(request):
    """Affiche le résultat d'un quiz personnel."""
    result = request.session.get("personal_quiz_result")
    if not result:
        return redirect("my_documents")
    return render(request, "courses/personal_quiz_result.html", {"result": result})


@login_required
def personal_generate_resume(request, file_id):
    """Génère un résumé IA depuis un fichier personnel."""
    personal_file = get_object_or_404(PersonalFile, id=file_id, user=request.user)

    if not personal_file.is_pdf():
        messages.error(request, "Le résumé IA fonctionne uniquement avec les PDFs.")
        return redirect("my_documents")

    text = _extract_pdf_text(personal_file.file.path)
    if len(text.strip()) < 100:
        messages.error(request, "Le document ne contient pas assez de texte.")
        return redirect("my_documents")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""Tu es un assistant pédagogique expert. Génère un résumé structuré et détaillé du document suivant en français.

TEXTE :
\"\"\"
{text[:6000]}
\"\"\"

FORMAT ATTENDU :
- Un titre principal
- 3 à 5 sections avec titres clairs
- Points clés sous forme de puces
- Une conclusion courte

Sois clair, concis et pédagogique."""
        response = model.generate_content(prompt)
        resume_content = response.text.strip()

        note = PersonalNote.objects.create(
            user=request.user,
            file=personal_file,
            type="resume",
            title=f"Résumé — {personal_file.title}",
            content=resume_content,
        )
        messages.success(request, "✅ Résumé généré avec succès !")
        return redirect(f"/mes-documents/note/{note.id}/")
    except Exception as e:
        messages.error(request, f"Erreur IA : {e}")
        return redirect("my_documents")


@login_required
def personal_generate_flashcards(request, file_id):
    """Génère des flashcards depuis un fichier personnel."""
    personal_file = get_object_or_404(PersonalFile, id=file_id, user=request.user)

    if not personal_file.is_pdf():
        messages.error(request, "Les flashcards fonctionnent uniquement avec les PDFs.")
        return redirect("my_documents")

    text = _extract_pdf_text(personal_file.file.path)
    if len(text.strip()) < 100:
        messages.error(request, "Le document ne contient pas assez de texte.")
        return redirect("my_documents")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""Tu es un professeur expert. Génère 10 flashcards pédagogiques en français à partir du texte suivant.

TEXTE :
\"\"\"
{text[:6000]}
\"\"\"

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après :
[
  {{"question": "...", "answer": "..."}},
  ...
]"""
        response = model.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        flashcards = json.loads(raw.strip())

        note = PersonalNote.objects.create(
            user=request.user,
            file=personal_file,
            type="flashcard",
            title=f"Flashcards — {personal_file.title}",
            content=json.dumps(flashcards, ensure_ascii=False),
        )
        messages.success(request, f"✅ {len(flashcards)} flashcards générées !")
        return redirect(f"/mes-documents/note/{note.id}/")
    except Exception as e:
        messages.error(request, f"Erreur IA : {e}")
        return redirect("my_documents")


@login_required
def personal_note_view(request, note_id):
    """Affiche un résumé ou des flashcards."""
    note = get_object_or_404(PersonalNote, id=note_id, user=request.user)
    flashcards = None
    if note.type == "flashcard":
        try:
            flashcards = json.loads(note.content)
        except:
            flashcards = []
    return render(request, "courses/personal_note.html", {
        "note": note,
        "flashcards": flashcards,
    })