# Workout Tracker (CLI) — Python + SQLite

A command-line workout tracker that logs workouts, exercises, and sets to a SQLite database and generates end-of-workout summaries including PRs, streaks, and improvement suggestions.

## Why This Project
I built this project to practice designing a real-world, data-driven application with persistent storage, analytics, and rule-based feedback — similar to how production systems track user activity and generate insights over time.

## Backend Concepts Demonstrated
- Relational data modeling (workouts, exercises, sets)
- CRUD operations with persistent storage
- Analytics and aggregation logic
- Business rules and conditional recommendations
- Separation of concerns (database logic vs application logic)

## Design Decisions
- SQLite was chosen for simplicity and portability while maintaining relational integrity.
- A CLI interface keeps the focus on backend logic and data modeling.
- Analytics are computed dynamically rather than stored to avoid data inconsistency.

## Features
- Log workouts by day and mood
- Pick exercises from a curated, seeded list
- Track sets: weight (0 = bodyweight), reps, and quality (bad/ok/good/great)
- Dumbbell-aware logging (defaults to pair when tagged dumbbell)
- Optional finisher: multiple items (cardio/core/stretching), default 10 minutes
- Edit and delete sets
- End-of-workout summary:
  - All-time PRs per exercise (max weight, best set volume, best workout volume)
  - Good/Great streaks (consecutive workouts with high-quality sets)
  - Comparison vs previous workout (volume, weight, reps)
  - Improvement rules (e.g., under-target reps, fewer than 3 sets)

## Tech Stack
- Python 3.x
- SQLite (built-in `sqlite3`)
- No external dependencies

## Run Locally
```bash
python workout_app.py
