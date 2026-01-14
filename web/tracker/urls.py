from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("start/", views.start_workout, name="start_workout"),

    path("workouts/<int:workout_id>/", views.workout_detail, name="workout_detail"),
    path("workouts/<int:workout_id>/end/", views.end_workout, name="end_workout"),
    path("workouts/<int:workout_id>/delete/", views.delete_workout, name="delete_workout"),

    # EDIT / DELETE SETS
    path("sets/<int:set_id>/edit/", views.edit_set, name="edit_set"),
    path("sets/<int:set_id>/delete/", views.delete_set, name="delete_set"),
]
