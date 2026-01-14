from django.core.management.base import BaseCommand
from tracker.models import Exercise


EXERCISES_IN_ORDER = [
    # Chest & Triceps
    ("Chest & Triceps", "Flat Bench Press", "Barbell"),
    ("Chest & Triceps", "Incline Bench Press", "Barbell"),
    ("Chest & Triceps", "Flat Bench Press", "Dumbbells"),
    ("Chest & Triceps", "Incline Bench Press", "Dumbbells"),
    ("Chest & Triceps", "Chest Flys", "Dumbbells"),
    ("Chest & Triceps", "Chest Flys", "Machine/Cable"),
    ("Chest & Triceps", "Skull Crushers", "EZ-bar"),
    ("Chest & Triceps", "Tricep Pushdown", "Cable"),
    ("Chest & Triceps", "Dips", "Bodyweight"),
    ("Chest & Triceps", "Dips", "Weighted"),

    # Legs
    ("Legs", "Squats", "Barbell"),
    ("Legs", "Squats", "Machine"),
    ("Legs", "Leg Press", "Machine"),
    ("Legs", "Leg Press Standing", "Machine"),
    ("Legs", "Calf raises", "Machine"),
    ("Legs", "Lunges", "Dumbbells/Kettlebells"),

    # Back & Biceps
    ("Back & Biceps", "Pull Ups", "Bodyweight"),
    ("Back & Biceps", "Pull Ups", "Weighted"),
    ("Back & Biceps", "Rows", "Dumbbells"),
    ("Back & Biceps", "Rows", "Machine"),
    ("Back & Biceps", "Deadlifts", "Barbell"),
    ("Back & Biceps", "Romanian Deadlifts", "Trap Bar"),
    ("Back & Biceps", "T-Bar Rows", "Chest Supported Rowing Machine"),
    ("Back & Biceps", "Standing T-Bar Rows", "V-Grip Barbell"),
    ("Back & Biceps", "Preacher Curl Bench", "EZ-Bar"),
    ("Back & Biceps", "Preacher Curl Machine", "Weighted"),
    ("Back & Biceps", "Bicep Curls Standing", "Dumbbells"),
    ("Back & Biceps", "Bicep Curls Standing", "EZ-Bar"),
    ("Back & Biceps", "Bicep Concentration Curls Seated", "Dumbbells"),

    # Shoulders & Traps
    ("Shoulders & Traps", "Shoulder Press", "Barbell"),
    ("Shoulders & Traps", "Shoulder Press", "Dumbbells"),
    ("Shoulders & Traps", "Reverse Flys", "Dumbbells"),
    ("Shoulders & Traps", "Reverse Flys", "Machine"),
    ("Shoulders & Traps", "Walking Farmers Shrugs", "Weight Plates"),
    ("Shoulders & Traps", "Farmers Shrugs", "Dumbbells"),

    # Core
    ("Core", "Leg Lifts", "Bodyweight"),
    ("Core", "Russian Twist Sit-Ups", "Decline Bench Bodyweight"),
    ("Core", "Sit-Ups", "Decline Bench Bodyweight"),
    ("Core", "Sit-Ups", "Decline Bench Weighted"),
    ("Core", "Russian Twists", "Floor"),
    ("Core", "Plank Knees to Elbow", "Floor"),
    ("Core", "Plank Knees to Elbow Twisting", "Floor"),
    ("Core", "V Ups", "Floor"),
]


def is_dumbbell_pair(equipment: str) -> bool:
    # Default to "two dumbbells" when equipment contains "dumbbell"
    return "dumbbell" in (equipment or "").lower()


class Command(BaseCommand):
    help = "Seed exercises in the exact order provided by the user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset fields for seeded exercises. Does NOT delete due to PROTECT on SetEntry.exercise.",
        )

    def handle(self, *args, **options):
        # NOTE:
        # We cannot delete Exercise rows if SetEntry exists because SetEntry.exercise uses on_delete=PROTECT.
        # So "--reset" means: rewrite / upsert exercises from the seed list and also
        # set sort_order for anything in the list. We also optionally "deactivate" exercises
        # not in the seed list by pushing them to the bottom (not deleting).

        if options.get("reset"):
            self.stdout.write(
                "Reset requested: will rewrite exercise fields instead of deleting (SetEntry.exercise is PROTECT)."
            )

        created = 0
        updated = 0

        # Upsert everything from the seed list in the exact order
        for idx, (day, name, equipment) in enumerate(EXERCISES_IN_ORDER, start=1):
            ex, was_created = Exercise.objects.update_or_create(
                name=name,
                equipment=equipment,
                defaults={
                    "day": day,
                    "is_dumbbell_pair": is_dumbbell_pair(equipment),
                    "sort_order": idx,
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        total = Exercise.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete. Created={created}, Updated={updated}, Total={total}"
            )
        )
