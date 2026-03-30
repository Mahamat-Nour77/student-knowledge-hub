# Remplace la fonction upload_document dans views.py

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

            generate_quiz_flag = request.POST.get("generate_quiz", "0")
            num_questions = int(request.POST.get("num_questions", 10))

            if generate_quiz_flag == "1":
                # Extraire le texte et générer le quiz
                text = _extract_pdf_text(document.file.path)
                if len(text.strip()) < 100:
                    messages.warning(request, "Document uploadé ✅ mais le texte est trop court pour générer un quiz.")
                    return redirect("course_detail", course_id=course.id)
                try:
                    questions_data = _generate_quiz_with_claude(text, num_questions)
                    quiz = Quiz.objects.create(
                        document=document,
                        created_by=request.user,
                        mode="qcm",
                        num_questions=len(questions_data),
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
                    messages.success(request, f"✅ Document uploadé et quiz généré avec succès !")
                    return redirect("take_quiz", quiz_id=quiz.id)
                except Exception as e:
                    messages.error(request, f"Document uploadé ✅ mais erreur quiz : {e}")
                    return redirect("course_detail", course_id=course.id)
            else:
                messages.success(request, "✅ Document uploadé avec succès !")
                return redirect("course_detail", course_id=course.id)
        else:
            messages.error(request, "Erreur dans le formulaire.")

    else:
        form = DocumentForm()

    return render(request, "courses/upload_document.html", {
        "form": form,
        "course": course
    })