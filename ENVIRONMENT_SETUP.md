# Environment Setup Guide

This guide helps you set up the environment variables for Discussion-Den.

## Quick Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Generate a secure secret key:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Update `.env` with your values:**
   - Replace `SECRET_KEY` with the generated key
   - Update `DATABASE_URL` with your PostgreSQL credentials
   - Optionally configure Google OAuth

## Required Environment Variables

### Flask Configuration
- `FLASK_ENV`: Set to `development` for local development, `production` for deployment
- `FLASK_DEBUG`: Set to `True` for development, `False` for production
- `SECRET_KEY`: **CRITICAL** - Use a secure random key, never use default values

### Database Configuration
- `DATABASE_URL`: PostgreSQL connection string
  - Format: `postgresql+psycopg2://username:password@host:port/database_name`
  - Example: `postgresql+psycopg2://postgres:mypassword@localhost:5432/discussion_den`

## Optional Environment Variables

### Google OAuth (for "Sign in with Google")
- `GOOGLE_CLIENT_ID`: From Google Cloud Console
- `GOOGLE_CLIENT_SECRET`: From Google Cloud Console  
- `GOOGLE_REDIRECT_URI`: Callback URL (usually `http://localhost:5000/auth/google/callback`)

### Security Settings
- `WTF_CSRF_ENABLED`: Enable CSRF protection (default: `True`)
- `SESSION_COOKIE_SECURE`: Set to `True` in production with HTTPS
- `SESSION_COOKIE_HTTPONLY`: Prevent XSS attacks (default: `True`)

### Application Settings
- `MAX_CONTENT_LENGTH`: Maximum file upload size in bytes
- `POSTS_PER_PAGE`: Number of posts per page for pagination
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

## Database Setup

1. **Install PostgreSQL** (required - SQLite is not supported)

2. **Create database:**
   ```sql
   CREATE DATABASE discussion_den;
   CREATE USER your_username WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE discussion_den TO your_username;
   ```

3. **Initialize database:**
   ```bash
   flask init-db
   ```

4. **Seed with sample data (optional):**
   ```bash
   flask seed
   ```

## Google OAuth Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Identity API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URIs:
   - Development: `http://localhost:5000/auth/google/callback`
   - Production: `https://yourdomain.com/auth/google/callback`
6. Copy Client ID and Client Secret to your `.env` file

## Security Best Practices

### Development
- Never commit `.env` to version control
- Use different secret keys for different environments
- Keep database credentials secure

### Production
- Set `FLASK_ENV=production`
- Set `FLASK_DEBUG=False`
- Use environment variables instead of `.env` file
- Enable HTTPS and set `SESSION_COOKIE_SECURE=True`
- Use strong, unique passwords for database
- Regularly rotate secret keys
- Set up proper logging and monitoring

## Troubleshooting

### Common Issues

1. **Database connection errors:**
   - Check PostgreSQL is running
   - Verify credentials in `DATABASE_URL`
   - Ensure database exists

2. **Secret key errors:**
   - Generate a new secret key
   - Ensure no spaces or special characters in key

3. **Google OAuth errors:**
   - Check redirect URI matches exactly
   - Verify client ID and secret are correct
   - Ensure Google Identity API is enabled

### Environment Validation

Run this command to check your environment setup:
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['SECRET_KEY', 'DATABASE_URL']
optional = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET']

print('Required variables:')
for var in required:
    value = os.getenv(var)
    status = '✓' if value and value != 'your_secret_key_here' else '✗'
    print(f'  {status} {var}: {\"Set\" if value else \"Missing\"}')

print('\nOptional variables:')
for var in optional:
    value = os.getenv(var)
    status = '✓' if value else '-'
    print(f'  {status} {var}: {\"Set\" if value else \"Not set\"}')
"
```

## Example .env File

See `.env.example` for a complete template with all available configuration options.