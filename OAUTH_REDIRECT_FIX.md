# OAuth Redirect Configuration Fix

## Problem
The development branch (`https://mental-model-frontend-qrqc6ar1n-sound-8957s-projects.vercel.app`) is redirecting users to the production URL instead of the development URL after OAuth authentication.

## Root Cause
Supabase OAuth configuration only allows the production URL as a valid redirect destination. When users authenticate on the development environment, Supabase redirects them to the production URL because it's the only configured redirect URL.

## Solution

### Step 1: Update Supabase Dashboard Configuration

1. **Go to Supabase Dashboard**: https://supabase.com/dashboard
2. **Select your project**
3. **Navigate to**: Authentication → URL Configuration
4. **Add Development URL**: In the "Redirect URLs" section, add:
   ```
   https://mental-model-frontend-qrqc6ar1n-sound-8957s-projects.vercel.app/auth/callback
   ```
5. **Keep existing Production URL**:
   ```
   https://mental-model-frontend.vercel.app/auth/callback
   ```
6. **Save Configuration**

### Step 2: Verify Environment Variables

Ensure the development deployment has the correct Supabase environment variables:
- `REACT_APP_SUPABASE_URL`: Should point to your Supabase project
- `REACT_APP_SUPABASE_ANON_KEY`: Should be the anon key for your project

### Step 3: Test the Fix

1. **Deploy the updated code** to the development branch
2. **Try signing in** on the development URL
3. **Verify** that after OAuth, users are redirected back to the development URL instead of production

## Alternative Solutions

### Option A: Separate Supabase Projects
If you want complete environment isolation:
- Create a separate Supabase project for development
- Use different environment variables for dev vs prod
- Each project can have its own OAuth configuration

### Option B: Dynamic Redirect Configuration
Modify the authentication code to handle multiple environments automatically (already implemented in the updated code with logging).

## Files Modified
- `frontend/src/utils/supabase.js`: Added logging for OAuth redirect URL debugging

## Notes
- The main issue is on the Supabase configuration side, not the code
- Both development and production URLs must be explicitly allowed in Supabase
- Vercel preview deployments generate dynamic URLs, so you may need to add new URLs as deployments are created