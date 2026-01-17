from django.conf import settings
from django.db import models


class Workout(models.Model):
    DAY_CHOICES = [
        ("Back & Biceps", "Back & Biceps"),
        ("Chest & Triceps", "Chest & Triceps"),
        ("Legs", "Legs"),
        ("Core", "Core"),
        ("Shoulders & Traps", "Shoulders & Traps"),
        ("Combination", "Combination"),
    ]

    MOOD_CHOICES = [
        ("Exhausted", "Exhausted"),
        ("Low Energy", "Low Energy"),
        ("Normal", "Normal"),
        ("Energetic", "Energetic"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workouts",
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=100, blank=True, default="")
    day = models.CharField(max_length=32, choices=DAY_CHOICES)
    mood = models.CharField(max_length=32, choices=MOOD_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} - {self.started_at:%Y-%m-%d %I:%M %p}"
        return f"{self.day} - {self.started_at:%Y-%m-%d %I:%M %p}"

    @property
    def display_name(self):
        """Return custom name if set, otherwise return day type"""
        return self.name if self.name else self.day


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
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT)
    set_number = models.PositiveIntegerField()
    weight_lb = models.PositiveIntegerField()  # 0 = bodyweight
    reps = models.PositiveIntegerField()
    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]

    def __str__(self) -> str:
        return f"{self.exercise.name}: {self.weight_lb}x{self.reps} ({self.quality})"
