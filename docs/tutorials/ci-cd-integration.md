# CI/CD Integration Guide

This guide covers integrating Shopify Nano-SRE into your CI/CD pipeline to automatically monitor your Shopify store during deployments and on a scheduled basis.

## Overview

Integrating Nano-SRE into your CI/CD pipeline provides:

- **Pre-deployment checks**: Verify store health before deploying changes
- **Post-deployment validation**: Ensure deployments didn't break critical functionality
- **Scheduled monitoring**: Run checks on a cron schedule
- **Automated alerts**: Get notified of issues without manual intervention

## GitHub Actions Integration

### Basic Workflow

Create `.github/workflows/shopify-monitoring.yml`:

```yaml
name: Shopify Store Monitoring

on:
  # Run on every push to main
  push:
    branches: [main]
  
  # Run on pull requests
  pull_request:
    branches: [main]
  
  # Run on a schedule (every hour)
  schedule:
    - cron: '0 * * * *'
  
  # Allow manual triggering
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Shopify Nano-SRE
        run: |
          pip install shopify-nano-sre
          playwright install chromium
      
      - name: Run store audit
        env:
          STORE_URL: ${{ secrets.STORE_URL }}
          LLM_PROVIDER: ${{ secrets.LLM_PROVIDER }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_MODEL: ${{ secrets.LLM_MODEL }}
        run: |
          nano-sre audit --url $STORE_URL --output audit-report.json
      
      - name: Upload audit report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: audit-report
          path: audit-report.json
```

### Required Secrets

Add these secrets to your GitHub repository (Settings > Secrets and variables > Actions):

- `STORE_URL`: Your Shopify store URL
- `LLM_PROVIDER`: Your LLM provider (e.g., `openai`)
- `LLM_API_KEY`: Your LLM API key
- `LLM_MODEL`: Your LLM model (e.g., `gpt-4`)

### Advanced Workflow with Alerts

For production use, add Slack/Discord notifications:

```yaml
name: Shopify Store Monitoring with Alerts

on:
  schedule:
    - cron: '*/30 * * * *'  # Every 30 minutes

jobs:
  monitor:
    runs-on: ubuntu-latest
    
    steps:
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Shopify Nano-SRE
        run: |
          pip install shopify-nano-sre
          playwright install chromium
      
      - name: Run store audit
        id: audit
        env:
          STORE_URL: ${{ secrets.STORE_URL }}
          LLM_PROVIDER: ${{ secrets.LLM_PROVIDER }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_MODEL: ${{ secrets.LLM_MODEL }}
        run: |
          nano-sre audit --url $STORE_URL --output audit-report.json
        continue-on-error: true
      
      - name: Parse audit results
        id: results
        run: |
          FAILED=$(jq '[.results[] | select(.status == "FAIL")] | length' audit-report.json)
          WARNED=$(jq '[.results[] | select(.status == "WARN")] | length' audit-report.json)
          echo "failed=$FAILED" >> $GITHUB_OUTPUT
          echo "warned=$WARNED" >> $GITHUB_OUTPUT
      
      - name: Send Slack notification on failure
        if: steps.results.outputs.failed > 0
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          payload: |
            {
              "text": "🚨 Shopify store health check failed!",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Shopify Store Monitor Alert*\n${{ steps.results.outputs.failed }} checks failed, ${{ steps.results.outputs.warned }} warnings"
                  }
                }
              ]
            }
      
      - name: Upload audit report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: audit-report-${{ github.run_number }}
          path: audit-report.json
```

## Docker Deployment

### Using Docker Compose

Use the provided `docker-compose.yml` in `docs/examples/`:

```bash
cd docs/examples
cp .env.docker.example .env
# Edit .env with your configuration
docker-compose up -d
```

This will:
- Build the Nano-SRE container
- Run scheduled checks based on `CHECK_INTERVAL_MINUTES`
- Store monitoring data in a persistent SQLite volume

### Standalone Docker

Build and run manually:

```bash
# Build the image
docker build -t shopify-nano-sre .

# Run with environment variables
docker run -d \
  -e STORE_URL=https://your-store.myshopify.com \
  -e LLM_PROVIDER=openai \
  -e LLM_API_KEY=sk-your-key \
  -e LLM_MODEL=gpt-4 \
  -v $(pwd)/data:/app/data \
  shopify-nano-sre
```

### Docker with Cron

For scheduled monitoring in Docker:

```dockerfile
FROM shopify-nano-sre:latest

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Add crontab file
COPY crontab /etc/cron.d/nano-sre-cron
RUN chmod 0644 /etc/cron.d/nano-sre-cron
RUN crontab /etc/cron.d/nano-sre-cron

# Start cron
CMD ["cron", "-f"]
```

Create `crontab`:

```
# Run every 30 minutes
*/30 * * * * cd /app && nano-sre audit --url $STORE_URL --output /app/data/audit-$(date +\%Y\%m\%d-\%H\%M).json >> /var/log/cron.log 2>&1
```

## GitLab CI Integration

Create `.gitlab-ci.yml`:

```yaml
stages:
  - monitor

shopify_monitor:
  stage: monitor
  image: python:3.11-slim
  
  before_script:
    - pip install shopify-nano-sre
    - playwright install chromium
  
  script:
    - nano-sre audit --url $STORE_URL --output audit-report.json
  
  artifacts:
    reports:
      junit: audit-report.json
    when: always
  
  only:
    - schedules
    - main
  
  variables:
    STORE_URL: $STORE_URL
    LLM_PROVIDER: $LLM_PROVIDER
    LLM_API_KEY: $LLM_API_KEY
    LLM_MODEL: $LLM_MODEL
```

## Jenkins Integration

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any
    
    environment {
        STORE_URL = credentials('shopify-store-url')
        LLM_API_KEY = credentials('llm-api-key')
        LLM_PROVIDER = 'openai'
        LLM_MODEL = 'gpt-4'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install shopify-nano-sre'
                sh 'playwright install chromium'
            }
        }
        
        stage('Monitor') {
            steps {
                sh 'nano-sre audit --url $STORE_URL --output audit-report.json'
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'audit-report.json', allowEmptyArchive: true
        }
        failure {
            mail to: 'team@example.com',
                 subject: "Shopify Monitor Failed: ${env.JOB_NAME}",
                 body: "Check ${env.BUILD_URL} for details"
        }
    }
}
```

## Kubernetes Deployment

### CronJob for Scheduled Monitoring

Create `k8s/cronjob.yaml`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: shopify-nano-sre
spec:
  schedule: "*/30 * * * *"  # Every 30 minutes
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: nano-sre
            image: shopify-nano-sre:latest
            command:
            - nano-sre
            - audit
            - --url
            - $(STORE_URL)
            - --output
            - /reports/audit-report.json
            env:
            - name: STORE_URL
              valueFrom:
                secretKeyRef:
                  name: nano-sre-secrets
                  key: store-url
            - name: LLM_API_KEY
              valueFrom:
                secretKeyRef:
                  name: nano-sre-secrets
                  key: llm-api-key
            - name: LLM_PROVIDER
              value: "openai"
            - name: LLM_MODEL
              value: "gpt-4"
            volumeMounts:
            - name: reports
              mountPath: /reports
          volumes:
          - name: reports
            persistentVolumeClaim:
              claimName: nano-sre-reports
          restartPolicy: OnFailure
```

Create secrets:

```bash
kubectl create secret generic nano-sre-secrets \
  --from-literal=store-url=https://your-store.myshopify.com \
  --from-literal=llm-api-key=sk-your-key
```

## Vercel/Netlify Serverless

For serverless deployments, create an API endpoint:

### Vercel

Create `api/monitor.py`:

```python
from http.server import BaseHTTPRequestHandler
import asyncio
from nano_sre.agent.core import Agent
from nano_sre.config.settings import Settings
from nano_sre.skills import PixelAuditor

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        async def run_audit():
            settings = Settings()
            agent = Agent(settings)
            agent.register_skill(PixelAuditor())
            
            results = await agent.execute_skills()
            return results
        
        results = asyncio.run(run_audit())
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(str(results).encode())
```

Configure in `vercel.json`:

```json
{
  "functions": {
    "api/monitor.py": {
      "runtime": "python3.11",
      "maxDuration": 60
    }
  }
}
```

## Pre-deployment Checks

### Block Deployments on Failure

In GitHub Actions:

```yaml
- name: Pre-deployment health check
  run: |
    nano-sre audit --url https://staging.myshopify.com
    
- name: Deploy to production
  if: success()
  run: |
    # Your deployment commands
```

### Post-deployment Validation

```yaml
- name: Deploy to production
  run: |
    # Your deployment commands
    
- name: Post-deployment validation
  run: |
    sleep 60  # Wait for deployment to propagate
    nano-sre audit --url https://your-store.myshopify.com
    
- name: Rollback on failure
  if: failure()
  run: |
    # Your rollback commands
```

## Alert Configuration

### Slack Webhooks

Add to your `.env`:

```bash
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Discord Webhooks

```bash
ALERT_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
```

### Custom Webhooks

The webhook will receive a POST request with:

```json
{
  "status": "FAIL",
  "store_url": "https://your-store.myshopify.com",
  "failed_skills": ["PixelAuditor"],
  "timestamp": "2026-02-17T21:00:00Z",
  "details": "Facebook pixel not firing on checkout"
}
```

## Best Practices

### Frequency Recommendations

- **Development**: Run on every commit/PR
- **Staging**: Every 30 minutes
- **Production**: Every 15 minutes for critical stores

### Resource Management

- Use `playwright install chromium` (not all browsers)
- Set reasonable timeouts in CI (60-120 seconds)
- Cache dependencies when possible

### Security

- Never commit API keys to version control
- Use environment variables or secrets management
- Rotate API keys regularly
- Use separate API keys for dev/staging/production

## Troubleshooting

### CI Timeout Issues

Increase timeout or reduce check frequency:

```yaml
timeout-minutes: 10  # GitHub Actions
```

### Memory Issues in Docker

Increase container memory:

```yaml
services:
  nano-sre:
    mem_limit: 2g
```

### Rate Limiting

If hitting LLM API rate limits, add delay between checks:

```bash
CHECK_INTERVAL_MINUTES=60  # Increase interval
```

## Next Steps

- [Custom Skills Guide](./custom-skills.md) - Create monitoring checks specific to your store
- [GitHub Actions Docs](https://docs.github.com/en/actions) - Learn more about GitHub Actions
- [Docker Compose Docs](https://docs.docker.com/compose/) - Docker Compose reference

## Example Configurations

See `docs/examples/` for complete example configurations:

- `.env.ci.example` - CI/CD environment variables
- `.env.docker.example` - Docker deployment configuration
- `docker-compose.yml` - Complete Docker Compose setup
