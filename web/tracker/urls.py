from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),

    # About pages (split)
    path("about/", views.about, name="about"),
    path("about/how-it-works/", views.about_how_it_works, name="about_how_it_works"),
    path("about/training/", views.about_training, name="about_training"),

    # Account
    path("account/", views.account, name="account"),
    path("account/delete/", views.delete_account, name="delete_account"),

    # Privacy
    path("privacy/", views.privacy, name="privacy"),

    # Workout management
    path("start/", views.start_workout, name="start_workout"),
    path("workouts/<int:workout_id>/", views.workout_detail, name="workout_detail"),
    path("workouts/<int:workout_id>/add-set/", views.add_set, name="add_set"),
    path("workouts/<int:workout_id>/end/", views.end_workout, name="end_workout"),
    path("workouts/<int:workout_id>/delete/", views.delete_workout, name="delete_workout"),

    # Set management
    path("sets/<int:set_id>/edit/", views.edit_set, name="edit_set"),
    path("sets/<int:set_id>/delete/", views.delete_set, name="delete_set"),
    path("sets/<int:set_id>/move/", views.move_set, name="move_set"),
]
