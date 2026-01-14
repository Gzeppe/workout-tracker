# Deployment Guide - Workout Tracker

This guide will walk you through deploying your workout tracker app to Railway.app for free.

## Prerequisites

- A GitHub account
- A Railway.app account (sign up at https://railway.app)
- Your code pushed to a GitHub repository

## Step 1: Prepare Your Repository

Make sure all the deployment files are committed:
- `requirements.txt` - Python dependencies
- `Procfile` - Deployment commands
- `runtime.txt` - Python version
- `railway.json` - Railway configuration

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

## Step 2: Create a Railway Project

1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub account
5. Select your workout-tracker repository

## Step 3: Add PostgreSQL Database

1. In your Railway project, click "+ New"
2. Select "Database"
3. Choose "PostgreSQL"
4. Railway will automatically create a PostgreSQL database
5. The `DATABASE_URL` environment variable will be automatically set

## Step 4: Configure Environment Variables

In your Railway project settings, add these environment variables:

### Required Variables:

1. **SECRET_KEY** (CRITICAL - Generate a secure one)
   ```bash
   # Generate a secure secret key (run this locally):
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Copy the output and add it as `SECRET_KEY` in Railway

2. **DEBUG**
   - Value: `False`
   - ⚠️ NEVER set this to `True` in production

3. **ALLOWED_HOSTS**
   - Value: `.railway.app,your-custom-domain.com` (if you have one)
   - Railway will give you a URL like `your-app.up.railway.app`
   - You can update this after deployment

4. **CSRF_TRUSTED_ORIGINS**
   - Value: `https://your-app.up.railway.app`
   - ⚠️ Update this with your actual Railway URL after deployment

### Optional Variables:

5. **DJANGO_SETTINGS_MODULE**
   - Value: `config.settings`
   - Usually not needed as it's the default

## Step 5: Deploy

1. Railway will automatically deploy your app after you connect the repository
2. Watch the deployment logs for any errors
3. The deployment process will:
   - Install Python dependencies
   - Run database migrations
   - Load initial exercise data
   - Start the Gunicorn web server

## Step 6: Access Your App

1. Once deployed, Railway will give you a URL (e.g., `your-app.up.railway.app`)
2. Visit that URL in your browser
3. You should see the login page!

## Step 7: Create Your First User

Since you don't have a superuser yet, you can:

**Option A: Use the registration page**
- Go to `/register/` on your deployed app
- Create an account through the web interface

**Option B: Create a superuser via Railway shell**
1. In Railway, go to your project
2. Click on your web service
3. Go to "Settings" → "Variables"
4. Click "Shell" or use Railway CLI:
   ```bash
   railway run python web/manage.py createsuperuser
   ```

## Post-Deployment Checklist

- [ ] App loads without errors
- [ ] Can register a new user
- [ ] Can log in
- [ ] Can start a workout
- [ ] Exercises are loaded (check workout creation page)
- [ ] Can add sets to a workout
- [ ] Can end a workout and see summary
- [ ] Calendar displays correctly

## Updating Environment Variables After First Deploy

After your first deployment, you'll have the actual Railway URL. Update these:

1. **ALLOWED_HOSTS**
   - Add your Railway domain: `your-actual-app.up.railway.app`

2. **CSRF_TRUSTED_ORIGINS**
   - Update to: `https://your-actual-app.up.railway.app`

Railway will automatically redeploy when you change environment variables.

## Troubleshooting

### "DisallowedHost" Error
- Check your `ALLOWED_HOSTS` environment variable
- Make sure it includes your Railway domain

### "CSRF verification failed"
- Check your `CSRF_TRUSTED_ORIGINS` environment variable
- Make sure it starts with `https://` and includes your Railway domain

### Database Connection Errors
- Make sure PostgreSQL is running in your Railway project
- Check that `DATABASE_URL` is set (should be automatic)

### Static Files Not Loading
- The app uses Tailwind CDN, so static files should work automatically
- If issues persist, run: `railway run python web/manage.py collectstatic --noinput`

### App Crashes on Startup
- Check Railway logs for errors
- Common issues:
  - Missing environment variables
  - Database migration failures
  - Import errors

## Viewing Logs

In Railway:
1. Go to your project
2. Click on your web service
3. Click "Deployments"
4. Click on the latest deployment
5. View the logs to debug any issues

## Cost Information

- **Railway Free Tier**: $5 monthly credit
- **Typical usage**: Small apps like this usually stay within free tier
- **What uses credits**:
  - Web service runtime
  - PostgreSQL database
  - Outbound data transfer

Monitor your usage in Railway dashboard to ensure you stay within limits.

## Security Notes

✅ **What's Been Secured:**
- Secret key is in environment variables
- DEBUG is False in production
- HTTPS enforced
- Security headers enabled (HSTS, XSS protection, etc.)
- CSRF protection enabled
- Database credentials secured via Railway

⚠️ **Additional Security Considerations:**
- Change the default SECRET_KEY immediately
- Use strong passwords for user accounts
- Consider adding rate limiting for login attempts (future enhancement)
- Regularly update dependencies for security patches

## Backup Your Data

Railway doesn't automatically backup your database. To backup:

```bash
# Download database backup
railway run pg_dump $DATABASE_URL > backup.sql

# Restore from backup
railway run psql $DATABASE_URL < backup.sql
```

Set up regular backups for production use!

## Custom Domain (Optional)

To use your own domain:
1. In Railway project settings, add your domain
2. Update DNS records as instructed by Railway
3. Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to include your domain

## Need Help?

- Railway Documentation: https://docs.railway.app
- Django Documentation: https://docs.djangoproject.com
- Check Railway deployment logs for error messages
