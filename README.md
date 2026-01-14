# Workout Tracker

A comprehensive workout tracking application with CLI and web interfaces, featuring workout analytics, personal records tracking, and motivational insights.

## Features

- **User Authentication**: Secure registration and login system
- **Workout Logging**: Track exercises, sets, reps, and quality
- **Rest Timer**: Built-in timer with audio alerts
- **Workout Analysis**:
  - Personal records (PRs) tracking
  - Progress comparisons
  - Performance streaks
  - Areas for improvement
  - Context-aware motivational messages
- **Calendar View**: Visual workout history
- **Mobile Responsive**: Works on all devices

## Tech Stack

- **Backend**: Django 5.2.9, Python 3.10
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Tailwind CSS (via CDN)
- **Deployment**: Railway.app
- **Web Server**: Gunicorn

## Local Development

### Prerequisites
- Python 3.10+
- pip

### Setup

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   cd web
   python manage.py migrate
   python manage.py load_exercises
   python manage.py runserver
   ```

5. Visit http://localhost:8000

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed Railway deployment instructions.

### Quick Deploy Checklist
1. Push code to GitHub
2. Connect to Railway
3. Add PostgreSQL
4. Set environment variables
5. Deploy!

## Security Features

- Environment-based configuration
- HTTPS enforcement
- Secure cookies
- CSRF protection
- Password hashing
- SQL injection protection

## License

Open source - personal use

