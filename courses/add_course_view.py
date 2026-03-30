# ══════════════════════════════════════════════════════
# Remplace la fonction add_course dans views.py
# ══════════════════════════════════════════════════════

@login_required
def add_course(request):
    if request.method == "POST":
        name        = request.POST.get("name", "").strip()
        professor   = request.POST.get("professor", "").strip()
        filiere     = request.POST.get("filiere", "")
        semester    = request.POST.get("semester", "")
        difficulty  = request.POST.get("difficulty", "medium")
        tags        = request.POST.get("tags", "")
        description = request.POST.get("description", "").strip()
        image       = request.FILES.get("image")
        pdf_file    = request.FILES.get("pdf_file")

        if not name:
            messages.error(request, "Le nom du cours est obligatoire.")
            return redirect("add_course")

        semester_display = f"{filiere} — {semester}" if filiere and semester else (filiere or semester or "")

        course = Course(
            name=name,
            professor=professor,
            semester=semester_display,
        )
        if image:
            course.image = image
        course.save()

        # Si un PDF est uploadé, créer un Document automatiquement
        if pdf_file:
            Document.objects.create(
                title=f"{name} — Document principal",
                description=description or f"Document principal du cours {name}",
                file=pdf_file,
                course=course,
                uploaded_by=request.user,
            )
            messages.success(request, f"✅ Cours « {name} » et document PDF ajoutés avec succès !")
        else:
            messages.success(request, f"✅ Cours « {name} » ajouté avec succès !")

        return redirect("course_detail", course_id=course.id)

    return render(request, "courses/add_course.html")