# E-ZPass Fraud Detection System - Complete Setup Guide

## 🚀 Quick Start Overview

This guide will help you set up the complete E-ZPass fraud detection system with Azure integrations, email monitoring, and React dashboard.

**What you'll need to configure:**
1. Azure SQL Database
2. Azure OpenAI GPT-4 service  
3. Email account for CSV monitoring
4. SMTP service for fraud alerts
5. React frontend environment

---

## 📋 Prerequisites

Before starting, ensure you have:
- Node.js 18+ installed
- Azure subscription with SQL Database and OpenAI access
- Email account (Gmail, Outlook, etc.) for E-ZPass CSV monitoring
- SMTP credentials for sending fraud alerts

---

## 🗄️ 1. Azure SQL Database Setup

### Step 1: Create Azure SQL Database
1. Go to [Azure Portal](https://portal.azure.com)
2. Create new **SQL Database**
3. Note down these connection details:

```
Server: your-server.database.windows.net
Database: ezpass-fraud-db
Username: your-admin-username
Password: your-strong-password
```

### Step 2: Configure Firewall
1. In Azure SQL server settings, go to **Networking**
2. Add your IP address to firewall rules
3. Enable "Allow Azure services" if using Azure hosting

### Step 3: Run Database Schema

Connect to your database and run this SQL to create the required tables:

```sql
-- Create transactions table
CREATE TABLE transactions (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    transaction_id NVARCHAR(255) NOT NULL UNIQUE,
    account_id NVARCHAR(255),
    license_plate NVARCHAR(50),
    amount DECIMAL(10,2) NOT NULL,
    location NVARCHAR(255) NOT NULL,
    timestamp DATETIME2 NOT NULL,
    lane_id NVARCHAR(50),
    vehicle_class NVARCHAR(50),
    batch_id UNIQUEIDENTIFIER,
    created_at DATETIME2 DEFAULT GETDATE()
);

-- Create fraud_analysis table
CREATE TABLE fraud_analysis (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    transaction_id NVARCHAR(255) NOT NULL,
    is_fraud_flagged BIT NOT NULL DEFAULT 0,
    fraud_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    ai_reasoning NVARCHAR(MAX),
    risk_factors NVARCHAR(MAX),
    confidence_score DECIMAL(5,2),
    model_used NVARCHAR(100),
    analyzed_at DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);

-- Create processing_batches table
CREATE TABLE processing_batches (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    batch_id UNIQUEIDENTIFIER NOT NULL UNIQUE DEFAULT NEWID(),
    filename NVARCHAR(255),
    total_transactions INT DEFAULT 0,
    fraud_count INT DEFAULT 0,
    fraud_percentage DECIMAL(5,2) DEFAULT 0,
    processed_at DATETIME2 DEFAULT GETDATE(),
    alert_sent BIT DEFAULT 0,
    source NVARCHAR(100) DEFAULT 'email'
);

-- Create indexes for performance
CREATE INDEX IX_transactions_timestamp ON transactions(timestamp);
CREATE INDEX IX_transactions_batch_id ON transactions(batch_id);
CREATE INDEX IX_fraud_analysis_fraud_score ON fraud_analysis(fraud_score);
CREATE INDEX IX_fraud_analysis_transaction_id ON fraud_analysis(transaction_id);
```

---

## 🤖 2. Azure OpenAI Setup

### Step 1: Create Azure OpenAI Resource
1. In Azure Portal, create **Azure OpenAI** resource
2. Choose region with GPT-4 availability
3. Note your endpoint URL and keys

### Step 2: Deploy GPT-4 Model
1. Go to Azure OpenAI Studio
2. Deploy **GPT-4** model
3. Note the deployment name (usually "gpt-4")

### Step 3: Get Your Credentials
You'll need these values for your `.env` file:
```
Endpoint: https://your-openai-resource.openai.azure.com/
API Key: your-api-key-here
Deployment Name: gpt-4
```

---

## 📧 3. Email Account Setup

### For Gmail (Recommended):
1. Enable 2-factor authentication
2. Generate an **App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"

### For Outlook/Office365:
1. Use your regular email and password
2. Ensure IMAP is enabled in account settings

### Email Configuration Details:
```
IMAP Settings:
- Gmail: imap.gmail.com:993
- Outlook: outlook.office365.com:993

SMTP Settings (for alerts):
- Gmail: smtp.gmail.com:587
- Outlook: smtp.office365.com:587
```

---

## ⚙️ 4. Backend Configuration

### Step 1: Install Dependencies
```bash
cd backend
npm install
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` file with your actual values:

```env
# Database Configuration - FILL THESE IN
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=ezpass-fraud-db
AZURE_SQL_USERNAME=your-admin-username
AZURE_SQL_PASSWORD=your-strong-password

# Azure OpenAI Configuration - FILL THESE IN
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Email Monitoring Configuration - FILL THESE IN
EMAIL_MONITORING_ENABLED=true
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your-email@gmail.com
IMAP_PASS=your-app-password
IMAP_TLS=true

# Email Alert Configuration - FILL THESE IN  
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=your-email@gmail.com
SMTP_TO=fraud-alerts@yourcompany.com

# Processing Configuration (Optional - has defaults)
MAX_BATCH_SIZE=1000
FRAUD_RATE_ALERT_THRESHOLD=5.0
EMAIL_CHECK_INTERVAL=30000

# Server Configuration (Optional)
PORT=3001
NODE_ENV=development
```

### Step 3: Test Your Configuration
```bash
# Test database connection
npm run test-db

# Test email connection  
npm run test-email

# Test Azure OpenAI
npm run test-ai

# Start the server
npm start
```

### Step 4: Verify Health Check
Visit: `http://localhost:3001/health`

You should see all services showing as "healthy" or "configured".

---

## 🎨 5. Frontend Setup

### Step 1: Create React Frontend
```bash
# From the root directory
npx create-react-app frontend
cd frontend

# Install additional dependencies
npm install axios recharts lucide-react @headlessui/react
```

### Step 2: Configure API Connection
Create `frontend/src/config.js`:

```javascript
const config = {
  API_BASE_URL: process.env.NODE_ENV === 'production' 
    ? 'https://your-production-api.com/api'
    : 'http://localhost:3001/api'
};

export default config;
```

### Step 3: Environment Variables
Create `frontend/.env`:

```env
REACT_APP_API_URL=http://localhost:3001/api
REACT_APP_REFRESH_INTERVAL=30000
```

---

## 🧪 6. Testing the Complete System

### Step 1: Start Backend Server
```bash
cd backend
npm start
```

### Step 2: Start Frontend Development Server
```bash
cd frontend  
npm start
```

### Step 3: Test CSV Processing
1. Prepare a test CSV file with these columns:
   ```csv
   transaction_id,account_id,license_plate,amount,location,timestamp,lane_id,vehicle_class
   TXN001,ACC001,ABC123,2.50,"GW Bridge Plaza",2024-01-15 08:30:00,Lane1,Class1
   TXN002,ACC002,XYZ789,4.75,"Lincoln Tunnel",2024-01-15 08:35:00,Lane2,Class2
   ```

2. Test manual upload:
   - Go to your frontend dashboard
   - Upload the CSV file
   - Check that transactions appear in the system

3. Test email processing:
   - Send the CSV as attachment to your monitored email
   - Check logs to see automatic processing

---

## 🚨 7. Troubleshooting Common Issues

### Database Connection Issues:
```bash
# Test connection manually
node -e "
const { ConnectionPool } = require('mssql');
const config = {
  server: 'your-server.database.windows.net',
  database: 'ezpass-fraud-db',
  user: 'your-username',
  password: 'your-password',
  options: { encrypt: true }
};
new ConnectionPool(config).connect().then(() => console.log('DB OK')).catch(console.error);
"
```

### Azure OpenAI Issues:
- Verify your endpoint URL format
- Ensure GPT-4 model is deployed
- Check API key permissions

### Email Issues:
- For Gmail: Use App Password, not regular password
- Check firewall/antivirus blocking IMAP connections
- Verify email account has IMAP enabled

### Frontend API Issues:
- Check CORS settings in backend
- Verify API URL in frontend config
- Check browser network tab for errors

---

## 🚀 8. Production Deployment

### Backend Deployment (Azure App Service):
1. Create Azure App Service
2. Set environment variables in App Service configuration
3. Deploy from GitHub/VS Code
4. Update CORS origins to include your frontend domain

### Frontend Deployment (Azure Static Web Apps):
1. Build the React app: `npm run build`
2. Deploy to Azure Static Web Apps
3. Update API URL in production config

### Database Security:
- Remove "Allow Azure services" after deployment
- Add only necessary IP addresses to firewall
- Use Azure Key Vault for sensitive credentials

---

## 📊 9. Monitoring and Maintenance

### Log Files Location:
- Backend logs: `backend/logs/`
- Processing logs: Console output
- Database logs: Azure SQL Database metrics

### Key Metrics to Monitor:
- Fraud detection rate
- Email processing frequency  
- API response times
- Database connection health

### Regular Maintenance:
- Review fraud analysis accuracy monthly
- Update Azure OpenAI prompts based on new fraud patterns
- Archive old transaction data quarterly
- Update email monitoring rules as needed

---

## 🔧 10. Development Scripts

Add these to your `backend/package.json`:

```json
{
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "test-db": "node -e \"require('./services/database').testConnection()\"",
    "test-email": "node -e \"require('./services/email-service').testConnection()\"", 
    "test-ai": "node -e \"require('./services/fraud-detector').testConnection()\"",
    "process-csv": "node scripts/process-csv.js"
  }
}
```

---

## ✅ Final Checklist

Before going live:

- [ ] Database tables created and accessible
- [ ] Azure OpenAI GPT-4 deployed and responding
- [ ] Email monitoring receiving test emails
- [ ] SMTP alerts sending successfully  
- [ ] Frontend connecting to backend API
- [ ] Health check endpoint returning all green
- [ ] Test CSV processing end-to-end
- [ ] Production environment variables configured
- [ ] Security headers and CORS properly set
- [ ] Logging and monitoring in place

---

## 🆘 Need Help?

If you encounter issues:

1. Check the health endpoint: `http://localhost:3001/health`
2. Review console logs for specific error messages
3. Verify all credentials in `.env` file
4. Test each service individually using the test scripts
5. Check Azure resource status in Azure Portal

**Common credential locations:**
- Azure SQL: Azure Portal → SQL databases → Connection strings
- Azure OpenAI: Azure Portal → OpenAI resource → Keys and Endpoint  
- Email: Your email provider's IMAP/SMTP documentation

---

**🎉 Congratulations! Your E-ZPass fraud detection system is now ready to automatically monitor emails, process CSV files, detect fraud with AI, and alert you to suspicious activity!**