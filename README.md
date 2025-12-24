\# Workout Tracker (CLI) — Python + SQLite



A command-line workout tracker that logs workouts, exercises, and sets to a SQLite database and generates an end-of-workout summary with PRs, streaks, and improvement suggestions.



\## Features

\- Log workouts by day + mood

\- Pick exercises from a curated list (seeded in-order)

\- Track sets: weight (0 = bodyweight), reps, quality (bad/ok/good/great)

\- Dumbbell-aware logging (defaults to pair when tagged dumbbell)

\- Optional finisher: add multiple items (cardio/core/stretching), default 10 minutes

\- Edit/delete sets

\- End-of-workout summary:

&nbsp; - All-time PRs per exercise (max weight, best set volume, best workout volume)

&nbsp; - Good/Great streaks (consecutive workouts where all sets were good/great)

&nbsp; - Compare vs last time (volume/weight/reps deltas)

&nbsp; - Improvement rules (e.g., under-target reps, <3 sets)



\## Tech Stack

\- Python 3.x

\- SQLite (built-in `sqlite3`)

\- No external dependencies (simple and portable)



\## Run Locally

```bash

python workout\_app.py



