import calendar

from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods

from .models import Workout, Exercise, SetEntry


DAYS = ["Back & Biceps", "Chest & Triceps", "Legs", "Core", "Shoulders & Traps", "Combination"]
MOODS = ["Exhausted", "Low Energy", "Normal", "Energetic"]
QUALITIES = ["bad", "ok", "good", "great"]


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        password_confirm = request.POST.get("password_confirm", "").strip()

        errors = []

        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters long.")

        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")

        if password != password_confirm:
            errors.append("Passwords do not match.")

        if User.objects.filter(username=username).exists():
            errors.append("Username already taken.")

        if not errors:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect("dashboard")

        return render(request, "registration/register.html", {"errors": errors, "username": username})

    return render(request, "registration/register.html")


@login_required
def dashboard(request):
    recent_qs = Workout.objects.filter(user=request.user).order_by("-started_at")

    top3 = list(recent_qs[:3])
    rest = list(recent_qs[3:50])  # keep it reasonable for UI

    today = timezone.localdate()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    cal = calendar.Calendar(firstweekday=6)  # Sunday start
    weeks = cal.monthdatescalendar(year, month)

    start = weeks[0][0]
    end = weeks[-1][-1]

    workout_days = set(
        Workout.objects.filter(
            user=request.user,
            started_at__date__gte=start,
            started_at__date__lte=end,
        ).values_list("started_at__date", flat=True)
    )

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    return render(
        request,
        "dashboard.html",
        {
            "top3": top3,
            "rest": rest,
            "weeks": weeks,
            "workout_days": workout_days,
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
        },
    )


@login_required
def start_workout(request):
    if request.method == "POST":
        day = request.POST.get("day")
        mood = request.POST.get("mood")

        if day in DAYS and mood in MOODS:
            w = Workout.objects.create(user=request.user, day=day, mood=mood)
            return redirect("workout_detail", workout_id=w.id)

    return render(request, "start_workout.html", {"days": DAYS, "moods": MOODS})


@login_required
def workout_detail(request, workout_id: int):
    w = get_object_or_404(Workout, id=workout_id, user=request.user)
    # Show all exercises for Combination day, otherwise filter by day
    if w.day == "Combination":
        exercises = Exercise.objects.all()  # ordered by model Meta sort_order
    else:
        exercises = Exercise.objects.filter(day=w.day)  # ordered by model Meta sort_order
    sets = w.sets.select_related("exercise").all()

    if request.method == "POST":
        exercise_id = (request.POST.get("exercise_id") or "").strip()
        weight_lb = (request.POST.get("weight_lb") or "").strip()
        reps = (request.POST.get("reps") or "").strip()
        quality = (request.POST.get("quality") or "").strip()

        if not exercise_id.isdigit():
            return HttpResponseBadRequest("Invalid exercise")
        if not weight_lb.isdigit():
            return HttpResponseBadRequest("Invalid weight")
        if not reps.isdigit():
            return HttpResponseBadRequest("Invalid reps")
        if quality not in QUALITIES:
            return HttpResponseBadRequest("Invalid quality")

        ex = get_object_or_404(Exercise, id=int(exercise_id))
        weight_lb_i = int(weight_lb)  # no cap
        reps_i = int(reps)

        next_set_num = SetEntry.objects.filter(workout=w, exercise=ex).count() + 1

        SetEntry.objects.create(
            workout=w,
            exercise=ex,
            set_number=next_set_num,
            weight_lb=weight_lb_i,
            reps=reps_i,
            quality=quality,
        )
        return redirect("workout_detail", workout_id=w.id)

    return render(
        request,
        "workout_detail.html",
        {"workout": w, "exercises": exercises, "sets": sets, "qualities": QUALITIES},
    )


@login_required
def end_workout(request, workout_id: int):
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    if not w.ended_at:
        w.ended_at = timezone.now()
        w.save()

    total_sets = w.sets.count()
    good_great = w.sets.filter(quality__in=["good", "great"]).count()

    # Analysis section
    analysis = generate_workout_analysis(w, request.user)

    return render(
        request,
        "summary.html",
        {
            "workout": w,
            "total_sets": total_sets,
            "good_great": good_great,
            "analysis": analysis,
        },
    )


def generate_workout_analysis(current_workout, user):
    """Generate comprehensive workout analysis with PRs, streaks, improvements, and motivation."""
    analysis = {
        "prs": [],
        "improvements": [],
        "areas_to_improve": [],
        "streaks": [],
        "motivation": "",
    }

    # Get all sets from current workout grouped by exercise
    from django.db.models import Max, Sum, Count, Q

    current_sets = current_workout.sets.select_related("exercise").all()

    # Calculate PRs for each exercise in this workout
    exercises_in_workout = set(s.exercise for s in current_sets)

    for exercise in exercises_in_workout:
        exercise_sets = [s for s in current_sets if s.exercise == exercise]

        # Get historical data for this exercise
        all_time_sets = SetEntry.objects.filter(
            workout__user=user, exercise=exercise, workout__ended_at__isnull=False
        ).exclude(workout=current_workout)

        if exercise_sets:
            # Max weight PR
            current_max_weight = max(s.weight_lb for s in exercise_sets)
            historical_max = (
                all_time_sets.aggregate(Max("weight_lb"))["weight_lb__max"] or 0
            )

            if current_max_weight > historical_max:
                analysis["prs"].append(
                    f"🏆 New max weight PR for {exercise.name}: {current_max_weight} lb!"
                )

            # Max reps PR (at any weight)
            current_max_reps = max(s.reps for s in exercise_sets)
            historical_max_reps = all_time_sets.aggregate(Max("reps"))["reps__max"] or 0

            if current_max_reps > historical_max_reps:
                analysis["prs"].append(
                    f"🏆 New max reps PR for {exercise.name}: {current_max_reps} reps!"
                )

            # Total volume PR for this exercise in a single workout
            current_volume = sum(s.weight_lb * s.reps for s in exercise_sets)

            # Get previous workout volumes for this exercise (manually calculate per workout)
            previous_workouts_for_exercise = (
                all_time_sets.values_list("workout_id", flat=True).distinct()
            )

            previous_volumes = []
            for workout_id in previous_workouts_for_exercise:
                workout_sets = all_time_sets.filter(workout_id=workout_id)
                workout_volume = sum(s.weight_lb * s.reps for s in workout_sets)
                previous_volumes.append(workout_volume)

            if previous_volumes:
                max_previous_volume = max(previous_volumes)
                if current_volume > max_previous_volume:
                    analysis["prs"].append(
                        f"🏆 New volume PR for {exercise.name}: {current_volume} total volume!"
                    )

    # Compare to previous workout
    previous_workouts = (
        Workout.objects.filter(user=user, ended_at__isnull=False)
        .exclude(id=current_workout.id)
        .order_by("-ended_at")[:5]
    )

    # Get current workout stats for comparison
    total_sets = current_workout.sets.count()
    good_great = current_workout.sets.filter(quality__in=["good", "great"]).count()

    if previous_workouts:
        last_workout = previous_workouts[0]

        # Compare total sets
        last_total_sets = last_workout.sets.count()
        if total_sets > last_total_sets:
            analysis["improvements"].append(
                f"📈 Increased total sets from {last_total_sets} to {total_sets}"
            )

        # Compare good/great quality sets
        last_good = last_workout.sets.filter(quality__in=["good", "great"]).count()
        if good_great > last_good:
            analysis["improvements"].append(
                f"📈 Improved quality sets from {last_good} to {good_great}"
            )

        # Check for exercises where weight increased
        for exercise in exercises_in_workout:
            current_ex_sets = [s for s in current_sets if s.exercise == exercise]
            last_ex_sets = last_workout.sets.filter(exercise=exercise)

            if last_ex_sets.exists() and current_ex_sets:
                current_avg = sum(s.weight_lb for s in current_ex_sets) / len(
                    current_ex_sets
                )
                last_avg = (
                    last_ex_sets.aggregate(avg=Sum("weight_lb"))["avg"]
                    / last_ex_sets.count()
                )

                if current_avg > last_avg:
                    analysis["improvements"].append(
                        f"💪 Increased average weight for {exercise.name}"
                    )

    # Areas to improve
    low_quality_sets = current_workout.sets.filter(quality__in=["bad", "ok"])
    if low_quality_sets.exists():
        low_q_count = low_quality_sets.count()
        analysis["areas_to_improve"].append(
            f"⚠️ {low_q_count} sets rated as 'bad' or 'ok' - focus on form and recovery"
        )

    # Check for exercises with declining reps
    for exercise in exercises_in_workout:
        exercise_sets_ordered = sorted(
            [s for s in current_sets if s.exercise == exercise],
            key=lambda x: x.set_number,
        )
        if len(exercise_sets_ordered) >= 3:
            if (
                exercise_sets_ordered[-1].reps < exercise_sets_ordered[0].reps * 0.6
            ):  # 40% drop
                analysis["areas_to_improve"].append(
                    f"⚠️ {exercise.name}: Significant rep drop across sets - consider reducing weight or longer rest"
                )

    # Check quality streaks
    recent_workouts = list(previous_workouts[:5])
    if recent_workouts:
        streak_count = 0
        for workout in [current_workout] + recent_workouts:
            good_pct = (
                workout.sets.filter(quality__in=["good", "great"]).count()
                / max(workout.sets.count(), 1)
            )
            if good_pct >= 0.7:  # 70% good/great
                streak_count += 1
            else:
                break

        if streak_count >= 3:
            analysis["streaks"].append(
                f"🔥 {streak_count} workout streak with 70%+ quality sets!"
            )

    # Motivational message based on mood and performance
    mood = current_workout.mood
    quality_pct = good_great / max(total_sets, 1)

    if mood in ["Exhausted", "Low Energy"] and quality_pct >= 0.6:
        analysis["motivation"] = (
            "💪 Amazing work pushing through despite low energy! Your dedication is impressive. "
            "Make sure to prioritize rest and recovery - you've earned it!"
        )
    elif mood in ["Exhausted", "Low Energy"]:
        analysis["motivation"] = (
            "🌟 Great job showing up even when energy was low! Remember, consistency matters more than perfection. "
            "Rest well and come back stronger!"
        )
    elif quality_pct >= 0.8 and total_sets >= 10:
        analysis["motivation"] = (
            "🎉 Outstanding performance! You absolutely crushed this workout! "
            "This is the kind of effort that builds champions. Keep this momentum going!"
        )
    elif quality_pct >= 0.7:
        analysis["motivation"] = (
            "👏 Solid workout! You're making consistent progress. "
            "Keep focusing on quality over quantity and the results will follow!"
        )
    elif analysis["prs"]:
        analysis["motivation"] = (
            "🏆 New personal records! Your hard work is paying off. "
            "Celebrate these wins and keep pushing your limits!"
        )
    else:
        analysis["motivation"] = (
            "✨ Every workout is progress! You showed up and put in the work. "
            "Keep building on this foundation and trust the process!"
        )

    # Check recent mood trend for additional encouragement
    recent_moods = [w.mood for w in recent_workouts[:3]]
    if recent_moods.count("Exhausted") >= 2 or recent_moods.count("Low Energy") >= 2:
        analysis["motivation"] += (
            " (Your recent workouts show low energy - consider taking an extra rest day or adjusting intensity.)"
        )

    return analysis


@login_required
def edit_set(request, set_id: int):
    s = get_object_or_404(SetEntry, id=set_id, workout__user=request.user)
    w = s.workout

    if request.method == "POST":
        weight_lb = (request.POST.get("weight_lb") or "").strip()
        reps = (request.POST.get("reps") or "").strip()
        quality = (request.POST.get("quality") or "").strip()

        if not weight_lb.isdigit():
            return HttpResponseBadRequest("Invalid weight")
        if not reps.isdigit():
            return HttpResponseBadRequest("Invalid reps")
        if quality not in QUALITIES:
            return HttpResponseBadRequest("Invalid quality")

        s.weight_lb = int(weight_lb)  # no cap
        s.reps = int(reps)
        s.quality = quality
        s.save()

        return redirect("workout_detail", workout_id=w.id)

    return render(request, "edit_set.html", {"set": s, "qualities": QUALITIES})


@login_required
@require_http_methods(["POST"])
def delete_set(request, set_id: int):
    s = get_object_or_404(SetEntry, id=set_id, workout__user=request.user)
    workout_id = s.workout.id
    s.delete()
    return redirect("workout_detail", workout_id=workout_id)


@login_required
@require_http_methods(["GET", "POST"])
def delete_workout(request, workout_id: int):
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    if request.method == "POST":
        w.delete()  # cascades => deletes SetEntry rows
        return redirect("dashboard")

    return render(
        request,
        "delete_workout.html",
        {"workout": w, "set_count": w.sets.count()},
    )


def about(request):
    """About page explaining the app and workout recommendations"""
    return render(request, "about.html")
