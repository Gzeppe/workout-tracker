from django.core.management.base import BaseCommand
from tracker.models import Exercise


class Command(BaseCommand):
    help = 'Load initial exercise data into the database'

    def handle(self, *args, **options):
        # Exercise data matching the CLI version
        EXERCISE_DATA = [
            # Chest & Triceps
            ("Chest & Triceps", "Flat Bench Press", "barbell"),
            ("Chest & Triceps", "Incline Bench Press", "barbell"),
            ("Chest & Triceps", "Flat Bench Press", "dumbbell"),
            ("Chest & Triceps", "Incline Bench Press", "dumbbell"),
            ("Chest & Triceps", "Chest Flys", "dumbbell"),
            ("Chest & Triceps", "Chest Flys", "machine,cable"),
            ("Chest & Triceps", "Skull Crushers", "ezbar"),
            ("Chest & Triceps", "Tricep Pushdown", "cable"),
            ("Chest & Triceps", "Dips", "bodyweight"),
            ("Chest & Triceps", "Dips", "weighted"),

            # Legs
            ("Legs", "Squats", "barbell"),
            ("Legs", "Squats", "machine"),
            ("Legs", "Leg Press", "machine"),
            ("Legs", "Leg Press Standing", "machine"),
            ("Legs", "Calf raises", "machine"),
            ("Legs", "Lunges", "dumbbell,kettlebell"),

            # Back & Biceps
            ("Back & Biceps", "Pull Ups", "bodyweight"),
            ("Back & Biceps", "Pull Ups", "weighted"),
            ("Back & Biceps", "Rows", "dumbbell"),
            ("Back & Biceps", "Rows", "machine"),
            ("Back & Biceps", "Deadlifts", "barbell"),
            ("Back & Biceps", "Romanian Deadlifts", "trapbar"),
            ("Back & Biceps", "T-Bar Rows", "machine"),
            ("Back & Biceps", "Standing T-Bar Rows", "barbell"),
            ("Back & Biceps", "Preacher Curl Bench", "ezbar"),
            ("Back & Biceps", "Preacher Curl Machine", "machine,weighted"),
            ("Back & Biceps", "Bicep Curls Standing", "dumbbell"),
            ("Back & Biceps", "Bicep Curls Standing", "ezbar"),
            ("Back & Biceps", "Bicep Concentration Curls Seated", "dumbbell"),

            # Shoulders & Traps
            ("Shoulders & Traps", "Shoulder Press", "barbell"),
            ("Shoulders & Traps", "Shoulder Press", "dumbbell"),
            ("Shoulders & Traps", "Reverse Flys", "dumbbell"),
            ("Shoulders & Traps", "Reverse Flys", "machine"),
            ("Shoulders & Traps", "Walking Farmers Shrugs", "plates"),
            ("Shoulders & Traps", "Farmers Shrugs", "dumbbell"),

            # Core
            ("Core", "Leg Lifts", "bodyweight"),
            ("Core", "Russian Twist Sit-Ups", "bench,bodyweight"),
            ("Core", "Sit-Ups", "bench,bodyweight"),
            ("Core", "Sit-Ups", "bench,weighted"),
            ("Core", "Russian Twists", "floor"),
            ("Core", "Plank Knees to Elbow", "floor"),
            ("Core", "Plank Knees to Elbow Twisting", "floor"),
            ("Core", "V Ups", "floor"),
        ]

        # Check if exercises already exist
        if Exercise.objects.exists():
            self.stdout.write(
                self.style.WARNING('Exercises already exist. Skipping load.')
            )
            return

        # Create exercises with sort_order
        created_count = 0
        for idx, (day, name, equipment) in enumerate(EXERCISE_DATA):
            Exercise.objects.create(
                day=day,
                name=name,
                equipment=equipment,
                sort_order=idx
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {created_count} exercises')
        )
