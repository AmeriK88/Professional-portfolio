# Django Axes Access Log Maintenance

## Overview

This document describes the maintenance process for Django Axes access logs in the JFGC Dev 2.0 portfolio application.

### What is Maintained

- **Cleaned**: `AccessLog` records older than 90 days
- **Preserved**: Recent access logs (within the past 90 days)
- **Unaffected**: 
  - Active login attempts and lockout counters (`AccessAttempt` records)
  - User authentication state
  - Security lockout configuration

The maintenance operation removes historical access logs only, preserving the application's active security state.

## Retention Policy

- **Retention period**: 90 days
- **Date field used**: `AccessLog.attempt_time` (DateTimeField, UTC timezone)
- **Timezone handling**: UTC-aware datetime comparison using Django's `timezone.now()`

## Current Environment

- **Django Axes version**: 8.0.0
- **Database**: MySQL (via PyMySQL)
- **Management command**: `python manage.py axes_reset_logs --age 90`

## Counting Eligible Records

Before running maintenance, count records older than 90 days:

```bash
python manage.py shell -c "
from axes.models import AccessLog
from datetime import timedelta
from django.utils import timezone

now = timezone.now()
cutoff = now - timedelta(days=90)

total = AccessLog.objects.count()
old_records = AccessLog.objects.filter(attempt_time__lt=cutoff).count()
recent_records = AccessLog.objects.filter(attempt_time__gte=cutoff).count()

print(f'Total records: {total}')
print(f'Records older than 90 days: {old_records}')
print(f'Records within 90 days: {recent_records}')
print(f'90-day cutoff time: {cutoff}')
"
```

## Running Maintenance Manually

### Local Development

```bash
# Activate the virtual environment
.\venv\Scripts\Activate.ps1

# Run the cleanup (deletes records older than 90 days)
python manage.py axes_reset_logs --age 90 -v 2
```

### Production (Railway)

```bash
python manage.py axes_reset_logs --age 90 -v 2
```

### Expected Output

**First run (with eligible records):**
```
INFO: AXES: Reset 32 access logs older than 90 days from database.
32 logs removed.
```

**Subsequent runs (no eligible records):**
```
INFO: AXES: Reset 0 access logs older than 90 days from database.
No logs found.
```

## Safety Properties

✓ **Idempotent**: Running the command repeatedly on the same dataset is safe (no errors or data loss)
✓ **Reversible boundary handling**: Records exactly at the 90-day cutoff (created at the boundary time) are preserved
✓ **No active security impact**: Does not reset lockout counters, clear active attempts, or modify authentication state
✓ **Timezone-safe**: Uses Django's UTC-aware `timezone.now()` for all calculations

## Railway Cron Setup

### Recommended Schedule

```
0 3 * * 0
```

This corresponds to **Sunday at 03:00 UTC** (weekly execution).

### Manual Configuration Steps

Since the maintenance should run in a separate Railway Cron service:

1. **Do not modify the main web service** (`Procfile` or startup commands)

2. **Create a new Railway Cron service** with:
   - **Image**: Same as your main service (or Alpine Python + Django dependencies)
   - **Command**: 
     ```bash
     python manage.py axes_reset_logs --age 90
     ```
   - **Schedule**: `0 3 * * 0` (Sunday 03:00 UTC)
   - **Environment Variables**: Inherit or explicitly copy from the main service:
     - `DATABASE_URL` (required)
     - `DJANGO_SETTINGS_MODULE` (if used)
     - `SECRET_KEY`
     - Any other settings needed by Django startup

3. **Deploy and verify** in Railway dashboard:
   - Check that the Cron service starts successfully
   - Verify the service connects to the production database
   - Monitor logs for execution output

### Verifying Successful Execution

After deployment, check Railway Cron service logs:

1. Navigate to your Railway project dashboard
2. Select the Cron service
3. Open the **Logs** tab
4. Look for output like:
   ```
   INFO: AXES: Reset N access logs older than 90 days from database.
   N logs removed.
   ```

If the command completes without error, the maintenance was successful.

## Limitations and Considerations

### Database Performance

- Deletion of 32 records (as tested) completes in ~1 second
- For high-volume deployments (e.g., 100,000+ AccessLog records), consider:
  - Running during off-peak hours (current schedule: 03:00 UTC is good)
  - Monitoring database lock times
  - Potentially adjusting the 90-day retention if disk space requires more aggressive cleanup

### Version-Specific Notes

- **Django Axes 8.0.0**: The `--age` parameter is stable and fully supported
- **Older versions** (< 7.0): Verify `axes_reset_logs` command availability before use
- **Newer versions** (> 8.0.0): Expected to maintain backward compatibility

### AccessLog Model Stability

The `AccessLog` model includes:
- `attempt_time` (DateTimeField) – timestamp of the access attempt
- `ip_address`, `username`, `user_agent` – attempt details
- `path_info`, `http_accept`, `session_hash` – request metadata

The cleanup uses only `attempt_time` for filtering and does not require model changes.

## Troubleshooting

### Command not found

```
CommandError: No available app 'axes' or it doesn't support the "reset_logs" action.
```

**Cause**: Django Axes is not installed or not in `INSTALLED_APPS`.

**Fix**: Verify:
- `django-axes==8.0.0` in `requirements.txt`
- `"axes"` in `INSTALLED_APPS` in `portfolio/settings.py`

### Database connection errors

```
OperationalError: (2003, "Can't connect to MySQL server...")
```

**Cause**: Cron service cannot connect to the database.

**Fix**: Verify:
- `DATABASE_URL` environment variable is set in the Cron service
- Database credentials are correct
- Railway networking allows the Cron service to access the database

### No records deleted

```
INFO: AXES: Reset 0 access logs older than 90 days from database.
No logs found.
```

**Reason**: All current logs are within the 90-day retention window.

**Status**: This is normal and safe; no action required.

## Monitoring and Alerts

Consider setting up Railway notifications for:
- Cron job execution failures
- Unusually high numbers of deleted records (> typical baseline)

For ongoing monitoring, periodically check:
```bash
python manage.py shell -c "
from axes.models import AccessLog
print(f'Current AccessLog count: {AccessLog.objects.count()}')
"
```

## Related Documentation

- [Django Axes Official Docs](https://django-axes.readthedocs.io/)
- Railway Cron Jobs: Check your Railway project settings for cron configuration
- Django Timezone Support: https://docs.djangoproject.com/en/5.1/topics/i18n/timezones/
