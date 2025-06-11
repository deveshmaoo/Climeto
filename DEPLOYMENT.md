# 🚀 HRMS Deployment Guide

## Why AWS Amplify Doesn't Work
AWS Amplify is for **static websites** (HTML, CSS, JS). Your Flask app is a **dynamic web application** that needs a Python server.

## ✅ Deployment Options

### 1. 🟢 **Heroku** (Easiest - Recommended)

#### Prerequisites:
- Create Heroku account: https://heroku.com
- Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli

#### Steps:
```bash
# 1. Login to Heroku
heroku login

# 2. Create app
heroku create your-hrms-app-name

# 3. Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key-here
heroku config:set DATABASE_URL=sqlite:///hrms.db

# 4. Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# 5. Initialize database
heroku run python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

#### Add PostgreSQL (Optional):
```bash
heroku addons:create heroku-postgresql:essential-0
```

---

### 2. 🟡 **AWS Elastic Beanstalk**

#### Prerequisites:
- AWS Account
- AWS CLI installed
- EB CLI installed: `pip install awsebcli`

#### Steps:
```bash
# 1. Initialize EB application
eb init -p python-3.9 hrms-application

# 2. Create environment
eb create hrms-production

# 3. Deploy
eb deploy

# 4. Set environment variables
eb setenv FLASK_ENV=production SECRET_KEY=your-secret-key-here

# 5. Open app
eb open
```

---

### 3. 🟠 **Railway** (Modern Alternative)

#### Steps:
1. Go to https://railway.app
2. Connect your GitHub repository
3. Railway auto-detects Flask app
4. Set environment variables in dashboard
5. Deploy automatically

---

### 4. 🔵 **DigitalOcean App Platform**

#### Steps:
1. Go to https://cloud.digitalocean.com/apps
2. Create app from GitHub
3. Select your repository
4. Choose Python environment
5. Set run command: `gunicorn run:app`
6. Deploy

---

### 5. 🟣 **Render** (Free Tier Available)

#### Steps:
1. Go to https://render.com
2. Connect GitHub repository
3. Create Web Service
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `gunicorn run:app`
6. Deploy

---

## 🔧 Environment Variables (Required for all platforms)

```bash
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=sqlite:///hrms.db  # or your database URL
```

## 📝 Important Notes

1. **Database**: Your app uses SQLite by default. For production, consider PostgreSQL or MySQL.

2. **File Uploads**: Configure cloud storage (AWS S3, Cloudinary) for file uploads in production.

3. **Security**: 
   - Set strong SECRET_KEY
   - Use HTTPS in production
   - Configure CORS if needed

4. **Performance**:
   - Use Gunicorn with multiple workers
   - Consider Redis for caching
   - Use CDN for static files

## 🚨 Quick Fix for Database Issues

If you get database errors after deployment:

```python
# Run this once after deployment
from app import create_app, db
from app.models.employee import Employee
from app.models.auth import User

app = create_app()
with app.app_context():
    db.create_all()
    
    # Create admin user if doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', email='admin@company.com')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        admin_employee = Employee(
            first_name='Admin',
            last_name='User',
            email='admin@company.com',
            department='Management',
            role='Admin',
            employment_status='Active'
        )
        db.session.add(admin_employee)
        db.session.commit()
        
        admin_user.employee_id = admin_employee.id
        db.session.commit()
```

## 🎯 Recommended Deployment Path

1. **Start with Heroku** (easiest, free tier)
2. **Move to Railway/Render** (modern, good free tiers)  
3. **Scale to AWS/DigitalOcean** (when you need more control)

## 💡 Pro Tips

- Always test deployment on staging environment first
- Keep your `requirements.txt` updated
- Use environment variables for all secrets
- Monitor your application logs after deployment
- Set up automated backups for your database 