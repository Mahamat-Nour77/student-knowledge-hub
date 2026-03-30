# Ajoute ces lignes dans urls.py (dans urlpatterns)

path("budget/add/",           views.budget_add,    name="budget_add"),
path("budget/delete/<int:entry_id>/", views.budget_delete, name="budget_delete"),
path("budget/clear/",         views.budget_clear,  name="budget_clear"),