#!/bin/bash

# HRMS Deployment Script
echo "🚀 HRMS Deployment Helper"
echo "========================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "Initializing Git..."
    git init
    git add .
    git commit -m "Initial commit"
fi

echo ""
echo "Choose deployment platform:"
echo "1. Heroku (Recommended - Easy)"
echo "2. Railway (Modern)"
echo "3. Render (Free tier)"
echo "4. AWS Elastic Beanstalk"
echo "5. Just prepare files"

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo "🟢 Deploying to Heroku..."
        
        # Check if Heroku CLI is installed
        if ! command -v heroku &> /dev/null; then
            echo "❌ Heroku CLI not found. Please install it first:"
            echo "https://devcenter.heroku.com/articles/heroku-cli"
            exit 1
        fi
        
        # Login and create app
        heroku login
        read -p "Enter your app name (e.g., my-hrms-app): " app_name
        heroku create $app_name
        
        # Set environment variables
        heroku config:set FLASK_ENV=production
        read -p "Enter a secret key (or press Enter for auto-generated): " secret_key
        if [ -z "$secret_key" ]; then
            secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        fi
        heroku config:set SECRET_KEY=$secret_key
        
        # Add PostgreSQL
        heroku addons:create heroku-postgresql:essential-0
        
        # Deploy
        git add .
        git commit -m "Deploy to Heroku"
        git push heroku main
        
        # Initialize database
        heroku run python3 -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
        
        echo "✅ Deployed! Opening app..."
        heroku open
        ;;
        
    2)
        echo "🟠 Preparing for Railway..."
        echo "1. Go to https://railway.app"
        echo "2. Connect your GitHub repository"
        echo "3. Railway will auto-detect your Flask app"
        echo "4. Add environment variables in dashboard:"
        echo "   - FLASK_ENV=production"
        echo "   - SECRET_KEY=your-secret-key"
        echo "5. Deploy automatically!"
        ;;
        
    3)
        echo "🟣 Preparing for Render..."
        echo "1. Go to https://render.com"
        echo "2. Connect GitHub repository"
        echo "3. Create Web Service"
        echo "4. Set:"
        echo "   - Build Command: pip install -r requirements.txt"
        echo "   - Start Command: gunicorn run:app"
        echo "5. Add environment variables"
        echo "6. Deploy!"
        ;;
        
    4)
        echo "🟡 Preparing for AWS Elastic Beanstalk..."
        
        # Check if EB CLI is installed
        if ! command -v eb &> /dev/null; then
            echo "Installing EB CLI..."
            pip install awsebcli
        fi
        
        # Initialize and deploy
        eb init -p python-3.9 hrms-application
        eb create hrms-production
        eb setenv FLASK_ENV=production
        read -p "Enter secret key: " secret_key
        eb setenv SECRET_KEY=$secret_key
        eb deploy
        eb open
        ;;
        
    5)
        echo "📁 Files prepared for deployment!"
        echo "Your deployment files are ready:"
        echo "- requirements.txt"
        echo "- Procfile (for Heroku)"
        echo "- runtime.txt (Python version)"
        echo "- application.py (for AWS EB)"
        echo "- .ebextensions/ (EB config)"
        ;;
        
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "📋 Post-deployment checklist:"
echo "✓ Set environment variables"
echo "✓ Initialize database"
echo "✓ Create admin user"
echo "✓ Test login functionality"
echo "✓ Upload test data"
echo ""
echo "🎉 Deployment complete!" 