# OAuth Troubleshooting Guide

This guide helps you resolve common OAuth authentication issues with Strava.

## Common Error: "403. That's an error. We're sorry, but you do not have access to this page."

This error typically occurs during the OAuth redirect process and is almost always related to redirect URI configuration.

### Root Cause

The redirect URI used in the OAuth authorization request doesn't exactly match what's configured in your Strava API application settings.

### Solution Steps

1. **Go to your Strava API application settings:**
   - Visit [https://www.strava.com/settings/api](https://www.strava.com/settings/api)
   - Select your application or create a new one

2. **Configure the Authorization Callback Domain correctly:**
   
   For **production** (when your app is deployed):
   - Set Authorization Callback Domain to: `kompass-dev.streamlit.app`
   - **Important:** Do NOT include `https://` or trailing slash
   
   For **local development**:
   - Set Authorization Callback Domain to: `localhost`
   - **Important:** Do NOT include `http://` or port number

3. **Set your environment variables:**
   ```bash
   STRAVA_CLIENT_ID=your_client_id_here
   STRAVA_CLIENT_SECRET=your_client_secret_here
   
   # For local development, also set:
   STREAMLIT_ENV=development
   ```

4. **Restart your application** after making these changes.

### Technical Details

The app uses these redirect URIs:
- **Production:** `https://kompass-dev.streamlit.app/`
- **Local development:** `http://localhost:8501/`

The Authorization Callback Domain in Strava settings must match the domain portion of these URIs.

### Environment Detection

The app determines which redirect URI to use based on:
- `STREAMLIT_ENV=development`
- `ENVIRONMENT=development`
- `ENV=dev`
- Presence of `localhost` in `STREAMLIT_SERVER_ADDRESS`
- `STREAMLIT_SERVER_PORT=8501`

### Advanced Configuration

You can override the default redirect URIs with environment variables:
```bash
STRAVA_REDIRECT_URI_LOCAL=http://localhost:8501/
STRAVA_REDIRECT_URI_PROD=https://your-domain.com/
```

### Debugging

The app provides debug information in the OAuth section. Look for:
- Current redirect URI being used
- Environment detection status
- Client ID confirmation

### Still Having Issues?

1. **Double-check the domain exactly matches** between Strava settings and the redirect URI
2. **Clear your browser cache** and cookies for Strava
3. **Try the authorization flow in an incognito/private window**
4. **Check that your Client ID and Client Secret are correct**
5. **Ensure there are no typos** in your environment variables

### Other Common OAuth Errors

#### "invalid_client" Error
- Your `STRAVA_CLIENT_ID` or `STRAVA_CLIENT_SECRET` is incorrect
- Double-check these values from your Strava API settings

#### "invalid_grant" Error
- The authorization code has expired (they expire quickly)
- The authorization code has already been used
- Try the OAuth flow again

#### "access_denied" Error
- You clicked "Cancel" or "Deny" during the Strava authorization
- Try the OAuth flow again and click "Authorize"

### Testing Your Configuration

You can test your OAuth configuration by:
1. Starting the app
2. Looking at the debug information in the OAuth section
3. Verifying the redirect URI matches your Strava settings
4. Attempting the OAuth flow

The app will show detailed error messages if something goes wrong during token exchange.