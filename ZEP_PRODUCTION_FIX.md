# 🚨 Zep Production Issue - Complete Fix Guide

## Issue Summary

**Problem**: Users are not being created in the production Zep environment  
**Root Cause**: Invalid/expired Zep API key causing `401 Unauthorized` errors  
**Impact**: User context features completely disabled, no personalization working  
**Severity**: HIGH - Core functionality broken  

## Diagnostic Results

```bash
# API Key Test Result
curl -H "Authorization: Bearer [CURRENT_KEY]" "https://api.getzep.com/api/v2/users-ordered"
# Response: "unauthorized" (401 status)
```

**Findings**:
1. ❌ Current API key is invalid or expired
2. ❌ All Zep API calls failing with 401 errors  
3. ❌ Circuit breakers opening due to repeated failures
4. ✅ Application gracefully degrades but loses key features
5. ✅ Code implementation and logic are correct

## Immediate Fix Required

### Step 1: Generate New Zep API Key

1. **Access Zep Cloud Dashboard**
   - Go to https://cloud.getzep.com
   - Log in with your account credentials

2. **Generate New API Key**
   - Navigate to "API Keys" or "Settings" section
   - Click "Generate New API Key" or "Create Key"
   - Copy the new key immediately (you won't see it again)
   - Ensure the key has all required permissions:
     - ✅ User management
     - ✅ Memory operations  
     - ✅ Graph operations

3. **Verify Key Format**
   - New key should start with `zep_` or `z_`
   - Should be 40+ characters long
   - No spaces or newlines

### Step 2: Update Production Environment

**For Railway Deployment:**
```bash
# Set environment variable in Railway dashboard
ZEP_API_KEY=zep_your_new_api_key_here
```

**For Local Development:**
```bash
# Update backend/.env file
ZEP_API_KEY=zep_your_new_api_key_here
ZEP_API_URL=https://api.getzep.com
```

**For Other Platforms:**
Update the `ZEP_API_KEY` environment variable in your deployment platform's settings.

### Step 3: Restart Application

After updating the API key:

```bash
# Restart the backend service to reload environment variables
# This will also reset the circuit breakers
```

### Step 4: Verify Fix

Use the new validation script:

```bash
cd backend
python3 zep_api_validator.py
```

Expected output:
```
🔍 Zep API Validation Suite
==================================================

📊 Validation Results
==================================================
✅ API Key Format: API key format is valid
✅ API Connectivity: Success
✅ User Creation: Success

🎉 Overall Status: SUCCESS
```

## Verification Steps

### 1. Check Health Endpoint

```bash
curl https://your-api-url.com/health
```

Look for:
```json
{
  "status": "healthy",
  "services": {
    "zep": {
      "status": "connected",
      "api_url": "https://api.getzep.com"
    }
  }
}
```

### 2. Test User Creation

```bash
curl -X POST https://your-api-url.com/api/user/business-data \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "data": {
      "company": "Test Company",
      "challenge": "Testing Zep integration"
    }
  }'
```

### 3. Verify User Exists in Zep

Check your Zep dashboard to confirm users are being created.

## Enhanced Monitoring

The updated configuration now includes:

### 1. Better Error Messages
```
🚨 CRITICAL: Zep API key is invalid or expired!
   -> Generate a new API key from https://cloud.getzep.com
   -> Update ZEP_API_KEY environment variable
```

### 2. API Key Format Validation
- Checks key starts with `zep_` or `z_`
- Validates minimum length
- Detects whitespace issues
- Catches copy-paste errors

### 3. Enhanced Health Reporting
- Detailed connection status
- User count reporting
- Specific error guidance

## Prevention Measures

### 1. API Key Rotation Schedule
- Set calendar reminder to rotate Zep API keys every 90 days
- Test new keys in staging before production deployment

### 2. Monitoring Alerts
Set up alerts for:
- Zep API error rate > 5%
- Circuit breaker state = OPEN
- Health check failures

### 3. Automated Testing
```bash
# Add to CI/CD pipeline
python3 backend/zep_api_validator.py
```

## Testing Checklist

After applying the fix, verify:

- [ ] Health endpoint shows Zep as "connected"
- [ ] New users can be created via API
- [ ] Chat responses include user context
- [ ] Business profile questions are saved to Zep
- [ ] User knowledge graphs are populated
- [ ] No circuit breaker alerts
- [ ] Application logs show successful Zep operations

## Rollback Plan

If issues persist after API key update:

1. **Temporarily disable Zep**: Remove `ZEP_API_KEY` from environment
2. **Application will gracefully degrade**: Core chat still works
3. **Debug with validation script**: Run detailed diagnostics
4. **Check Zep service status**: https://status.getzep.com
5. **Contact Zep support**: If service-side issues

## Long-term Improvements

### 1. API Key Management
- Consider using secret management service (AWS Secrets Manager, etc.)
- Implement key rotation automation

### 2. Enhanced Error Handling
- Add retry logic with exponential backoff
- Implement dead letter queues for failed operations

### 3. Observability
- Add Zep operation metrics to monitoring dashboard
- Set up Zep-specific logging and alerts

## Support Resources

- **Zep Documentation**: https://docs.getzep.com
- **API Reference**: https://docs.getzep.com/api
- **Community**: https://discord.gg/zep
- **Status Page**: https://status.getzep.com

---

**Priority**: Immediate action required - core functionality is broken
**Estimated Fix Time**: 10 minutes (API key generation + deployment restart)
**Verification Time**: 5 minutes using validation script