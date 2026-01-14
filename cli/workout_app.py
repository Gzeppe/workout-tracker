import time
from typing import Optional, List
import db

WORKOUT_DAYS = [
    "Back & Biceps",
    "Legs",
    "Core",
    "Chest & Triceps",
    "Shoulders & Traps",
]

MOODS = ["Exhausted", "Low Energy", "Normal", "Energetic"]
QUALITIES = ["bad", "ok", "good", "great"]
REST_OPTIONS = [60, 90, 120, 180]


def prompt_choice(title: str, options: List[str]) -> str:
    print("\n" + title)
    for i, opt in enumerate(options, 1):
        print(f"{i}) {opt}")
    while True:
        raw = input("Choose: ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print("Invalid choice.")


def prompt_int(msg: str, min_v: Optional[int] = None, max_v: Optional[int] = None) -> int:
    while True:
        raw = input(msg).strip()
        if raw.isdigit():
            v = int(raw)
            if (min_v is None or v >= min_v) and (max_v is None or v <= max_v):
                return v
        print("Enter a valid whole number.")


def prompt_quality() -> str:
    return prompt_choice("Set quality:", [q.upper() for q in QUALITIES]).lower()


def prompt_weight_typed(last_weight: Optional[int] = None) -> int:
    while True:
        suffix = f" (Enter = {last_weight})" if last_weight is not None else ""
        raw = input(f"Weight lbs (0=bodyweight){suffix}: ").strip()

        if raw == "" and last_weight is not None:
            return last_weight

        if not raw.isdigit():
            print("Enter a whole number (e.g., 0, 135, 185).")
            continue

        w = int(raw)
        if w < 0 or w > 350:
            print("Weight out of range.")
            continue
        if w % 5 != 0:
            print("Weight must be in 5 lb increments (e.g., 135, 140, 145).")
            continue
        return w


def choose_exercise(day: str) -> str:
    results = db.search_exercises(day, limit=500)
    if not results:
        print(f"No exercises found for {day}. (Did the DB seed correctly?)")
        return ""

    print(f"\nExercises for: {day}")
    for i, (name, tags) in enumerate(results, 1):
        tag_txt = f" [{tags}]" if tags else ""
        print(f"{i}) {name}{tag_txt}")

    idx = prompt_int(f"Choose 1-{len(results)}: ", 1, len(results))
    return results[idx - 1][0]


def get_implement_count(day: str, exercise_name: str) -> int:
    tags = db.get_exercise_tags(day, exercise_name)
    if tags and "dumbbell" in tags:
        raw = input("Dumbbells: Enter = 2 (pair), or type 1 for single: ").strip()
        if raw == "1":
            return 1
        return 2
    return 1


def rest_timer(seconds: int):
    print(f"\nRest timer: {seconds}s (Ctrl+C to stop)")
    try:
        for remaining in range(seconds, 0, -1):
            print(f"\r{remaining:>3}s remaining...", end="")
            time.sleep(1)
        print("\rDone!               ")
        try:
            import winsound
            winsound.Beep(900, 250)
        except Exception:
            print("\a", end="")
    except KeyboardInterrupt:
        print("\nTimer stopped.\n")


def show_current_workout(workout_id: int):
    rows = db.get_workout_sets(workout_id)
    if not rows:
        print("\nNo sets logged yet.\n")
        return

    finisher_log = db.get_finisher_log(workout_id)

    print("\nCurrent workout sets")
    print("-" * 100)
    print("SetID | Exercise                 | Set# | Reps | Weight | Quality")
    print("-" * 100)
    for sid, ex, sn, reps, wt, impl, q, _rest in rows:
        impl_txt = "x2" if impl == 2 else ""
        print(f"{sid:<5} | {ex:<23} | {sn:<4} | {reps:<4} | {int(wt):<4}{impl_txt:<3} | {q:<7}")
    print("-" * 100)

    if finisher_log and finisher_log.strip():
        print("\nFinisher:")
        for line in finisher_log.splitlines():
            print(f"- {line.strip()}")
        print()


def add_finisher_items(workout_id: int):
    print("\nFinisher (add multiple items).")
    while True:
        fin_type = prompt_choice("Add finisher type:", ["Cardio", "Core", "Stretching"]).lower()
        mins_raw = input("Duration minutes (default 10): ").strip()
        minutes = 10
        if mins_raw.isdigit() and int(mins_raw) > 0:
            minutes = int(mins_raw)

        note = input("Note (optional): ").strip()
        note_part = f" - {note}" if note else ""
        line = f"{fin_type} {minutes}m{note_part}"
        db.append_finisher_item(workout_id, line)

        more = input("Add another finisher item? (y/n): ").strip().lower()
        if more != "y":
            break


def workout_session():
    day = prompt_choice("Select workout day:", WORKOUT_DAYS)
    mood = prompt_choice("How are you feeling today?", MOODS)

    workout_id = db.start_workout(day, mood)
    print(f"\nStarted workout #{workout_id} ({day} | {mood})")

    while True:
        print("\nWorkout Menu")
        print("1) Add exercise + sets")
        print("2) View current workout")
        print("3) Edit a set")
        print("4) Delete a set")
        print("5) End workout")
        choice = input("Choose: ").strip()

        if choice == "1":
            exercise = choose_exercise(day)
            if not exercise:
                continue

            implement_count = get_implement_count(day, exercise)
            we_id = db.add_workout_exercise(workout_id, exercise)

            set_num = 1
            last_weight: Optional[int] = None

            while True:
                weight = prompt_weight_typed(last_weight=last_weight)
                last_weight = weight

                reps = prompt_int("Reps: ", 0, 100)
                quality = prompt_quality()

                rest_seconds = None
                rest_raw = input("Rest timer? (Enter to skip or 60/90/120/180): ").strip()
                if rest_raw.isdigit() and int(rest_raw) in REST_OPTIONS:
                    rest_seconds = int(rest_raw)

                db.add_set(
                    we_id,
                    set_num,
                    reps,
                    float(weight),
                    quality,
                    rest_seconds,
                    implement_count=implement_count
                )
                set_num += 1

                if rest_seconds:
                    rest_timer(rest_seconds)

                more = input("Add another set? (y/n): ").strip().lower()
                if more != "y":
                    break

        elif choice == "2":
            show_current_workout(workout_id)

        elif choice == "3":
            show_current_workout(workout_id)
            sid = prompt_int("SetID to edit: ", 1)

            new_reps_raw = input("New reps (blank = keep): ").strip()
            new_quality_raw = input("New quality bad/ok/good/great (blank = keep): ").strip().lower()

            change_w = input("Change weight? (y/n): ").strip().lower()
            new_weight = None
            if change_w == "y":
                new_weight = float(prompt_weight_typed(last_weight=None))

            new_reps = int(new_reps_raw) if new_reps_raw.isdigit() else None
            new_quality = new_quality_raw if new_quality_raw in QUALITIES else None

            db.update_set(sid, reps=new_reps, weight=new_weight, quality=new_quality)
            print("Updated.")

        elif choice == "4":
            show_current_workout(workout_id)
            sid = prompt_int("SetID to delete: ", 1)
            db.delete_set(sid)
            print("Deleted.")

        elif choice == "5":
            did_finisher = input("Finisher? (y/n): ").strip().lower()
            if did_finisher == "y":
                add_finisher_items(workout_id)

            db.end_workout(workout_id)
            print("Workout ended.")
            print(db.build_summary(workout_id))
            break

        else:
            print("Invalid choice.")


def main():
    db.init_db()

    while True:
        print("\nMain Menu")
        print("1) Start new workout")
        print("2) List previous workouts")
        print("3) View workout sets by id")
        print("4) Exit")

        choice = input("Choose: ").strip()

        if choice == "1":
            workout_session()

        elif choice == "2":
            rows = db.list_workouts()
            if not rows:
                print("\nNo workouts yet.\n")
                continue

            print("\nPrevious Workouts")
            print("-" * 90)
            for wid, started, ended, day, mood, set_count in rows:
                status = "DONE" if ended else "IN PROGRESS"
                print(f"#{wid} | {day} | {mood} | sets:{set_count} | {started} | {status}")

        elif choice == "3":
            wid = prompt_int("Workout id: ", 1)
            show_current_workout(wid)

        elif choice == "4":
            print("Bye.")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
