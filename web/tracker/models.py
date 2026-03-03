from django.conf import settings
from django.db import models


class Workout(models.Model):
    WORKOUT_TYPE_CHOICES = [
        ("weightlifting", "Weightlifting"),
        ("cardio", "Cardio"),
        ("hiit", "HIIT"),
    ]

    DAY_CHOICES = [
        ("Custom Workout", "Custom Workout"),
        ("Back & Biceps", "Back & Biceps"),
        ("Chest & Triceps", "Chest & Triceps"),
        ("Legs", "Legs"),
        ("Core", "Core"),
        ("Shoulders & Traps", "Shoulders & Traps"),
    ]

    MOOD_CHOICES = [
        ("Exhausted", "Exhausted"),
        ("Low Energy", "Low Energy"),
        ("Normal", "Normal"),
        ("Energetic", "Energetic"),
    ]

    CARDIO_TYPE_CHOICES = [
        ("running", "Running"),
        ("cycling", "Cycling"),
        ("swimming", "Swimming"),
        ("rowing", "Rowing"),
        ("elliptical", "Elliptical"),
        ("stair_climber", "Stair Climber"),
        ("jump_rope", "Jump Rope"),
        ("walking", "Walking"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workouts",
        null=True,
        blank=True,
    )

    # Workout type (new)
    workout_type = models.CharField(
        max_length=20, choices=WORKOUT_TYPE_CHOICES, default="weightlifting"
    )

    name = models.CharField(max_length=100, blank=True, default="")
    day = models.CharField(max_length=32, choices=DAY_CHOICES, blank=True, default="")
    mood = models.CharField(max_length=32, choices=MOOD_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Cardio-specific fields
    cardio_type = models.CharField(
        max_length=32, choices=CARDIO_TYPE_CHOICES, blank=True, default=""
    )
    cardio_equipment = models.CharField(max_length=80, blank=True, default="")
    target_duration_minutes = models.PositiveIntegerField(default=0)
    target_distance_miles = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )

    # Template reference (new)
    template = models.ForeignKey(
        "WorkoutTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workouts_from_template",
    )

    # End-of-session notes
    notes = models.TextField(blank=True, default="")

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} - {self.started_at:%Y-%m-%d %I:%M %p}"
        return f"{self.day} - {self.started_at:%Y-%m-%d %I:%M %p}"

    @property
    def display_name(self):
        """Return custom name if set, otherwise return day type or workout type"""
        if self.name:
            return self.name
        if self.workout_type == "cardio" and self.cardio_type:
            return dict(self.CARDIO_TYPE_CHOICES).get(self.cardio_type, self.cardio_type)
        if self.workout_type == "hiit":
            return "HIIT Session"
        return self.day if self.day else "Workout"

    @property
    def workout_type_display(self):
        """Return human-readable workout type"""
        return dict(self.WORKOUT_TYPE_CHOICES).get(self.workout_type, self.workout_type)


class Exercise(models.Model):
    DAY_CHOICES = [
        ("Chest & Triceps", "Chest & Triceps"),
        ("Back & Biceps", "Back & Biceps"),
        ("Legs", "Legs"),
        ("Core", "Core"),
        ("Shoulders & Traps", "Shoulders & Traps"),
    ]

    name = models.CharField(max_length=120)
    equipment = models.CharField(max_length=80, blank=True, default="")
    day = models.CharField(max_length=32, choices=DAY_CHOICES)

    is_dumbbell_pair = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "equipment"],
                name="unique_exercise_name_equipment",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} | {self.equipment}"


class SetEntry(models.Model):
    QUALITY_CHOICES = [
        ("bad", "Bad"),
        ("ok", "OK"),
        ("good", "Good"),
        ("great", "Great"),
    ]

    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="sets")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, null=True, blank=True)
    custom_exercise_name = models.CharField(max_length=120, blank=True, default="")
    custom_equipment = models.CharField(max_length=80, blank=True, default="")
    set_number = models.PositiveIntegerField()
    weight_lb = models.PositiveIntegerField()  # 0 = bodyweight
    reps = models.PositiveIntegerField(default=0)  # 0 for cardio/timed exercises
    duration_seconds = models.PositiveIntegerField(default=0)  # For cardio: time in seconds
    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # Cardio-specific fields
    distance_miles = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    incline_percent = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    speed_mph = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["position", "created_at"]

    @property
    def exercise_name(self):
        """Return custom exercise name or linked exercise name"""
        if self.custom_exercise_name:
            return self.custom_exercise_name
        return self.exercise.name if self.exercise else "Unknown"

    def __str__(self) -> str:
        name = self.exercise_name
        if self.duration_seconds > 0:
            mins = self.duration_seconds // 60
            secs = self.duration_seconds % 60
            return f"{name}: {mins}m {secs}s ({self.quality})"
        return f"{name}: {self.weight_lb}x{self.reps} ({self.quality})"


class ScheduledWorkout(models.Model):
    """Scheduled future workouts for calendar planning"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheduled_workouts",
    )
    scheduled_date = models.DateField()
    workout_type = models.CharField(
        max_length=20, choices=Workout.WORKOUT_TYPE_CHOICES, default="weightlifting"
    )
    day = models.CharField(
        max_length=32, choices=Workout.DAY_CHOICES, blank=True, default=""
    )
    cardio_type = models.CharField(
        max_length=32, choices=Workout.CARDIO_TYPE_CHOICES, blank=True, default=""
    )
    template = models.ForeignKey(
        "WorkoutTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_workouts",
    )
    notes = models.TextField(blank=True, default="")
    completed = models.BooleanField(default=False)
    completed_workout = models.ForeignKey(
        Workout,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_from",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_date", "created_at"]

    def __str__(self) -> str:
        return f"{self.get_workout_type_display()} on {self.scheduled_date}"

    @property
    def display_name(self):
        """Return descriptive name for the scheduled workout"""
        if self.template:
            return self.template.name
        if self.workout_type == "weightlifting" and self.day:
            return self.day
        if self.workout_type == "cardio" and self.cardio_type:
            return dict(Workout.CARDIO_TYPE_CHOICES).get(
                self.cardio_type, self.cardio_type
            )
        if self.workout_type == "hiit":
            return "HIIT Session"
        return dict(Workout.WORKOUT_TYPE_CHOICES).get(
            self.workout_type, self.workout_type
        )


class WorkoutTemplate(models.Model):
    """Reusable workout templates"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workout_templates",
    )
    name = models.CharField(max_length=100)
    workout_type = models.CharField(
        max_length=20, choices=Workout.WORKOUT_TYPE_CHOICES, default="weightlifting"
    )
    day = models.CharField(
        max_length=32, choices=Workout.DAY_CHOICES, blank=True, default=""
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Cardio template fields
    cardio_type = models.CharField(
        max_length=32, choices=Workout.CARDIO_TYPE_CHOICES, blank=True, default=""
    )
    target_duration_minutes = models.PositiveIntegerField(default=0)
    target_distance_miles = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )

    # HIIT template fields
    hiit_intervals = models.PositiveIntegerField(default=8)
    hiit_work_seconds = models.PositiveIntegerField(default=30)
    hiit_rest_seconds = models.PositiveIntegerField(default=15)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_workout_type_display()})"


class TemplateExercise(models.Model):
    """Exercises within a workout template"""

    template = models.ForeignKey(
        WorkoutTemplate, on_delete=models.CASCADE, related_name="exercises"
    )
    exercise = models.ForeignKey(
        "Exercise", on_delete=models.PROTECT, null=True, blank=True
    )
    custom_exercise_name = models.CharField(max_length=120, blank=True, default="")
    custom_equipment = models.CharField(max_length=80, blank=True, default="")
    target_sets = models.PositiveIntegerField(default=3)
    target_reps = models.PositiveIntegerField(default=10)
    target_weight = models.PositiveIntegerField(default=0)
    target_duration_seconds = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default="")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]

    @property
    def exercise_name(self):
        """Return custom exercise name or linked exercise name"""
        if self.custom_exercise_name:
            return self.custom_exercise_name
        return self.exercise.name if self.exercise else "Unknown"

    def __str__(self) -> str:
        return f"{self.exercise_name} - {self.target_sets}x{self.target_reps}"


class HIITSession(models.Model):
    """HIIT-specific session data"""

    workout = models.OneToOneField(
        Workout, on_delete=models.CASCADE, related_name="hiit_session"
    )
    total_intervals = models.PositiveIntegerField(default=8)
    work_duration = models.PositiveIntegerField(default=30)  # seconds
    rest_duration = models.PositiveIntegerField(default=15)  # seconds
    intervals_completed = models.PositiveIntegerField(default=0)
    total_work_time = models.PositiveIntegerField(default=0)  # actual work time in seconds
    total_rest_time = models.PositiveIntegerField(default=0)  # actual rest time in seconds

    def __str__(self) -> str:
        return f"HIIT: {self.intervals_completed}/{self.total_intervals} intervals"

    @property
    def planned_duration_seconds(self):
        """Calculate total planned session duration"""
        return (self.work_duration + self.rest_duration) * self.total_intervals

    @property
    def planned_duration_display(self):
        """Return formatted planned duration"""
        total_secs = self.planned_duration_seconds
        mins = total_secs // 60
        secs = total_secs % 60
        return f"{mins}:{secs:02d}"
