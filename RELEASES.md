# Workout Tracker - Release History

## v2.0.0 - Major Feature Update (January 2026)

### New Workout Types
- **Cardio Workouts**: Full cardio tracking with duration, distance, speed, and incline metrics
  - Support for running, cycling, swimming, rowing, elliptical, stair climber, jump rope, and walking
  - Running timer with interval logging
  - Automatic totals calculation (duration, distance, average speed)

- **HIIT Workouts**: High-Intensity Interval Training with built-in timer
  - Configurable work/rest intervals
  - Preset protocols (Tabata, 30/30, EMOM)
  - Audio cues for phase transitions
  - Visual progress tracking with color-coded phases

### Menu-Based Dashboard
- Redesigned dashboard with three main sections:
  - **Start Workout** - Quick access to all workout types
  - **Previous Workouts** - View workout history with list and stats views
  - **Calendar** - Visual calendar with workout tracking and scheduling

### Calendar & Scheduling
- Full calendar view showing completed workouts by date
- Schedule future workouts with workout type selection
- Start workouts directly from scheduled items
- Color-coded markers for different workout types

### Workout Templates
- Save and reuse workout structures
- Create templates for any workout type (weightlifting, cardio, HIIT)
- Save completed workouts as templates
- Quick-start workouts from templates
- Template management (view, edit, delete)

### History & Stats
- Unified workout history view
- Toggle between List view and Stats view
- Filter by workout type
- Weekly workout trends
- Workout type distribution charts
- Total workouts and sets statistics

### New About Pages
- **Cardio Training Guide**: Comprehensive cardio training information
- **HIIT Training Guide**: HIIT protocols, exercises, and tips
- Updated "How the App Works" page with all new features
- Updated "Training Suggestions" with cardio and HIIT guidelines

### Database Updates
- New models: ScheduledWorkout, WorkoutTemplate, TemplateExercise, HIITSession
- Extended Workout model with workout_type and cardio fields
- Extended SetEntry model with cardio metrics (distance, speed, incline)

---

## v1.5.0 - Custom Exercises & Duration Tracking (January 2026)

### Custom Exercise Entry
- Enter custom exercise names for any workout
- Add custom equipment descriptions
- Works alongside the predefined exercise library

### Duration Tracking
- Track timed exercises (planks, holds, etc.)
- Duration displayed in workout summaries

### Set Reordering
- Move sets up/down in the workout
- Drag-and-drop style reordering via buttons
- Maintains proper position tracking

---

## v1.4.0 - UI/UX Improvements & HIIT Timer (January 2026)

### HIIT Interval Timer (Dashboard)
- Configurable intervals, work time, and rest time
- Start/pause/reset controls
- Audio alerts at phase transitions
- Visual countdown display

### Rest Timer Enhancements
- Stopwatch mode (count up)
- Countdown mode (1-4 minutes)
- Persistent timer state across set additions
- Audio beep on countdown completion

### UI Improvements
- Modernized card designs with gradients
- Improved button styling and hover effects
- Better mobile responsiveness
- Enhanced color scheme

---

## v1.3.0 - Security & Privacy (January 2026)

### Account Security
- Password validation with Django's built-in validators
- Rate limiting on registration (5 attempts per minute)
- Secure password reset flow
- Email validation on registration

### Privacy Features
- User data isolation (users only see their own data)
- Account deletion with full data removal
- Privacy policy page
- Rate limit error page

### Account Management
- Account settings page
- Delete account functionality with confirmation
- Password confirmation for account deletion

---

## v1.2.0 - Branding & About Pages (January 2026)

### Branding
- Custom logo added to header
- Favicon for browser tabs
- "Gtech LLC" branding in footer

### About Pages
- "How the App Works" - Feature overview and getting started guide
- "Training Suggestions" - Workout split recommendations and tips
- Rest period guidelines
- Progressive overload tips

### Welcome Experience
- Updated welcome message
- Improved dashboard layout

---

## v1.1.0 - Web UI Launch (January 2026)

### User Authentication
- User registration with username/email/password
- Login/logout functionality
- Password reset via email
- Session management

### Workout Tracking
- Start workout with name, day type, and mood
- Log sets with exercise, weight, reps, and quality rating
- End workout and view summary
- Delete workouts

### Exercise Library
- Predefined exercises organized by muscle group
- Day-based filtering (Back & Biceps, Chest & Triceps, Legs, Core, Shoulders & Traps)
- "Custom Workout" option for mixed exercises

### Workout Analysis
- Personal Records (PRs) detection for weight, reps, and volume
- Comparison with previous workouts
- Quality-based insights
- Context-aware motivational messages
- Performance streaks

### Rest Timer
- Built-in timer for rest periods
- Stopwatch and countdown modes

### Calendar View
- Monthly calendar showing workout days
- Visual workout history

---

## v1.0.0 - Initial Release (January 2026)

### Core Features
- CLI-based workout tracker
- SQLite database storage
- Basic workout logging
- Exercise tracking

### Railway Deployment
- Django web application
- PostgreSQL database (production)
- Gunicorn WSGI server
- Static file serving with WhiteNoise
- HTTPS enforcement

---

## Technical Stack

- **Backend**: Django 5.2.9
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Tailwind CSS (CDN), HTMX 1.9.10
- **Hosting**: Railway
- **Server**: Gunicorn

---

## Contributors

Built by **Gtech LLC**
