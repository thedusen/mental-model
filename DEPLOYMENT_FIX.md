# Deployment Fix: API URL Configuration

## Issue
The frontend is showing "Invalid graph data structure received from API" because it's trying to make API calls to `/api/graph` instead of the full deployed backend URL.

## Root Cause
The frontend components `GraphViewD3.js` and `GraphViewSimple.js` were using relative URLs (`/api/graph`) instead of the full API URL with the environment variable.

## Fix Applied
✅ **Fixed GraphViewD3.js** - Now uses `${API_URL}/api/graph`
✅ **Fixed GraphViewSimple.js** - Now uses `${API_URL}/api/graph`

## Next Steps

### 1. Set Environment Variable in Vercel
1. Go to your Vercel dashboard: https://vercel.com/dashboard
2. Navigate to your `mental-model-frontend` project
3. Go to **Settings** → **Environment Variables**
4. Add a new environment variable:
   - **Name:** `REACT_APP_API_URL`
   - **Value:** Your deployed backend URL (e.g., `https://your-backend.railway.app`)
   - **Environment:** Production (and Preview if desired)
5. Click **Save**

### 2. Redeploy Frontend
After setting the environment variable, you need to redeploy:
- **Option A:** Push a new commit to trigger automatic deployment
- **Option B:** Go to Vercel dashboard → Deployments → Click "Redeploy" on the latest deployment

### 3. Verify the Fix
After redeployment, the frontend should:
- Load the graph data successfully
- Show the interactive D3 visualization
- Allow chat functionality

## Testing Locally
To test locally, you can:
1. Create a `.env` file in the `frontend/` directory
2. Add: `REACT_APP_API_URL=http://localhost:8000`
3. Run `npm start` in the frontend directory

## Backend URL Examples
- Railway: `https://your-app-name.railway.app`
- Render: `https://your-app-name.onrender.com`
- Heroku: `https://your-app-name.herokuapp.com`
- DigitalOcean: `https://your-app-name.ondigitalocean.app`

## Troubleshooting
If the issue persists:
1. Check browser console for CORS errors
2. Verify the backend URL is correct and accessible
3. Ensure the backend is running and responding to `/api/graph` endpoint
4. Check that the environment variable is set correctly in Vercel 