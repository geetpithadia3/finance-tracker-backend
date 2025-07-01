# Security Guide

## Environment Configuration

1. **Generate a secure secret key**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set environment variables**:
   ```bash
   export SECRET_KEY="your-generated-secret-key"
   export DEBUG=False
   export POSTGRES_PASSWORD="your-secure-password"
   ```

3. **Never commit `.env` files** - Add them to `.gitignore`

## Password Requirements

- Minimum 8 characters
- Must contain uppercase and lowercase letters
- Must contain at least one number
- Must contain at least one special character

## API Security

- All sensitive endpoints require JWT authentication
- Input validation on all user inputs
- SQL injection prevention through parameterized queries
- CORS restricted to allowed origins only

## Production Checklist

- [ ] Change default secret key
- [ ] Set DEBUG=False
- [ ] Use environment variables for secrets
- [ ] Configure secure database credentials
- [ ] Set up HTTPS in production
- [ ] Review CORS origins
- [ ] Monitor logs for suspicious activity

## Reporting Security Issues

If you discover a security vulnerability, please email security@yourcompany.com