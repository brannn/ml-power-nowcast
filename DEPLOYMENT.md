# Power Demand Dashboard Deployment Guide

This guide shows you how to deploy your power demand forecasting system with:
- **Local ML API** running on your M4 Mac Mini
- **Interactive Dashboard** hosted on Fly.io
- **Real-time data flow** between local and cloud

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   M4 Mac Mini   │    │     Internet     │    │     Fly.io      │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ ML Models   │ │    │ │    ngrok     │ │    │ │  Dashboard  │ │
│ │ Data Proc.  │ │◄───┤ │   Tunnel     │ ├────┤ │  (Next.js)  │ │
│ │ FastAPI     │ │    │ │              │ │    │ │             │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

1. **Fly.io Account**: Sign up at https://fly.io
2. **Fly CLI**: Install flyctl
3. **ngrok Account**: For exposing local API (free tier works)
4. **Your M4 Mac Mini**: With the ML models running

## 🚀 Step 1: Set Up Local API Server

### 1.1 Start the Local API
```bash
# In your project root
cd /Users/bran/Work/model-power-nowcast
source .venv/bin/activate
python src/api/prediction_server.py
```

The API will be available at `http://localhost:8000`

### 1.2 Test the API
```bash
# Test health check
curl http://localhost:8000/

# Test prediction endpoint
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"temperature": 28.5, "humidity": 65, "wind_speed": 3.2}'
```

### 1.3 Expose API with ngrok
```bash
# Install ngrok if you haven't
brew install ngrok

# Expose your local API
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

## 🤖 Step 2: Set Up Automated Pipeline

### 2.1 Configure Automated Data Pipeline
```bash
# Make scripts executable
chmod +x scripts/automated_pipeline.py
chmod +x scripts/setup_cron.sh

# Test the pipeline
python scripts/automated_pipeline.py --dry-run

# Set up cron jobs for automation
./scripts/setup_cron.sh
```

### 2.2 Pipeline Schedule
- **Every 15 minutes**: Fresh predictions generated
- **Every 6 hours**: New data ingestion from CAISO
- **Daily at 2 AM**: Model retraining if needed
- **Daily at 3 AM**: Full pipeline backup run

### 2.3 S3 Data Structure
```
s3://ml-power-nowcast-data-1756420517/
├── data/raw/           # Raw CAISO/weather data
├── data/processed/     # Feature-engineered data
├── forecasts/          # Live predictions (JSON)
│   └── latest.json     # Current 6-hour forecast
├── models/             # Model artifacts
│   ├── latest_metrics.json
│   └── last_training.txt
└── metrics/            # Performance tracking
```

## 🌐 Step 3: Deploy Dashboard to Fly.io

### 2.1 Install Fly CLI
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
flyctl auth login
```

### 2.2 Configure Environment
Update the `fly.toml` file with your ngrok URL:

```toml
[env]
  NODE_ENV = "production"
  NEXT_PUBLIC_API_URL = "https://your-ngrok-url.ngrok.io"
```

### 2.3 Deploy to Fly.io
```bash
# In the dashboard directory
cd dashboard

# Deploy the app
flyctl deploy
```

## 🔧 Step 3: Configuration Options

### 3.1 Environment Variables

**Local API (.env file):**
```bash
# Optional: Configure AWS credentials if not using default profile
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-west-1

# Optional: Configure API settings
API_HOST=0.0.0.0
API_PORT=8000
```

**Dashboard (fly.toml):**
```toml
[env]
  NODE_ENV = "production"
  NEXT_PUBLIC_API_URL = "https://your-ngrok-url.ngrok.io"
  # Optional: Add analytics, monitoring
  NEXT_PUBLIC_ANALYTICS_ID = "your_analytics_id"
```

### 3.2 Security Considerations

1. **API Security**: Add API key authentication
2. **CORS**: Configure allowed origins
3. **Rate Limiting**: Implement request throttling
4. **HTTPS**: Always use HTTPS in production

## 📊 Step 4: Monitoring & Maintenance

### 4.1 Local API Monitoring
```bash
# Check API logs
tail -f api.log

# Monitor system resources
htop

# Check model performance
curl http://localhost:8000/metrics
```

### 4.2 Dashboard Monitoring
```bash
# Check Fly.io app status
flyctl status

# View logs
flyctl logs

# Scale if needed
flyctl scale count 2
```

### 4.3 Data Pipeline Maintenance
```bash
# Update models (run periodically)
python src/models/retrain_models.py

# Refresh data
python scripts/collect_recent_data.py

# Backup models
aws s3 cp models/ s3://your-backup-bucket/models/ --recursive
```

## 🔄 Step 5: Automated Deployment

### 5.1 GitHub Actions (Optional)
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Dashboard
on:
  push:
    branches: [main]
    paths: ['dashboard/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        working-directory: ./dashboard
```

### 5.2 Model Retraining Schedule
```bash
# Add to crontab for daily retraining
0 2 * * * cd /Users/bran/Work/model-power-nowcast && source .venv/bin/activate && python src/models/retrain_models.py
```

## 🛠️ Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check if local API is running: `curl http://localhost:8000/`
   - Verify ngrok tunnel: `ngrok status`
   - Check firewall settings

2. **Dashboard Build Failed**
   - Verify all dependencies: `npm install`
   - Check Next.js config: `npm run build`
   - Review Fly.io logs: `flyctl logs`

3. **Model Prediction Errors**
   - Check data availability: `python -c "import boto3; print(boto3.client('s3').list_objects_v2(Bucket='ml-power-nowcast-data-1756420517'))"`
   - Verify model files exist
   - Check AWS credentials

4. **Performance Issues**
   - Monitor API response times
   - Scale Fly.io app: `flyctl scale count 2`
   - Optimize model inference

### Debug Commands
```bash
# Test local API endpoints
curl http://localhost:8000/status
curl http://localhost:8000/metrics
curl http://localhost:8000/historical?days=1

# Test dashboard locally
cd dashboard
npm run dev

# Check Fly.io deployment
flyctl status
flyctl logs --app power-demand-dashboard
```

## 📈 Next Steps

1. **Enhanced Security**: Add authentication, API keys
2. **Real-time Updates**: WebSocket connections for live data
3. **Mobile App**: React Native version
4. **Advanced Analytics**: Add more ML insights
5. **Alerting**: Set up notifications for anomalies

## 🎯 Production Checklist

- [ ] Local API running and accessible
- [ ] ngrok tunnel established
- [ ] Dashboard deployed to Fly.io
- [ ] Environment variables configured
- [ ] SSL/HTTPS enabled
- [ ] Monitoring set up
- [ ] Backup strategy implemented
- [ ] Documentation updated

Your power demand forecasting system is now live! 🚀

**Local API**: http://localhost:8000
**Public Dashboard**: https://power-demand-dashboard.fly.dev
**API Docs**: http://localhost:8000/docs
