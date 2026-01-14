import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

DB_FILE = "workouts.db"

EQUIPMENT_CHOICES = [
    "any",
    "barbell",
    "dumbbell",
    "kettlebell",
    "ezbar",
    "machine",
    "cable",
    "trapbar",
    "bodyweight",
    "weighted",
    "plates",
    "bench",
    "floor",
    "other",
]

# Exercises in the EXACT order you provided.
EXERCISE_SEED = [
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


# ---- SUMMARY TUNING (easy to tweak later) ----
TARGET_REPS = 10            # your "good" rep target
NEAR_TARGET_MIN = 8         # "ok" threshold (1-2 reps short of 10)
MIN_SETS_GOAL = 3           # minimum sets per exercise guideline
QUALITY_GOOD = {"good", "great"}


def now_iso() -> str:
    # Example: 2025-12-19 01:42 PM
    return datetime.now().strftime("%Y-%m-%d %I:%M %p")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            day TEXT NOT NULL,
            mood TEXT NOT NULL,
            finisher_log TEXT
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            exercise TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_exercise_id INTEGER NOT NULL,
            set_number INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            weight REAL NOT NULL,
            implement_count INTEGER NOT NULL,
            quality TEXT NOT NULL,
            rest_seconds INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (workout_exercise_id) REFERENCES workout_exercises(id) ON DELETE CASCADE
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            name TEXT NOT NULL,
            equipment_tags TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            UNIQUE(day, name, equipment_tags)
        );
        """)

        row = conn.execute("SELECT COUNT(*) FROM exercises;").fetchone()
        if row and row[0] == 0:
            conn.executemany(
                """
                INSERT INTO exercises (day, name, equipment_tags, display_order)
                VALUES (?, ?, ?, ?);
                """,
                [(d, n, e, i) for i, (d, n, e) in enumerate(EXERCISE_SEED)]
            )


# ------------------ WRITE OPERATIONS ------------------

def start_workout(day: str, mood: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO workouts (started_at, day, mood, finisher_log) VALUES (?, ?, ?, ?);",
            (now_iso(), day, mood, None)
        )
        return int(cur.lastrowid)


def end_workout(workout_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE workouts SET ended_at = ? WHERE id = ?;", (now_iso(), workout_id))


def append_finisher_item(workout_id: int, item_line: str) -> None:
    with get_conn() as conn:
        row = conn.execute("SELECT finisher_log FROM workouts WHERE id = ?;", (workout_id,)).fetchone()
        current = row[0] if row else None
        if current and current.strip():
            new_val = current.rstrip() + "\n" + item_line.strip()
        else:
            new_val = item_line.strip()
        conn.execute("UPDATE workouts SET finisher_log = ? WHERE id = ?;", (new_val, workout_id))


def add_workout_exercise(workout_id: int, exercise: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO workout_exercises (workout_id, exercise, created_at)
            VALUES (?, ?, ?);
            """,
            (workout_id, exercise, now_iso())
        )
        return int(cur.lastrowid)


def add_set(
    workout_exercise_id: int,
    set_number: int,
    reps: int,
    weight: float,
    quality: str,
    rest_seconds: Optional[int],
    implement_count: int = 1
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO sets (
                workout_exercise_id,
                set_number,
                reps,
                weight,
                implement_count,
                quality,
                rest_seconds,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                workout_exercise_id,
                set_number,
                reps,
                weight,
                implement_count,
                quality,
                rest_seconds,
                now_iso()
            )
        )
        return int(cur.lastrowid)


def delete_set(set_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sets WHERE id = ?;", (set_id,))


def update_set(set_id: int, reps: Optional[int] = None, weight: Optional[float] = None, quality: Optional[str] = None) -> None:
    fields = []
    params = []

    if reps is not None:
        fields.append("reps = ?")
        params.append(reps)
    if weight is not None:
        fields.append("weight = ?")
        params.append(weight)
    if quality is not None:
        fields.append("quality = ?")
        params.append(quality)

    if not fields:
        return

    params.append(set_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE sets SET {', '.join(fields)} WHERE id = ?;", tuple(params))


# ------------------ READ OPERATIONS ------------------

def list_workouts(limit: int = 20) -> List[Tuple]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT w.id, w.started_at, COALESCE(w.ended_at,''), w.day, w.mood,
                   COUNT(s.id) as set_count
            FROM workouts w
            LEFT JOIN workout_exercises we ON we.workout_id = w.id
            LEFT JOIN sets s ON s.workout_exercise_id = we.id
            GROUP BY w.id
            ORDER BY w.id DESC
            LIMIT ?;
            """,
            (limit,)
        ).fetchall()


def get_workout_sets(workout_id: int) -> List[Tuple]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT
                s.id,
                we.exercise,
                s.set_number,
                s.reps,
                s.weight,
                s.implement_count,
                s.quality,
                COALESCE(s.rest_seconds, 0)
            FROM sets s
            JOIN workout_exercises we ON we.id = s.workout_exercise_id
            WHERE we.workout_id = ?
            ORDER BY we.id, s.set_number;
            """,
            (workout_id,)
        ).fetchall()


def get_finisher_log(workout_id: int) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute("SELECT finisher_log FROM workouts WHERE id = ?;", (workout_id,)).fetchone()
        return row[0] if row else None


def get_workout_info(workout_id: int) -> Optional[Tuple]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, started_at, ended_at, day, mood, finisher_log
            FROM workouts
            WHERE id = ?;
            """,
            (workout_id,)
        ).fetchone()
        return row


def search_exercises(day: str, limit: int = 500) -> List[Tuple[str, str]]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT name, equipment_tags
            FROM exercises
            WHERE day = ?
            ORDER BY display_order
            LIMIT ?;
            """,
            (day, limit)
        ).fetchall()


def get_exercise_tags(day: str, exercise_name: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT equipment_tags
            FROM exercises
            WHERE day = ?
              AND name = ?
            LIMIT 1;
            """,
            (day, exercise_name)
        ).fetchone()
        return row[0] if row else None


# ------------------ SUMMARY HELPERS ------------------

def _workout_sets_grouped(workout_id: int) -> Dict[str, List[Dict[str, Any]]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT we.exercise, s.set_number, s.reps, s.weight, s.implement_count, s.quality
            FROM sets s
            JOIN workout_exercises we ON we.id = s.workout_exercise_id
            WHERE we.workout_id = ?
            ORDER BY we.id, s.set_number;
            """,
            (workout_id,)
        ).fetchall()

    out: Dict[str, List[Dict[str, Any]]] = {}
    for ex, set_num, reps, wt, impl, q in rows:
        out.setdefault(ex, []).append(
            {
                "set_number": int(set_num),
                "reps": int(reps),
                "weight": float(wt),
                "implement_count": int(impl),
                "quality": str(q),
            }
        )
    return out


def _exercise_stats(sets: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_sets = len(sets)
    total_reps = sum(s["reps"] for s in sets)
    total_volume = sum(s["reps"] * s["weight"] * s["implement_count"] for s in sets)

    max_weight = max((s["weight"] for s in sets), default=0.0)
    max_weight_impl = 1
    for s in sets:
        if s["weight"] == max_weight:
            max_weight_impl = s["implement_count"]
            break

    # best reps at max weight (within that workout)
    best_reps_at_max_weight = 0
    for s in sets:
        if s["weight"] == max_weight and s["reps"] > best_reps_at_max_weight:
            best_reps_at_max_weight = s["reps"]

    good_great = sum(1 for s in sets if s["quality"] in QUALITY_GOOD)
    bad_ok = total_sets - good_great

    best_set = max(sets, key=lambda s: s["reps"] * s["weight"] * s["implement_count"])
    best_set_volume = best_set["reps"] * best_set["weight"] * best_set["implement_count"]

    # reps distribution for better rules
    reps_below_near = sum(1 for s in sets if s["reps"] < NEAR_TARGET_MIN and s["weight"] > 0)
    reps_below_target = sum(1 for s in sets if s["reps"] < TARGET_REPS and s["weight"] > 0)
    reps_at_or_above_target = sum(1 for s in sets if s["reps"] >= TARGET_REPS)

    avg_reps = (total_reps / total_sets) if total_sets else 0.0

    return {
        "total_sets": total_sets,
        "total_reps": total_reps,
        "avg_reps": avg_reps,
        "total_volume": total_volume,
        "max_weight": max_weight,
        "max_weight_impl": max_weight_impl,
        "best_reps_at_max_weight": best_reps_at_max_weight,
        "good_great_sets": good_great,
        "bad_ok_sets": bad_ok,
        "best_set": best_set,
        "best_set_volume": best_set_volume,
        "reps_below_near": reps_below_near,
        "reps_below_target": reps_below_target,
        "reps_at_or_above_target": reps_at_or_above_target,
    }


def _previous_exercise_stats(before_workout_id: int, exercise_name: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        prev_workout_row = conn.execute(
            """
            SELECT we.workout_id
            FROM workout_exercises we
            WHERE we.exercise = ?
              AND we.workout_id < ?
            ORDER BY we.workout_id DESC
            LIMIT 1;
            """,
            (exercise_name, before_workout_id)
        ).fetchone()

        if not prev_workout_row:
            return None

        prev_workout_id = int(prev_workout_row[0])

        rows = conn.execute(
            """
            SELECT s.set_number, s.reps, s.weight, s.implement_count, s.quality
            FROM sets s
            JOIN workout_exercises we ON we.id = s.workout_exercise_id
            WHERE we.workout_id = ?
              AND we.exercise = ?
            ORDER BY s.set_number;
            """,
            (prev_workout_id, exercise_name)
        ).fetchall()

    sets = [
        {
            "set_number": int(sn),
            "reps": int(reps),
            "weight": float(wt),
            "implement_count": int(impl),
            "quality": str(q),
        }
        for sn, reps, wt, impl, q in rows
    ]

    stats = _exercise_stats(sets)
    stats["workout_id"] = prev_workout_id
    return stats


def _recent_mood_trend(current_workout_id: int, lookback: int = 3) -> List[str]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT mood
            FROM workouts
            WHERE id < ?
            ORDER BY id DESC
            LIMIT ?;
            """,
            (current_workout_id, lookback)
        ).fetchall()
    return [r[0] for r in rows]


def _all_time_prs_for_exercise(exercise_name: str) -> Dict[str, Any]:
    """
    All-time PRs for an exercise across ALL workouts.
    - max_weight (per implement) + reps at that weight best
    - best_set_volume (single set)
    - best_workout_volume (sum volume for that exercise inside a workout)
    """
    with get_conn() as conn:
        # Max weight ever (per implement)
        row_max_w = conn.execute(
            """
            SELECT s.weight, s.implement_count
            FROM sets s
            JOIN workout_exercises we ON we.id = s.workout_exercise_id
            WHERE we.exercise = ?
            ORDER BY s.weight DESC
            LIMIT 1;
            """,
            (exercise_name,)
        ).fetchone()

        max_w = float(row_max_w[0]) if row_max_w else 0.0
        max_w_impl = int(row_max_w[1]) if row_max_w else 1

        # Best reps at that max weight
        row_best_reps = conn.execute(
            """
            SELECT MAX(s.reps)
            FROM sets s
            JOIN workout_exercises we ON we.id = s.workout_exercise_id
            WHERE we.exercise = ?
              AND s.weight = ?;
            """,
            (exercise_name, max_w)
        ).fetchone()
        best_reps_at_max = int(row_best_reps[0]) if row_best_reps and row_best_reps[0] is not None else 0

        # Best set volume ever
        row_best_set = conn.execute(
            """
            SELECT s.weight, s.implement_count, s.reps
            FROM sets s
            JOIN workout_exercises we ON we.id = s.workout_exercise_id
            WHERE we.exercise = ?
            ORDER BY (s.weight * s.implement_count * s.reps) DESC
            LIMIT 1;
            """,
            (exercise_name,)
        ).fetchone()

        if row_best_set:
            bsw = float(row_best_set[0])
            bsi = int(row_best_set[1])
            bsr = int(row_best_set[2])
            best_set_volume = bsw * bsi * bsr
        else:
            bsw, bsi, bsr, best_set_volume = 0.0, 1, 0, 0.0

        # Best workout volume for that exercise (sum across its sets in a workout)
        row_best_workout = conn.execute(
            """
            SELECT we.workout_id,
                   SUM(s.weight * s.implement_count * s.reps) AS vol
            FROM sets s
            JOIN workout_exercises we ON we.id = s.workout_exercise_id
            WHERE we.exercise = ?
            GROUP BY we.workout_id
            ORDER BY vol DESC
            LIMIT 1;
            """,
            (exercise_name,)
        ).fetchone()

        best_workout_id = int(row_best_workout[0]) if row_best_workout else None
        best_workout_volume = float(row_best_workout[1]) if row_best_workout else 0.0

    return {
        "max_weight": max_w,
        "max_weight_impl": max_w_impl,
        "best_reps_at_max_weight": best_reps_at_max,
        "best_set_weight": bsw,
        "best_set_impl": bsi,
        "best_set_reps": bsr,
        "best_set_volume": best_set_volume,
        "best_workout_id": best_workout_id,
        "best_workout_volume": best_workout_volume,
    }


def _good_great_streak_for_exercise(exercise_name: str, up_to_workout_id: int) -> int:
    """
    Streak counts consecutive workouts (ending at up_to_workout_id) where
    every set for that exercise was GOOD or GREAT.
    """
    with get_conn() as conn:
        workout_ids = conn.execute(
            """
            SELECT DISTINCT we.workout_id
            FROM workout_exercises we
            WHERE we.exercise = ?
              AND we.workout_id <= ?
            ORDER BY we.workout_id DESC;
            """,
            (exercise_name, up_to_workout_id)
        ).fetchall()

    if not workout_ids:
        return 0

    streak = 0
    for (wid,) in workout_ids:
        # get qualities for this exercise in that workout
        with get_conn() as conn:
            quals = conn.execute(
                """
                SELECT s.quality
                FROM sets s
                JOIN workout_exercises we ON we.id = s.workout_exercise_id
                WHERE we.exercise = ?
                  AND we.workout_id = ?;
                """,
                (exercise_name, int(wid))
            ).fetchall()

        if not quals:
            continue

        if all(str(q[0]) in QUALITY_GOOD for q in quals):
            streak += 1
        else:
            break

    return streak


# ------------------ SUMMARY (UPGRADED) ------------------

def build_summary(workout_id: int) -> str:
    info = get_workout_info(workout_id)
    if not info:
        return "No workout found."

    _id, started_at, ended_at, day, mood, finisher_log = info
    grouped = _workout_sets_grouped(workout_id)

    if not grouped:
        return (
            f"\n=== Workout Summary ===\n"
            f"{day} | Mood: {mood}\n"
            f"Started: {started_at}\n"
            f"Ended:   {ended_at or '(in progress)'}\n"
            f"\nNo sets logged.\n"
        )

    # Stats for each exercise in THIS workout
    ex_stats: Dict[str, Dict[str, Any]] = {ex: _exercise_stats(sets) for ex, sets in grouped.items()}

    def fmt_weight(w: float, impl: int) -> str:
        return f"{int(w)}x2" if impl == 2 else f"{int(w)}"

    # --- All-time PR section (for exercises you did today) ---
    pr_lines: List[str] = []
    pr_hits: List[str] = []

    for ex, stats in ex_stats.items():
        prs = _all_time_prs_for_exercise(ex)

        # detect "new all-time max weight" (simple: if today's max equals all-time max)
        if stats["max_weight"] > 0 and abs(stats["max_weight"] - prs["max_weight"]) < 1e-9:
            pr_hits.append(f"{ex}: tied/beat all-time max weight — {fmt_weight(prs['max_weight'], prs['max_weight_impl'])} lbs")

        # detect "new best workout volume" for this exercise (if today's total equals all-time best)
        if stats["total_volume"] > 0 and abs(stats["total_volume"] - prs["best_workout_volume"]) < 1e-6:
            pr_hits.append(f"{ex}: new/best all-time workout volume — {int(prs['best_workout_volume'])}")

    # Also show a single "top PR highlight" across today's exercises
    # pick the exercise with the biggest best_set_volume today, and show all-time best set too
    best_set_volume_ex = max(ex_stats.items(), key=lambda kv: kv[1]["best_set_volume"])[0]
    today_best = ex_stats[best_set_volume_ex]["best_set"]
    all_prs = _all_time_prs_for_exercise(best_set_volume_ex)

    pr_lines.append(
        f"Today best set (by volume): {best_set_volume_ex} — "
        f"{fmt_weight(today_best['weight'], today_best['implement_count'])} x {today_best['reps']}"
    )
    if all_prs["best_set_volume"] > 0:
        pr_lines.append(
            f"All-time best set: {best_set_volume_ex} — "
            f"{fmt_weight(all_prs['best_set_weight'], all_prs['best_set_impl'])} x {all_prs['best_set_reps']}"
        )

    # --- Compare vs last time + “did well / improve” ---
    did_well: List[str] = []
    improve: List[str] = []
    comparisons: List[str] = []

    for ex, stats in ex_stats.items():
        # Sets goal
        if stats["total_sets"] < MIN_SETS_GOAL:
            improve.append(f"{ex}: only {stats['total_sets']} sets (goal {MIN_SETS_GOAL}).")

        # Better reps rules
        # - if most sets are below target reps (10), suggest reducing weight or resting more
        if stats["reps_below_target"] >= max(2, stats["total_sets"] // 2):
            improve.append(f"{ex}: lots of sets under {TARGET_REPS} reps — consider slightly lower weight to hit target reps.")
        # - if any sets are far below target (<8), flag as “too heavy” / “form breakdown”
        if stats["reps_below_near"] >= 1:
            improve.append(f"{ex}: at least one set under {NEAR_TARGET_MIN} reps — might be too heavy or fatigue/form drop.")

        # Quality signals
        if stats["good_great_sets"] == stats["total_sets"]:
            did_well.append(f"{ex}: perfect quality — all GOOD/GREAT sets.")
        elif stats["good_great_sets"] >= max(1, stats["total_sets"] - 1):
            did_well.append(f"{ex}: strong quality — mostly GOOD/GREAT sets.")
        elif stats["bad_ok_sets"] >= stats["good_great_sets"]:
            improve.append(f"{ex}: more BAD/OK than GOOD/GREAT — adjust weight/reps/rest to improve quality.")

        # Compare to last time for this exercise
        prev = _previous_exercise_stats(workout_id, ex)
        if prev:
            dv = stats["total_volume"] - prev["total_volume"]
            dw = stats["max_weight"] - prev["max_weight"]
            dr = stats["total_reps"] - prev["total_reps"]

            up = []
            down = []
            if dw > 0: up.append(f"max weight +{int(dw)}")
            if dr > 0: up.append(f"reps +{dr}")
            if dv > 0: up.append(f"volume +{int(dv)}")

            if dw < 0: down.append(f"max weight {int(dw)}")
            if dr < 0: down.append(f"reps {dr}")
            if dv < 0: down.append(f"volume {int(dv)}")

            if up:
                comparisons.append(f"{ex} vs last time (workout #{prev['workout_id']}): " + ", ".join(up) + ".")
                did_well.append(f"{ex}: up from last time ({', '.join(up)}).")
            elif down:
                comparisons.append(f"{ex} vs last time (workout #{prev['workout_id']}): " + ", ".join(down) + ".")
                improve.append(f"{ex}: down vs last time — " + ", ".join(down) + ".")
            else:
                comparisons.append(f"{ex} vs last time (workout #{prev['workout_id']}): about the same.")
        else:
            comparisons.append(f"{ex}: first time logged — baseline created.")

        # Good/Great streak (all sets good/great)
        streak = _good_great_streak_for_exercise(ex, workout_id)
        if streak >= 2:
            did_well.append(f"{ex}: GOOD/GREAT streak — {streak} workouts in a row.")

    # Mood encouragement (simple trend)
    mood_lines: List[str] = []
    recent = _recent_mood_trend(workout_id, lookback=3)
    low_energy_moods = {"Low Energy", "Exhausted"}
    recent_low = sum(1 for m in recent if m in low_energy_moods)

    if mood in low_energy_moods:
        mood_lines.append("You trained on a low-energy day — that’s consistency doing the work.")
    if recent and recent_low >= 2:
        mood_lines.append("Recent trend: multiple low-energy workouts. Consider sleep/recovery and keep intensity flexible.")

    # Finisher
    finisher_lines: List[str] = []
    if finisher_log and finisher_log.strip():
        finisher_lines.append("Finisher:")
        for line in finisher_log.splitlines():
            finisher_lines.append(f"- {line.strip()}")

    # De-dup helper
    def unique_keep_order(items: List[str]) -> List[str]:
        seen = set()
        out = []
        for it in items:
            if it not in seen:
                seen.add(it)
                out.append(it)
        return out

    did_well = unique_keep_order(did_well)
    improve = unique_keep_order(improve)
    comparisons = unique_keep_order(comparisons)
    pr_hits = unique_keep_order(pr_hits)

    # Build output
    lines: List[str] = []
    lines.append("\n=== Workout Summary ===")
    lines.append(f"{day} | Mood: {mood}")
    lines.append(f"Started: {started_at}")
    lines.append(f"Ended:   {ended_at or '(in progress)'}")
    lines.append("")

    lines.append("PRs:")
    for pl in pr_lines:
        lines.append(f"- {pl}")
    for hit in pr_hits[:8]:
        lines.append(f"- {hit}")

    lines.append("")
    lines.append("Compare to last time:")
    for c in comparisons[:12]:
        lines.append(f"- {c}")

    lines.append("")
    lines.append("Things you did well:")
    for d in did_well[:10]:
        lines.append(f"- {d}")

    lines.append("")
    lines.append("Things to improve:")
    if improve:
        for im in improve[:10]:
            lines.append(f"- {im}")
    else:
        lines.append("- Nothing obvious — keep building momentum.")

    if mood_lines:
        lines.append("")
        for ml in mood_lines:
            lines.append(f"* {ml}")

    if finisher_lines:
        lines.append("")
        lines.extend(finisher_lines)

    lines.append("")
    return "\n".join(lines)
