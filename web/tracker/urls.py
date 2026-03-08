from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),

    # About pages
    path("about/", views.about, name="about"),
    path("about/how-it-works/", views.about_how_it_works, name="about_how_it_works"),
    path("about/training/", views.about_training, name="about_training"),
    path("about/cardio-guide/", views.about_cardio, name="about_cardio"),
    path("about/hiit-guide/", views.about_hiit, name="about_hiit"),

    # Account
    path("account/", views.account, name="account"),
    path("account/delete/", views.delete_account, name="delete_account"),

    # Privacy
    path("privacy/", views.privacy, name="privacy"),

    # Workout type selection & start
    path("start/", views.select_workout_type, name="select_workout_type"),
    path("start/workout/", views.start_workout, name="start_workout"),  # Legacy
    path("start/weightlifting/", views.start_weightlifting, name="start_weightlifting"),
    path("start/cardio/", views.start_cardio, name="start_cardio"),
    path("start/hiit/", views.start_hiit, name="start_hiit"),

    # Workout detail (routes to type-specific view)
    path("workouts/<int:workout_id>/", views.workout_detail, name="workout_detail"),
    path("workouts/<int:workout_id>/cardio/", views.cardio_workout_detail, name="cardio_workout_detail"),
    path("workouts/<int:workout_id>/hiit/", views.hiit_workout_detail, name="hiit_workout_detail"),

    # Workout actions
    path("workouts/<int:workout_id>/notes/", views.save_workout_notes, name="save_workout_notes"),
    path("workouts/<int:workout_id>/warmup/", views.save_warmup, name="save_warmup"),
    path("workouts/<int:workout_id>/finisher/", views.save_finisher, name="save_finisher"),

    # User preferences
    path("preferences/adaptive/", views.toggle_adaptive_programming, name="toggle_adaptive_programming"),
    path("workouts/<int:workout_id>/add-set/", views.add_set, name="add_set"),
    path("workouts/<int:workout_id>/add-cardio/", views.add_cardio_entry, name="add_cardio_entry"),
    path("workouts/<int:workout_id>/update-hiit/", views.update_hiit_session, name="update_hiit_session"),
    path("workouts/<int:workout_id>/end/", views.end_workout, name="end_workout"),
    path("workouts/<int:workout_id>/delete/", views.delete_workout, name="delete_workout"),

    # Set management
    path("sets/<int:set_id>/edit/", views.edit_set, name="edit_set"),
    path("sets/<int:set_id>/delete/", views.delete_set, name="delete_set"),
    path("sets/<int:set_id>/move/", views.move_set, name="move_set"),

    # Calendar & Scheduling
    path("calendar/", views.calendar_view, name="calendar_view"),
    path("calendar/schedule/", views.schedule_workout, name="schedule_workout"),
    path("calendar/schedule/<int:scheduled_id>/delete/", views.delete_scheduled, name="delete_scheduled"),
    path("calendar/schedule/<int:scheduled_id>/start/", views.start_from_scheduled, name="start_from_scheduled"),

    # Templates
    path("templates/", views.template_list, name="template_list"),
    path("templates/create/", views.create_template, name="create_template"),
    path("templates/<int:template_id>/", views.template_detail, name="template_detail"),
    path("templates/<int:template_id>/edit/", views.edit_template, name="edit_template"),
    path("templates/<int:template_id>/delete/", views.delete_template, name="delete_template"),
    path("templates/<int:template_id>/use/", views.use_template, name="use_template"),
    path("workouts/<int:workout_id>/save-as-template/", views.save_as_template, name="save_as_template"),

    # History
    path("history/", views.workout_history, name="workout_history"),
]
