# 🚀 Deploy HRMS to Render

## Quick Fix for Current Error

The build is failing due to package version conflicts. Here's how to fix it:

### Step 1: Choose Requirements File

**Option A: Minimal (Recommended for Render)**
```bash
# Rename the minimal requirements file
mv requirements-minimal.txt requirements.txt
```

**Option B: Keep Full Requirements (Updated)**
The main `requirements.txt` has been updated with flexible version ranges.

### Step 2: Deploy to Render

1. **Go to [Render.com](https://render.com)**
2. **Connect the Correct Repository**
   - Make sure you're connecting the right GitHub repository (not "Climeto")
   - The repository should contain your HRMS code

3. **Create Web Service**
   - Choose "Web Service"
   - Connect your repository
   - Configure:
     - **Name**: `hrms-app` (or your preferred name)
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn run:app`

4. **Add Environment Variables**
   ```
   FLASK_ENV=production
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///hrms.db
   ```

5. **Deploy**

### Step 3: Initialize Database (After First Deploy)

Once deployed, go to your Render dashboard and run this command in the Shell:

```bash
python3 -c "
from app import create_app, db
from app.models.employee import Employee
from app.models.auth import User

app = create_app()
with app.app_context():
    db.create_all()
    
    # Create admin user
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
        print('Admin user created successfully!')
"
```

## Troubleshooting

### If Build Still Fails:

1. **Check Repository**: Make sure you're deploying the correct repository
2. **Use Minimal Requirements**: Try with `requirements-minimal.txt`
3. **Python Version**: Render uses Python 3.11 by default

### If Database Issues:

1. **Add PostgreSQL**: 
   - Create a PostgreSQL database in Render
   - Update `DATABASE_URL` environment variable

2. **File Uploads**:
   - Configure file storage (Render doesn't persist files)
   - Consider using cloud storage (AWS S3, Cloudinary)

## Alternative Quick Deploy

If you want to try with minimal setup:

1. **Create a new `requirements.txt` with only essentials:**
   ```
   Flask==3.0.0
   Flask-Login==0.6.3
   Flask-SQLAlchemy==3.1.1
   gunicorn==21.2.0
   ```

2. **Deploy with basic functionality first**
3. **Add features incrementally**

## Success Indicators

✅ Build completes without errors
✅ App starts successfully  
✅ Can access login page
✅ Can login with admin/admin123
✅ Dashboard loads correctly

## Post-Deployment

- Test all functionality
- Set up proper database backups
- Configure domain name (optional)
- Set up monitoring/logging 