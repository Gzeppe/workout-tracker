import calendar
import re

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from .models import (
    Workout,
    Exercise,
    SetEntry,
    ScheduledWorkout,
    WorkoutTemplate,
    TemplateExercise,
    HIITSession,
    UserProfile,
)


DAYS = ["Back & Biceps", "Chest & Triceps", "Legs", "Core", "Shoulders & Traps", "Other"]
MOODS = ["Exhausted", "Low Energy", "Normal", "Energetic"]
QUALITIES = ["bad", "ok", "good", "great"]
WORKOUT_TYPES = ["weightlifting", "cardio", "hiit"]
CARDIO_TYPES = ["running", "cycling", "swimming", "rowing", "elliptical", "stair_climber", "jump_rope", "walking", "other"]

# Maps quality rating → difficulty score (higher = harder/worse)
QUALITY_DIFFICULTY = {"bad": 4, "ok": 3, "good": 2, "great": 1}

FATIGUE_KEYWORDS = frozenset({
    "fatigue", "tired", "exhausted", "sore", "sick", "sleep", "stressed",
    "stiff", "pain", "weak", "drained", "rough", "awful",
})

INJURY_KEYWORDS = frozenset({
    "injury", "injured", "hurt", "sprain", "strain", "pulled", "tweaked",
    "sharp", "ache", "aching", "swollen", "inflammation", "tendon", "ligament",
})

TIME_LIMIT_KEYWORDS = frozenset({
    "rushed", "short", "quick", "time", "late", "early", "cut", "limited",
    "busy", "hurried", "fast", "couldn't", "skip", "skipped",
})


def ratelimited_error(request, exception):
    """Custom view for rate limited requests"""
    return render(request, "ratelimited.html", status=429)


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        password_confirm = request.POST.get("password_confirm", "").strip()

        errors = []

        # Username validation
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters long.")
        elif len(username) > 30:
            errors.append("Username cannot exceed 30 characters.")
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append("Username can only contain letters, numbers, and underscores.")

        # Email validation
        if not email:
            errors.append("Email address is required.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Please enter a valid email address.")
            else:
                if User.objects.filter(email=email).exists():
                    errors.append("This email is already registered.")

        # Password validation
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        else:
            try:
                # Use Django's password validators
                validate_password(password)
            except ValidationError as e:
                errors.extend(e.messages)

        if password != password_confirm:
            errors.append("Passwords do not match.")

        if User.objects.filter(username=username).exists():
            errors.append("Username already taken.")

        if not errors:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect("dashboard")

        return render(request, "registration/register.html", {"errors": errors, "username": username, "email": email})

    return render(request, "registration/register.html")


@login_required
def dashboard(request):
    """New menu-based dashboard with quick stats"""
    user = request.user
    today = timezone.localdate()

    # Quick stats
    week_start = today - timedelta(days=today.weekday())
    this_week_count = Workout.objects.filter(
        user=user,
        ended_at__isnull=False,
        started_at__date__gte=week_start,
    ).count()

    # Calculate workout streak
    streak = calculate_workout_streak(user)

    # Recent PRs (last 30 days)
    recent_prs = count_recent_prs(user)

    # Upcoming scheduled workouts (next 7 days)
    upcoming_scheduled = ScheduledWorkout.objects.filter(
        user=user,
        scheduled_date__gte=today,
        scheduled_date__lte=today + timedelta(days=7),
        completed=False,
    )[:3]

    # User's templates for quick start
    templates = WorkoutTemplate.objects.filter(user=user)[:6]

    # Last completed workout for dashboard summary card
    last_workout = (
        Workout.objects.filter(user=user, ended_at__isnull=False)
        .order_by("-ended_at")
        .first()
    )

    return render(
        request,
        "dashboard.html",
        {
            "this_week_count": this_week_count,
            "streak": streak,
            "recent_prs": recent_prs,
            "upcoming_scheduled": upcoming_scheduled,
            "templates": templates,
            "last_workout": last_workout,
        },
    )


def calculate_workout_streak(user):
    """Calculate consecutive days with completed workouts"""
    today = timezone.localdate()
    streak = 0
    current_date = today

    while True:
        has_workout = Workout.objects.filter(
            user=user,
            ended_at__isnull=False,
            started_at__date=current_date,
        ).exists()

        if has_workout:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            # Allow one day gap (rest day)
            if current_date == today:
                current_date -= timedelta(days=1)
                continue
            break

    return streak


def count_recent_prs(user):
    """Count PRs achieved in the last 30 days (simplified)"""
    # This is a simplified count - just count workouts with good performance
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_workouts = Workout.objects.filter(
        user=user,
        ended_at__isnull=False,
        ended_at__gte=thirty_days_ago,
    )

    # Count workouts where most sets were "good" or "great"
    pr_count = 0
    for workout in recent_workouts:
        total_sets = workout.sets.count()
        if total_sets > 0:
            good_sets = workout.sets.filter(quality__in=["good", "great"]).count()
            if good_sets / total_sets >= 0.8:
                pr_count += 1

    return pr_count


@login_required
def select_workout_type(request):
    """Workout type selection page"""
    templates = WorkoutTemplate.objects.filter(user=request.user)[:6]
    return render(request, "workout/select_type.html", {"templates": templates})


@login_required
def start_weightlifting(request):
    """Start a weightlifting workout"""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        day = request.POST.get("day")
        mood = request.POST.get("mood")
        template_id = request.POST.get("template_id", "").strip()

        if day in DAYS and mood in MOODS:
            template = None
            if template_id and template_id.isdigit():
                template = WorkoutTemplate.objects.filter(
                    id=int(template_id), user=request.user
                ).first()

            w = Workout.objects.create(
                user=request.user,
                workout_type="weightlifting",
                name=name,
                day=day,
                mood=mood,
                template=template,
            )

            # Pre-populate exercise logs from template
            if template:
                position = 0
                for template_exercise in template.exercises.order_by("position"):
                    # Create sets based on target_sets from template
                    for set_num in range(1, template_exercise.target_sets + 1):
                        SetEntry.objects.create(
                            workout=w,
                            exercise=template_exercise.exercise,
                            custom_exercise_name=template_exercise.custom_exercise_name,
                            custom_equipment=template_exercise.custom_equipment,
                            set_number=set_num,
                            weight_lb=0,  # User must fill in
                            reps=0,  # User must fill in
                            quality="ok",  # Default quality, user can change
                            position=position,
                        )
                        position += 1

            return redirect("workout_detail", workout_id=w.id)

    templates = WorkoutTemplate.objects.filter(
        user=request.user, workout_type="weightlifting"
    )
    return render(
        request,
        "workout/start_weightlifting.html",
        {"days": DAYS, "moods": MOODS, "templates": templates},
    )


@login_required
def start_cardio(request):
    """Start a cardio workout"""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        cardio_type = request.POST.get("cardio_type", "").strip()
        equipment = request.POST.get("equipment", "").strip()
        target_duration = request.POST.get("target_duration", "0").strip()
        target_distance = request.POST.get("target_distance", "0").strip()
        mood = request.POST.get("mood")

        if cardio_type in CARDIO_TYPES and mood in MOODS:
            try:
                target_duration_int = int(target_duration) if target_duration else 0
                target_distance_dec = Decimal(target_distance) if target_distance else Decimal("0")
            except (ValueError, InvalidOperation):
                target_duration_int = 0
                target_distance_dec = Decimal("0")

            w = Workout.objects.create(
                user=request.user,
                workout_type="cardio",
                name=name,
                mood=mood,
                cardio_type=cardio_type,
                cardio_equipment=equipment,
                target_duration_minutes=target_duration_int,
                target_distance_miles=target_distance_dec,
            )
            return redirect("cardio_workout_detail", workout_id=w.id)

    cardio_type_choices = Workout.CARDIO_TYPE_CHOICES
    return render(
        request,
        "workout/start_cardio.html",
        {"cardio_types": cardio_type_choices, "moods": MOODS},
    )


@login_required
def start_hiit(request):
    """Start a HIIT workout"""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        mood = request.POST.get("mood")
        intervals = request.POST.get("intervals", "8").strip()
        work_duration = request.POST.get("work_duration", "30").strip()
        rest_duration = request.POST.get("rest_duration", "15").strip()

        if mood in MOODS:
            try:
                intervals_int = int(intervals) if intervals else 8
                work_int = int(work_duration) if work_duration else 30
                rest_int = int(rest_duration) if rest_duration else 15
            except ValueError:
                intervals_int, work_int, rest_int = 8, 30, 15

            w = Workout.objects.create(
                user=request.user,
                workout_type="hiit",
                name=name or "HIIT Session",
                mood=mood,
            )

            HIITSession.objects.create(
                workout=w,
                total_intervals=intervals_int,
                work_duration=work_int,
                rest_duration=rest_int,
            )

            return redirect("hiit_workout_detail", workout_id=w.id)

    return render(
        request,
        "workout/start_hiit.html",
        {"moods": MOODS},
    )


@login_required
def start_workout(request):
    """Legacy redirect to workout type selection"""
    return redirect("select_workout_type")


@login_required
def workout_detail(request, workout_id: int):
    """Route to appropriate workout detail view based on type"""
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    # If workout is already completed, show summary instead of active workout view
    if w.ended_at:
        return end_workout(request, workout_id)

    if w.workout_type == "cardio":
        return cardio_workout_detail(request, workout_id)
    elif w.workout_type == "hiit":
        return hiit_workout_detail(request, workout_id)
    else:
        return weightlifting_workout_detail(request, workout_id)


@login_required
def weightlifting_workout_detail(request, workout_id: int):
    """Weightlifting workout detail page"""
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    # Custom Workout / Other: no exercise dropdown, user types exercise name
    # Other days: filter exercises by day
    is_custom = w.day in ("Custom Workout", "Other")
    if is_custom:
        exercises = []
    else:
        exercises = Exercise.objects.filter(day=w.day)
    sets = w.sets.select_related("exercise").order_by("position", "created_at")

    return render(
        request,
        "workout/detail_weightlifting.html",
        {"workout": w, "exercises": exercises, "sets": sets, "qualities": QUALITIES, "is_custom": is_custom},
    )


@login_required
def cardio_workout_detail(request, workout_id: int):
    """Cardio workout detail page"""
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    # Get logged cardio intervals/entries
    entries = w.sets.order_by("position", "created_at")

    # Calculate totals
    total_duration = sum(e.duration_seconds for e in entries)
    total_distance = sum(e.distance_miles for e in entries)
    avg_speed = (
        sum(e.speed_mph for e in entries) / len(entries)
        if entries
        else Decimal("0")
    )

    return render(
        request,
        "workout/detail_cardio.html",
        {
            "workout": w,
            "entries": entries,
            "qualities": QUALITIES,
            "total_duration": total_duration,
            "total_distance": total_distance,
            "avg_speed": avg_speed,
        },
    )


@login_required
def hiit_workout_detail(request, workout_id: int):
    """HIIT workout detail page with interval timer"""
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    # Get or create HIIT session
    hiit_session, created = HIITSession.objects.get_or_create(
        workout=w,
        defaults={
            "total_intervals": 8,
            "work_duration": 30,
            "rest_duration": 15,
        },
    )

    return render(
        request,
        "workout/detail_hiit.html",
        {
            "workout": w,
            "hiit_session": hiit_session,
        },
    )


@login_required
@require_http_methods(["POST"])
def add_set(request, workout_id: int):
    """HTMX endpoint for adding a set without full page reload"""
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    exercise_id = (request.POST.get("exercise_id") or "").strip()
    custom_exercise_name = (request.POST.get("custom_exercise_name") or "").strip()
    custom_equipment = (request.POST.get("custom_equipment") or "").strip()
    weight_lb = (request.POST.get("weight_lb") or "").strip()
    reps = (request.POST.get("reps") or "").strip()
    quality = (request.POST.get("quality") or "").strip()
    duration_minutes = (request.POST.get("duration_minutes") or "0").strip()

    # Determine if using custom exercise or dropdown selection
    # Priority: custom_exercise_name takes precedence over exercise_id
    ex = None
    use_custom = bool(custom_exercise_name)

    if not use_custom:
        # No custom name entered, must use dropdown (unless Custom Workout day)
        if w.day in ("Custom Workout", "Other"):
            return HttpResponseBadRequest("Exercise name required")
        if not exercise_id.isdigit():
            return HttpResponseBadRequest("Please enter an exercise name or select from the list")
        ex = get_object_or_404(Exercise, id=int(exercise_id))

    if not weight_lb.isdigit():
        return HttpResponseBadRequest("Invalid weight")
    if not reps.isdigit():
        return HttpResponseBadRequest("Invalid reps")
    if quality not in QUALITIES:
        return HttpResponseBadRequest("Invalid quality")
    if duration_minutes and not duration_minutes.isdigit():
        return HttpResponseBadRequest("Invalid duration")

    weight_lb_i = int(weight_lb)
    reps_i = int(reps)
    duration_seconds = int(duration_minutes) * 60 if duration_minutes else 0

    # Calculate set number based on exercise name (custom or linked)
    if use_custom:
        next_set_num = SetEntry.objects.filter(workout=w, custom_exercise_name=custom_exercise_name).count() + 1
    else:
        next_set_num = SetEntry.objects.filter(workout=w, exercise=ex).count() + 1

    max_position = w.sets.count()

    SetEntry.objects.create(
        workout=w,
        exercise=ex,
        custom_exercise_name=custom_exercise_name if use_custom else "",
        custom_equipment=custom_equipment if use_custom else "",
        set_number=next_set_num,
        weight_lb=weight_lb_i,
        reps=reps_i,
        duration_seconds=duration_seconds,
        quality=quality,
        position=max_position,
    )

    # Return partial template with updated sets list
    sets = w.sets.select_related("exercise").order_by("position", "created_at")
    return render(request, "partials/sets_list.html", {"sets": sets, "workout": w})


@login_required
@require_http_methods(["POST"])
def add_cardio_entry(request, workout_id: int):
    """HTMX endpoint for adding a cardio interval/entry"""
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    duration_minutes = request.POST.get("duration_minutes", "0").strip()
    distance = request.POST.get("distance", "0").strip()
    speed = request.POST.get("speed", "0").strip()
    incline = request.POST.get("incline", "0").strip()
    quality = request.POST.get("quality", "good").strip()

    try:
        duration_seconds = int(duration_minutes) * 60 if duration_minutes else 0
        distance_dec = Decimal(distance) if distance else Decimal("0")
        speed_dec = Decimal(speed) if speed else Decimal("0")
        incline_dec = Decimal(incline) if incline else Decimal("0")
    except (ValueError, InvalidOperation):
        return HttpResponseBadRequest("Invalid input values")

    if quality not in QUALITIES:
        quality = "good"

    max_position = w.sets.count()
    set_number = max_position + 1

    SetEntry.objects.create(
        workout=w,
        custom_exercise_name=w.get_cardio_type_display() if w.cardio_type else "Cardio",
        set_number=set_number,
        weight_lb=0,
        reps=0,
        duration_seconds=duration_seconds,
        distance_miles=distance_dec,
        speed_mph=speed_dec,
        incline_percent=incline_dec,
        quality=quality,
        position=max_position,
    )

    # Return updated entries list
    entries = w.sets.order_by("position", "created_at")
    total_duration = sum(e.duration_seconds for e in entries)
    total_distance = sum(e.distance_miles for e in entries)
    avg_speed = (
        sum(e.speed_mph for e in entries) / len(entries)
        if entries
        else Decimal("0")
    )

    return render(
        request,
        "partials/cardio_entries.html",
        {
            "entries": entries,
            "workout": w,
            "total_duration": total_duration,
            "total_distance": total_distance,
            "avg_speed": avg_speed,
        },
    )


@login_required
@require_http_methods(["POST"])
def update_hiit_session(request, workout_id: int):
    """Update HIIT session progress"""
    w = get_object_or_404(Workout, id=workout_id, user=request.user)
    hiit_session = get_object_or_404(HIITSession, workout=w)

    intervals_completed = request.POST.get("intervals_completed", "0").strip()
    total_work_time = request.POST.get("total_work_time", "0").strip()
    total_rest_time = request.POST.get("total_rest_time", "0").strip()

    try:
        hiit_session.intervals_completed = int(intervals_completed)
        hiit_session.total_work_time = int(total_work_time)
        hiit_session.total_rest_time = int(total_rest_time)
        hiit_session.save()
    except ValueError:
        pass

    return render(
        request,
        "partials/hiit_progress.html",
        {"hiit_session": hiit_session, "workout": w},
    )


@login_required
def end_workout(request, workout_id: int):
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    if not w.ended_at:
        w.ended_at = timezone.now()
        w.save()

    total_sets = w.sets.count()
    good_great = w.sets.filter(quality__in=["good", "great"]).count()

    # Type-specific data
    cardio_stats = None
    hiit_stats = None

    if w.workout_type == "cardio":
        entries = w.sets.all()
        cardio_stats = {
            "total_duration": sum(e.duration_seconds for e in entries),
            "total_distance": sum(e.distance_miles for e in entries),
            "avg_speed": (
                sum(e.speed_mph for e in entries) / len(entries)
                if entries
                else Decimal("0")
            ),
            "avg_incline": (
                sum(e.incline_percent for e in entries) / len(entries)
                if entries
                else Decimal("0")
            ),
        }
    elif w.workout_type == "hiit":
        try:
            hiit_session = w.hiit_session
            hiit_stats = {
                "intervals_completed": hiit_session.intervals_completed,
                "total_intervals": hiit_session.total_intervals,
                "total_work_time": hiit_session.total_work_time,
                "total_rest_time": hiit_session.total_rest_time,
                "work_duration": hiit_session.work_duration,
                "rest_duration": hiit_session.rest_duration,
            }
        except HIITSession.DoesNotExist:
            pass

    # Analysis section (for weightlifting)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    analysis = None
    if w.workout_type == "weightlifting":
        analysis = generate_workout_analysis(w, request.user, adaptive=profile.adaptive_programming)

    return render(
        request,
        "workout/summary.html",
        {
            "workout": w,
            "total_sets": total_sets,
            "good_great": good_great,
            "analysis": analysis,
            "cardio_stats": cardio_stats,
            "hiit_stats": hiit_stats,
            "adaptive_enabled": profile.adaptive_programming,
        },
    )


@login_required
@require_http_methods(["POST"])
def save_workout_notes(request, workout_id: int):
    """Save end-of-session notes for a completed workout."""
    w = get_object_or_404(Workout, id=workout_id, user=request.user)
    w.notes = request.POST.get("notes", "").strip()
    w.save(update_fields=["notes"])
    return redirect("end_workout", workout_id=workout_id)


@login_required
@require_http_methods(["POST"])
def save_warmup(request, workout_id: int):
    w = get_object_or_404(Workout, id=workout_id, user=request.user)
    duration = request.POST.get("warmup_duration", "0").strip()
    w.warmup_duration_minutes = int(duration) if duration.isdigit() else 0
    w.warmup_notes = request.POST.get("warmup_notes", "").strip()
    w.save(update_fields=["warmup_duration_minutes", "warmup_notes"])
    dur = w.warmup_duration_minutes
    preview = (w.warmup_notes[:60] + "…") if len(w.warmup_notes) > 60 else w.warmup_notes
    html = (
        f'<div id="warmup-saved" class="flex items-center gap-2 px-4 py-3 rounded-xl '
        f'bg-[#AEFF00]/10 border border-[#AEFF00]/30 text-[#AEFF00] text-sm font-semibold">'
        f'<span>✓ Warmup logged</span>'
        f'<span class="text-[#AEFF00]/60 font-normal">— {dur} min'
        f'{": " + preview if preview else ""}</span></div>'
    )
    return HttpResponse(html)


@login_required
@require_http_methods(["POST"])
def save_finisher(request, workout_id: int):
    w = get_object_or_404(Workout, id=workout_id, user=request.user)
    duration = request.POST.get("finisher_duration", "0").strip()
    w.finisher_duration_minutes = int(duration) if duration.isdigit() else 0
    w.finisher_notes = request.POST.get("finisher_notes", "").strip()
    w.save(update_fields=["finisher_duration_minutes", "finisher_notes"])
    dur = w.finisher_duration_minutes
    preview = (w.finisher_notes[:60] + "…") if len(w.finisher_notes) > 60 else w.finisher_notes
    html = (
        f'<div id="finisher-saved" class="flex items-center gap-2 px-4 py-3 rounded-xl '
        f'bg-[#AEFF00]/10 border border-[#AEFF00]/30 text-[#AEFF00] text-sm font-semibold">'
        f'<span>✓ Finisher logged</span>'
        f'<span class="text-[#AEFF00]/60 font-normal">— {dur} min'
        f'{": " + preview if preview else ""}</span></div>'
    )
    return HttpResponse(html)


@login_required
@require_http_methods(["POST"])
def toggle_adaptive_programming(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.adaptive_programming = not profile.adaptive_programming
    profile.save()
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)


def generate_workout_analysis(current_workout, user, adaptive=False):
    """
    Generate comprehensive workout analysis including PRs, volume trends,
    strength progression, quality/RPE patterns, and contextual feedback tips.

    Returns a dict with both legacy keys (prs, improvements, areas_to_improve,
    streaks, motivation) and new keys (volume_trend, strength_trend,
    quality_pattern, days_since_last, consecutive_weeks, feedback_tips).
    """
    from django.db.models import Max, Sum

    analysis = {
        "prs": [],
        "improvements": [],
        "areas_to_improve": [],
        "streaks": [],
        "motivation": "",
        "volume_trend": None,
        "strength_trend": None,
        "quality_pattern": None,
        "days_since_last": None,
        "consecutive_weeks": 0,
        "feedback_tips": [],
        "overload_targets": [],     # per-exercise progressive overload suggestions
        "next_session_plan": [],    # adaptive programming: concrete next-session instructions
    }

    current_sets = list(current_workout.sets.select_related("exercise").all())
    exercises_in_workout = set(s.exercise for s in current_sets if s.exercise is not None)
    total_sets = len(current_sets)
    good_great = sum(1 for s in current_sets if s.quality in ("good", "great"))

    # ── PRs (per linked exercise) ─────────────────────────────────────────────
    for exercise in exercises_in_workout:
        ex_sets = [s for s in current_sets if s.exercise == exercise]
        if not ex_sets:
            continue

        all_time = SetEntry.objects.filter(
            workout__user=user, exercise=exercise, workout__ended_at__isnull=False
        ).exclude(workout=current_workout)

        cur_max_w = max(s.weight_lb for s in ex_sets)
        hist_max_w = all_time.aggregate(Max("weight_lb"))["weight_lb__max"] or 0
        if cur_max_w > hist_max_w:
            analysis["prs"].append(f"New max weight PR for {exercise.name}: {cur_max_w} lb!")

        cur_max_r = max(s.reps for s in ex_sets)
        hist_max_r = all_time.aggregate(Max("reps"))["reps__max"] or 0
        if cur_max_r > hist_max_r:
            analysis["prs"].append(f"New max reps PR for {exercise.name}: {cur_max_r} reps!")

        cur_vol = sum(s.weight_lb * s.reps for s in ex_sets)
        prev_wids = list(all_time.values_list("workout_id", flat=True).distinct())
        prev_vols = [sum(s.weight_lb * s.reps for s in all_time.filter(workout_id=wid)) for wid in prev_wids]
        if prev_vols and cur_vol > max(prev_vols):
            analysis["prs"].append(f"New volume PR for {exercise.name}: {cur_vol} total volume!")

    # ── Progressive overload targets (per exercise) ───────────────────────────
    for exercise in exercises_in_workout:
        if exercise is None:
            continue
        ex_sets = [s for s in current_sets if s.exercise == exercise and s.reps > 0]
        if not ex_sets:
            continue

        avg_score = sum(QUALITY_DIFFICULTY.get(s.quality, 2) for s in ex_sets) / len(ex_sets)
        max_weight = max(s.weight_lb for s in ex_sets)
        avg_reps = round(sum(s.reps for s in ex_sets) / len(ex_sets))

        if max_weight == 0:
            # Bodyweight exercise
            if avg_score <= 2.0:
                target = {"exercise": exercise.name, "current_weight": 0, "suggested_weight": 0,
                          "current_reps": avg_reps, "suggested_reps": avg_reps + 2,
                          "reasoning": "Bodyweight — add 2 reps per set next session"}
            else:
                target = {"exercise": exercise.name, "current_weight": 0, "suggested_weight": 0,
                          "current_reps": avg_reps, "suggested_reps": avg_reps,
                          "reasoning": "Maintain reps and focus on controlled form"}
        else:
            if avg_score <= 1.5:
                bump = 5 if max_weight >= 45 else 2
                target = {"exercise": exercise.name, "current_weight": max_weight,
                          "suggested_weight": max_weight + bump,
                          "current_reps": avg_reps, "suggested_reps": avg_reps,
                          "reasoning": f"Excellent effort — increase load by {bump} lb"}
            elif avg_score <= 2.5:
                target = {"exercise": exercise.name, "current_weight": max_weight,
                          "suggested_weight": max_weight + 5,
                          "current_reps": avg_reps, "suggested_reps": avg_reps,
                          "reasoning": "Solid session — try +5 lb next time"}
            elif avg_score <= 3.0:
                target = {"exercise": exercise.name, "current_weight": max_weight,
                          "suggested_weight": max_weight,
                          "current_reps": avg_reps, "suggested_reps": avg_reps + 1,
                          "reasoning": "Maintain weight, aim for +1 rep per set"}
            else:
                target = {"exercise": exercise.name, "current_weight": max_weight,
                          "suggested_weight": max(0, max_weight - 5),
                          "current_reps": avg_reps, "suggested_reps": avg_reps,
                          "reasoning": "Challenging session — drop 5 lb and rebuild quality"}

        analysis["overload_targets"].append(target)

    # ── Same-muscle-group history (computed early for apples-to-apples comparisons) ──
    same_group = []
    if current_workout.workout_type == "weightlifting" and current_workout.day:
        same_group = list(
            Workout.objects.filter(
                user=user,
                workout_type="weightlifting",
                day=current_workout.day,
                ended_at__isnull=False,
            )
            .exclude(id=current_workout.id)
            .order_by("-ended_at")[:6]
        )

    # ── Recent workouts (any type) for streak/mood analysis ───────────────────
    previous_workouts = list(
        Workout.objects.filter(user=user, ended_at__isnull=False)
        .exclude(id=current_workout.id)
        .order_by("-ended_at")[:5]
    )

    # ── Session-level comparisons (same muscle group — apples-to-apples) ──────
    comparison_base = same_group[0] if same_group else None

    if comparison_base:
        last_total = comparison_base.sets.count()
        if total_sets > last_total:
            analysis["improvements"].append(f"Increased total sets from {last_total} to {total_sets}")

        last_good = comparison_base.sets.filter(quality__in=["good", "great"]).count()
        if good_great > last_good:
            analysis["improvements"].append(f"Improved quality sets from {last_good} to {good_great}")

        for exercise in exercises_in_workout:
            if exercise is None:
                continue
            cur_ex = [s for s in current_sets if s.exercise == exercise]
            last_ex = comparison_base.sets.filter(exercise=exercise)
            if last_ex.exists() and cur_ex:
                cur_avg = sum(s.weight_lb for s in cur_ex) / len(cur_ex)
                last_avg = last_ex.aggregate(avg=Sum("weight_lb"))["avg"] / last_ex.count()
                if cur_avg > last_avg:
                    analysis["improvements"].append(f"Increased average weight for {exercise.name}")

    # ── Areas to improve ─────────────────────────────────────────────────────
    low_q = sum(1 for s in current_sets if s.quality in ("bad", "ok"))
    if low_q:
        analysis["areas_to_improve"].append(
            f"{low_q} sets rated as 'bad' or 'ok' - focus on form and recovery"
        )

    for exercise in exercises_in_workout:
        if exercise is None:
            continue
        ex_ordered = sorted([s for s in current_sets if s.exercise == exercise], key=lambda x: x.set_number)
        if len(ex_ordered) >= 3 and ex_ordered[-1].reps < ex_ordered[0].reps * 0.6:
            analysis["areas_to_improve"].append(
                f"{exercise.name}: Significant rep drop across sets - consider reducing weight or longer rest"
            )

    # ── Quality streak ────────────────────────────────────────────────────────
    streak_count = 0
    for workout in [current_workout] + previous_workouts[:5]:
        s_count = workout.sets.count()
        gpct = workout.sets.filter(quality__in=["good", "great"]).count() / max(s_count, 1)
        if gpct >= 0.7:
            streak_count += 1
        else:
            break
    if streak_count >= 3:
        analysis["streaks"].append(f"{streak_count} workout streak with 70%+ quality sets!")

    # ── Motivation message ────────────────────────────────────────────────────
    mood = current_workout.mood
    quality_pct = good_great / max(total_sets, 1)

    if mood in ("Exhausted", "Low Energy") and quality_pct >= 0.6:
        analysis["motivation"] = (
            "Amazing work pushing through despite low energy! Your dedication is impressive. "
            "Make sure to prioritize rest and recovery - you've earned it!"
        )
    elif mood in ("Exhausted", "Low Energy"):
        analysis["motivation"] = (
            "Great job showing up even when energy was low! Remember, consistency matters more than perfection. "
            "Rest well and come back stronger!"
        )
    elif quality_pct >= 0.8 and total_sets >= 10:
        analysis["motivation"] = (
            "Outstanding performance! You absolutely crushed this workout! "
            "This is the kind of effort that builds champions. Keep this momentum going!"
        )
    elif quality_pct >= 0.7:
        analysis["motivation"] = (
            "Solid workout! You're making consistent progress. "
            "Keep focusing on quality over quantity and the results will follow!"
        )
    elif analysis["prs"]:
        analysis["motivation"] = (
            "New personal records! Your hard work is paying off. "
            "Celebrate these wins and keep pushing your limits!"
        )
    else:
        analysis["motivation"] = (
            "Every workout is progress! You showed up and put in the work. "
            "Keep building on this foundation and trust the process!"
        )

    recent_moods = [w.mood for w in previous_workouts[:3]]
    if recent_moods.count("Exhausted") >= 2 or recent_moods.count("Low Energy") >= 2:
        analysis["motivation"] += (
            " (Your recent workouts show low energy - consider taking an extra rest day or adjusting intensity.)"
        )

    # Volume trend vs last same-group session
    if same_group:
        cur_vol_total = sum(s.weight_lb * s.reps for s in current_sets)
        prev_vol_total = sum(s.weight_lb * s.reps for s in same_group[0].sets.all())

        if prev_vol_total > 0:
            pct = ((cur_vol_total - prev_vol_total) / prev_vol_total) * 100
            direction = "up" if pct > 2 else ("down" if pct < -2 else "same")
        else:
            pct, direction = 0.0, "same"

        analysis["volume_trend"] = {
            "current": cur_vol_total,
            "previous": prev_vol_total,
            "pct_change": round(abs(pct), 1),
            "direction": direction,
        }

        # Days since last same-group session
        analysis["days_since_last"] = (
            timezone.now().date() - same_group[0].ended_at.date()
        ).days

        # Consecutive calendar weeks this muscle group was trained
        weeks_seen = set()
        for sess in [current_workout] + same_group:
            d = sess.ended_at.date() if sess.ended_at else timezone.now().date()
            weeks_seen.add(d.isocalendar()[:2])  # (iso_year, iso_week)

        check_year, check_week = timezone.now().date().isocalendar()[:2]
        wk_count = 0
        while (check_year, check_week) in weeks_seen:
            wk_count += 1
            prev_monday = date.fromisocalendar(check_year, check_week, 1) - timedelta(days=7)
            check_year, check_week = prev_monday.isocalendar()[:2]
        analysis["consecutive_weeks"] = wk_count

    # Strength trend — top set weight over last 3 same-group sessions
    if len(same_group) >= 2:
        top_weights = []
        for sess in [current_workout] + same_group[:2]:
            sess_sets = list(sess.sets.all())
            top_weights.append(max((s.weight_lb for s in sess_sets), default=0))

        if top_weights[0] > top_weights[1]:
            s_dir, s_desc = "up", "Top set weight trending up"
        elif top_weights[0] < top_weights[1]:
            s_dir, s_desc = "down", "Top set weight has decreased"
        else:
            s_dir, s_desc = "same", "Top set weight holding steady"

        if len(top_weights) == 3 and top_weights[0] == top_weights[1] == top_weights[2]:
            s_dir = "plateau"
            s_desc = f"Same top weight ({top_weights[0]} lb) for 3+ sessions"

        analysis["strength_trend"] = {
            "direction": s_dir,
            "description": s_desc,
            "sessions": top_weights,
        }

    # Quality/difficulty pattern (proxy for session RPE)
    if current_sets:
        scores = [QUALITY_DIFFICULTY.get(s.quality, 2) for s in current_sets]
        avg_score = sum(scores) / len(scores)
        analysis["quality_pattern"] = {
            "avg_score": round(avg_score, 2),
            "high_effort": avg_score >= 3.0,
            "label": (
                "very hard" if avg_score >= 3.5 else
                "hard" if avg_score >= 3.0 else
                "moderate" if avg_score >= 2.0 else
                "easy"
            ),
        }

    # ── NEW: Contextual feedback tips ─────────────────────────────────────────
    # Combine all notes sources for holistic analysis
    all_notes_text = " ".join(filter(None, [
        current_workout.notes or "",
        current_workout.warmup_notes or "",
        current_workout.finisher_notes or "",
    ]))
    notes_words = set(all_notes_text.lower().split())
    notes_has_fatigue = bool(FATIGUE_KEYWORDS & notes_words)
    notes_has_injury = bool(INJURY_KEYWORDS & notes_words)
    notes_has_time_limit = bool(TIME_LIMIT_KEYWORDS & notes_words)

    # Warmup-specific word set for body-part cross-referencing
    warmup_words = set((current_workout.warmup_notes or "").lower().split())
    warmup_has_discomfort = bool((FATIGUE_KEYWORDS | INJURY_KEYWORDS) & warmup_words)

    vt = analysis["volume_trend"]
    st = analysis["strength_trend"]
    qp = analysis["quality_pattern"]
    tips = []

    # Volume + effort context
    if vt and qp:
        if vt["direction"] == "up" and not qp["high_effort"]:
            tips.append(
                "Volume up with quality effort — consider adding weight or an extra set next session."
            )
        elif vt["direction"] == "down" and (notes_has_fatigue or notes_has_injury or notes_has_time_limit):
            tips.append(
                "Volume dip noted — your notes suggest this wasn't a typical session. "
                "Not a true regression; prioritize recovery before your next session."
            )
        elif vt["direction"] == "down":
            tips.append(
                "Volume dropped vs last session — consider whether rest, nutrition, or stress is a factor."
            )

    # High-effort pattern across sessions
    if qp and qp["high_effort"]:
        recent_high_count = 0
        for sess in same_group[:2]:
            sess_qs = list(sess.sets.all())
            if sess_qs:
                avg = sum(QUALITY_DIFFICULTY.get(s.quality, 2) for s in sess_qs) / len(sess_qs)
                if avg >= 3.0:
                    recent_high_count += 1

        if recent_high_count >= 2:
            tips.append(
                "Consistently high effort across last 3 sessions — "
                "a deload or extra rest day may improve your next performance."
            )
        else:
            tips.append(
                "High effort session — prioritize sleep and protein before your next session."
            )

    # Plateau detection
    if st and st["direction"] == "plateau":
        tips.append(
            f"Plateau detected: {st['description']} — "
            "try a rep range change, technique variation, or a planned deload week."
        )

    # PR highlight
    if analysis["prs"]:
        tips.append("Personal record achieved — use this as your new progressive overload baseline.")

    # Back-to-back warning
    if analysis["days_since_last"] is not None and analysis["days_since_last"] <= 1:
        tips.append(
            "Back-to-back sessions for this muscle group — ensure adequate recovery "
            "before your next session of the same type."
        )

    # Injury flag
    if notes_has_injury:
        tips.append(
            "Injury or pain noted — avoid pushing through discomfort. "
            "Consider rest, ice, and consulting a professional before your next session."
        )

    # Time-limited session flag
    if notes_has_time_limit and not notes_has_injury:
        tips.append(
            "Looks like this was a time-limited session. "
            "Volume may be lower than usual — don't count this as a regression."
        )

    # Warmup context
    if current_workout.warmup_duration_minutes > 0:
        if warmup_has_discomfort:
            tips.append(
                f"Your warmup notes flag some pre-existing tightness or discomfort "
                f"({current_workout.warmup_duration_minutes} min logged). If this pattern continues, "
                "prioritize a dedicated mobility session before your next training day."
            )
        else:
            tips.append(
                f"{current_workout.warmup_duration_minutes}-min warmup logged — "
                "consistent preparation like this directly improves performance quality and reduces injury risk."
            )

    # Finisher context
    if current_workout.finisher_duration_minutes > 0:
        fin_lower = (current_workout.finisher_notes or "").lower()
        high_intensity_finisher = any(
            w in fin_lower for w in ["amrap", "burnout", "drop", "superset", "hiit", "circuit", "sprint"]
        )
        if high_intensity_finisher:
            tips.append(
                f"High-intensity finisher logged ({current_workout.finisher_duration_minutes} min). "
                "This adds meaningful metabolic stress on top of your main work — "
                "prioritize protein intake and sleep tonight for full recovery."
            )
        else:
            tips.append(
                f"{current_workout.finisher_duration_minutes}-min finisher completed — "
                "great habit for conditioning and caloric burn beyond your main lifts."
            )

    analysis["feedback_tips"] = tips

    # ── Adaptive programming: next-session plan ───────────────────────────────
    if adaptive and analysis["overload_targets"]:
        rest_days = 2
        if analysis["days_since_last"] is not None:
            rest_days = max(2, min(analysis["days_since_last"], 4))

        plan = []
        for t in analysis["overload_targets"]:
            if t["current_weight"] == 0:
                line = (
                    f"{t['exercise']}: target {t['suggested_reps']} reps/set "
                    f"({t['reasoning']})"
                )
            else:
                line = (
                    f"{t['exercise']}: {t['suggested_weight']} lb × {t['suggested_reps']} reps "
                    f"({t['reasoning']})"
                )
            plan.append(line)

        if analysis["strength_trend"] and analysis["strength_trend"]["direction"] == "plateau":
            plan.append(
                "Plateau detected — consider cycling rep ranges: drop to 5s with heavier "
                "weight, or push 15s at lighter load, for 2–3 sessions."
            )

        if analysis["days_since_last"] is not None:
            plan.append(
                f"Suggested rest before next {current_workout.day} session: "
                f"at least {rest_days} day{'s' if rest_days != 1 else ''}."
            )

        analysis["next_session_plan"] = plan

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

        s.weight_lb = int(weight_lb)
        s.reps = int(reps)
        s.quality = quality
        s.save()

        return redirect("workout_detail", workout_id=w.id)

    return render(request, "edit_set.html", {"set": s, "qualities": QUALITIES})


@login_required
@require_http_methods(["POST"])
def delete_set(request, set_id: int):
    s = get_object_or_404(SetEntry, id=set_id, workout__user=request.user)
    workout = s.workout
    s.delete()

    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        sets = workout.sets.select_related("exercise").order_by("position", "created_at")
        return render(request, "partials/sets_list.html", {"sets": sets, "workout": workout})

    return redirect("workout_detail", workout_id=workout.id)


@login_required
@require_http_methods(["POST"])
def move_set(request, set_id: int):
    """Move a set up or down in the order"""
    s = get_object_or_404(SetEntry, id=set_id, workout__user=request.user)
    workout = s.workout
    direction = request.POST.get("direction", "up")

    # Get all sets ordered by position, then created_at as fallback
    sets_list = list(workout.sets.order_by("position", "created_at"))

    # Ensure all sets have unique positions (fix for legacy data with position=0)
    for i, set_entry in enumerate(sets_list):
        if set_entry.position != i:
            set_entry.position = i
            set_entry.save(update_fields=["position"])

    # Re-fetch to get updated positions
    sets_list = list(workout.sets.order_by("position"))
    current_index = next((i for i, x in enumerate(sets_list) if x.id == s.id), None)

    if current_index is None:
        return HttpResponseBadRequest("Set not found")

    if direction == "up" and current_index > 0:
        other_set = sets_list[current_index - 1]
        s.position, other_set.position = other_set.position, s.position
        s.save(update_fields=["position"])
        other_set.save(update_fields=["position"])
    elif direction == "down" and current_index < len(sets_list) - 1:
        other_set = sets_list[current_index + 1]
        s.position, other_set.position = other_set.position, s.position
        s.save(update_fields=["position"])
        other_set.save(update_fields=["position"])

    if request.headers.get('HX-Request'):
        sets = workout.sets.select_related("exercise").order_by("position")
        return render(request, "partials/sets_list.html", {"sets": sets, "workout": workout})

    return redirect("workout_detail", workout_id=workout.id)


@login_required
@require_http_methods(["GET", "POST"])
def delete_workout(request, workout_id: int):
    w = get_object_or_404(Workout, id=workout_id, user=request.user)

    if request.method == "POST":
        w.delete()
        return redirect("dashboard")

    return render(
        request,
        "delete_workout.html",
        {"workout": w, "set_count": w.sets.count()},
    )


def about_how_it_works(request):
    """About page - How the app works"""
    return render(request, "about_how_it_works.html")


def about_training(request):
    """About page - Training suggestions"""
    return render(request, "about_training.html")


def about(request):
    """Redirect to how it works page for backwards compatibility"""
    return redirect("about_how_it_works")


def privacy(request):
    """Privacy policy and disclaimer page"""
    return render(request, "privacy.html")


@login_required
def account(request):
    """Account settings page"""
    return render(request, "account.html")


@login_required
@require_http_methods(["GET", "POST"])
def delete_account(request):
    """Allow users to delete their account and all associated data"""
    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm", "")

        errors = []

        if confirm != "DELETE":
            errors.append("Please type DELETE to confirm.")

        if not request.user.check_password(password):
            errors.append("Incorrect password.")

        if not errors:
            request.user.delete()
            return redirect("login")

        return render(request, "delete_account.html", {"errors": errors})

    return render(request, "delete_account.html")


# =============================================================================
# CALENDAR & SCHEDULING VIEWS
# =============================================================================


@login_required
def calendar_view(request):
    """Full calendar view with workout history and scheduling"""
    today = timezone.localdate()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    cal = calendar.Calendar(firstweekday=6)  # Sunday start
    weeks = cal.monthdatescalendar(year, month)

    start = weeks[0][0]
    end = weeks[-1][-1]

    # Get completed workouts in date range (only those that were ended)
    workouts = Workout.objects.filter(
        user=request.user,
        ended_at__isnull=False,
        started_at__date__gte=start,
        started_at__date__lte=end,
    ).select_related("template")

    # Build dict of date -> workouts
    workout_by_date = {}
    for w in workouts:
        date = w.started_at.date()
        if date not in workout_by_date:
            workout_by_date[date] = []
        workout_by_date[date].append(w)

    # Get scheduled workouts in date range
    scheduled = ScheduledWorkout.objects.filter(
        user=request.user,
        scheduled_date__gte=start,
        scheduled_date__lte=end,
    ).select_related("template")

    scheduled_by_date = {}
    for s in scheduled:
        if s.scheduled_date not in scheduled_by_date:
            scheduled_by_date[s.scheduled_date] = []
        scheduled_by_date[s.scheduled_date].append(s)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    return render(
        request,
        "calendar/calendar.html",
        {
            "weeks": weeks,
            "workout_by_date": workout_by_date,
            "scheduled_by_date": scheduled_by_date,
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "today": today,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def schedule_workout(request):
    """Schedule a future workout"""
    if request.method == "POST":
        scheduled_date = request.POST.get("scheduled_date", "").strip()
        workout_type = request.POST.get("workout_type", "").strip()
        day = request.POST.get("day", "").strip()
        cardio_type = request.POST.get("cardio_type", "").strip()
        template_id = request.POST.get("template_id", "").strip()
        notes = request.POST.get("notes", "").strip()

        if scheduled_date and workout_type in WORKOUT_TYPES:
            from datetime import datetime

            try:
                date_obj = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
            except ValueError:
                return HttpResponseBadRequest("Invalid date")

            template = None
            if template_id and template_id.isdigit():
                template = WorkoutTemplate.objects.filter(
                    id=int(template_id), user=request.user
                ).first()

            ScheduledWorkout.objects.create(
                user=request.user,
                scheduled_date=date_obj,
                workout_type=workout_type,
                day=day if workout_type == "weightlifting" else "",
                cardio_type=cardio_type if workout_type == "cardio" else "",
                template=template,
                notes=notes,
            )

            return redirect("calendar_view")

    # GET request - show form
    date_param = request.GET.get("date", "")
    templates = WorkoutTemplate.objects.filter(user=request.user)

    return render(
        request,
        "calendar/schedule_form.html",
        {
            "date": date_param,
            "days": DAYS,
            "cardio_types": Workout.CARDIO_TYPE_CHOICES,
            "templates": templates,
        },
    )


@login_required
@require_http_methods(["POST"])
def delete_scheduled(request, scheduled_id: int):
    """Delete a scheduled workout"""
    scheduled = get_object_or_404(ScheduledWorkout, id=scheduled_id, user=request.user)
    scheduled.delete()

    if request.headers.get("HX-Request"):
        return render(request, "partials/empty.html")

    return redirect("calendar_view")


@login_required
def start_from_scheduled(request, scheduled_id: int):
    """Start a workout from a scheduled entry"""
    scheduled = get_object_or_404(ScheduledWorkout, id=scheduled_id, user=request.user)

    # Create the workout based on scheduled type
    if scheduled.workout_type == "weightlifting":
        return redirect(
            f"/start/weightlifting/?day={scheduled.day}&template_id={scheduled.template_id or ''}"
        )
    elif scheduled.workout_type == "cardio":
        return redirect(
            f"/start/cardio/?cardio_type={scheduled.cardio_type}&template_id={scheduled.template_id or ''}"
        )
    elif scheduled.workout_type == "hiit":
        return redirect("/start/hiit/")

    return redirect("select_workout_type")


# =============================================================================
# TEMPLATE VIEWS
# =============================================================================


@login_required
def template_list(request):
    """List all user's workout templates"""
    templates = WorkoutTemplate.objects.filter(user=request.user)

    # Filter by type if specified
    workout_type = request.GET.get("type", "")
    if workout_type in WORKOUT_TYPES:
        templates = templates.filter(workout_type=workout_type)

    return render(
        request,
        "templates/list.html",
        {"templates": templates, "filter_type": workout_type},
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_template(request):
    """Create a new workout template"""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        workout_type = request.POST.get("workout_type", "").strip()
        day = request.POST.get("day", "").strip()
        description = request.POST.get("description", "").strip()
        cardio_type = request.POST.get("cardio_type", "").strip()
        target_duration = request.POST.get("target_duration", "0").strip()
        target_distance = request.POST.get("target_distance", "0").strip()
        hiit_intervals = request.POST.get("hiit_intervals", "8").strip()
        hiit_work = request.POST.get("hiit_work", "30").strip()
        hiit_rest = request.POST.get("hiit_rest", "15").strip()

        if name and workout_type in WORKOUT_TYPES:
            try:
                target_duration_int = int(target_duration) if target_duration else 0
                target_distance_dec = Decimal(target_distance) if target_distance else Decimal("0")
                hiit_intervals_int = int(hiit_intervals) if hiit_intervals else 8
                hiit_work_int = int(hiit_work) if hiit_work else 30
                hiit_rest_int = int(hiit_rest) if hiit_rest else 15
            except (ValueError, InvalidOperation):
                target_duration_int = 0
                target_distance_dec = Decimal("0")
                hiit_intervals_int = 8
                hiit_work_int = 30
                hiit_rest_int = 15

            template = WorkoutTemplate.objects.create(
                user=request.user,
                name=name,
                workout_type=workout_type,
                day=day if workout_type == "weightlifting" else "",
                description=description,
                cardio_type=cardio_type if workout_type == "cardio" else "",
                target_duration_minutes=target_duration_int,
                target_distance_miles=target_distance_dec,
                hiit_intervals=hiit_intervals_int,
                hiit_work_seconds=hiit_work_int,
                hiit_rest_seconds=hiit_rest_int,
            )

            return redirect("template_detail", template_id=template.id)

    return render(
        request,
        "templates/create.html",
        {
            "days": DAYS,
            "cardio_types": Workout.CARDIO_TYPE_CHOICES,
        },
    )


@login_required
def template_detail(request, template_id: int):
    """View a workout template"""
    template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user)
    exercises = template.exercises.all()

    return render(
        request,
        "templates/detail.html",
        {"template": template, "exercises": exercises},
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_template(request, template_id: int):
    """Edit a workout template"""
    template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user)

    if request.method == "POST":
        template.name = request.POST.get("name", "").strip() or template.name
        template.description = request.POST.get("description", "").strip()
        template.save()
        return redirect("template_detail", template_id=template.id)

    return render(
        request,
        "templates/edit.html",
        {"template": template},
    )


@login_required
@require_http_methods(["POST"])
def delete_template(request, template_id: int):
    """Delete a workout template"""
    template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user)
    template.delete()
    return redirect("template_list")


@login_required
def use_template(request, template_id: int):
    """Start a workout using a template"""
    template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user)

    if template.workout_type == "weightlifting":
        return redirect(f"/start/weightlifting/?template_id={template.id}")
    elif template.workout_type == "cardio":
        return redirect(f"/start/cardio/?template_id={template.id}")
    elif template.workout_type == "hiit":
        return redirect(f"/start/hiit/?template_id={template.id}")

    return redirect("select_workout_type")


@login_required
@require_http_methods(["GET", "POST"])
def save_as_template(request, workout_id: int):
    """Save a completed workout as a template"""
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if name:
            template = WorkoutTemplate.objects.create(
                user=request.user,
                name=name,
                workout_type=workout.workout_type,
                day=workout.day,
                description=description,
                cardio_type=workout.cardio_type,
                target_duration_minutes=workout.target_duration_minutes,
                target_distance_miles=workout.target_distance_miles,
            )

            # Copy exercises from workout sets (for weightlifting)
            if workout.workout_type == "weightlifting":
                seen_exercises = set()
                position = 0
                for set_entry in workout.sets.order_by("position"):
                    exercise_key = (
                        set_entry.exercise_id,
                        set_entry.custom_exercise_name,
                    )
                    if exercise_key not in seen_exercises:
                        seen_exercises.add(exercise_key)
                        TemplateExercise.objects.create(
                            template=template,
                            exercise=set_entry.exercise,
                            custom_exercise_name=set_entry.custom_exercise_name,
                            custom_equipment=set_entry.custom_equipment,
                            target_sets=1,
                            target_reps=set_entry.reps,
                            target_weight=set_entry.weight_lb,
                            position=position,
                        )
                        position += 1

            return redirect("template_detail", template_id=template.id)

    return render(
        request,
        "templates/save_as_template.html",
        {"workout": workout},
    )


# =============================================================================
# HISTORY VIEW
# =============================================================================


@login_required
def workout_history(request):
    """Workout history with list and stats views"""
    workout_type_filter = request.GET.get("type", "")
    view_mode = request.GET.get("view", "list")

    workouts = Workout.objects.filter(
        user=request.user, ended_at__isnull=False
    ).order_by("-ended_at")

    if workout_type_filter in WORKOUT_TYPES:
        workouts = workouts.filter(workout_type=workout_type_filter)

    # Stats for the stats view
    stats = None
    if view_mode == "stats":
        from django.db.models import Count
        from django.db.models.functions import TruncWeek

        # Workouts per week (last 8 weeks)
        eight_weeks_ago = timezone.now() - timedelta(weeks=8)
        weekly_workouts = (
            Workout.objects.filter(
                user=request.user,
                ended_at__isnull=False,
                ended_at__gte=eight_weeks_ago,
            )
            .annotate(week=TruncWeek("ended_at"))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )

        # Workout type distribution
        type_distribution = (
            Workout.objects.filter(user=request.user, ended_at__isnull=False)
            .values("workout_type")
            .annotate(count=Count("id"))
        )

        # Total stats
        total_workouts = Workout.objects.filter(
            user=request.user, ended_at__isnull=False
        ).count()
        total_sets = SetEntry.objects.filter(workout__user=request.user).count()

        stats = {
            "weekly_workouts": list(weekly_workouts),
            "type_distribution": list(type_distribution),
            "total_workouts": total_workouts,
            "total_sets": total_sets,
            "streak": calculate_workout_streak(request.user),
        }

    return render(
        request,
        "history/workout_history.html",
        {
            "workouts": workouts[:50],
            "filter_type": workout_type_filter,
            "view_mode": view_mode,
            "stats": stats,
        },
    )


# =============================================================================
# NEW ABOUT PAGES
# =============================================================================


def about_cardio(request):
    """Cardio training guide"""
    return render(request, "about/about_cardio.html")


def about_hiit(request):
    """HIIT training guide"""
    return render(request, "about/about_hiit.html")
