# KOMpass - Strava API Speed Forecasting Application

KOMpass is a Python Streamlit web application that forecasts rider speed using the Strava API. It displays README content and athlete information from Strava.

**CRITICAL: Always follow these instructions first. Only fallback to additional search and context gathering if the information in these instructions is incomplete or found to be in error.**

## Working Effectively

### Bootstrap and Dependencies
- Install Streamlit (required dependency):
  ```bash
  pip3 install streamlit
  ```
  - **TIMING**: Installation takes approximately 18 seconds. NEVER CANCEL - set timeout to 60+ minutes to be safe.
  - **NOTE**: `requests` library is already available in most Python environments.

### Build and Validation
- **NO BUILD STEP REQUIRED**: This is a pure Python application with no compilation or build process.
- Validate Python syntax:
  ```bash
  python3 -m py_compile main.py strava_connect.py
  ```
  - Should complete in under 2 seconds with no output if successful.

### Running the Application
- **Basic startup** (local development):
  ```bash
  streamlit run main.py
  ```
  - **TIMING**: Startup takes 5-8 seconds. Application runs on http://localhost:8501
  - **CRITICAL**: App will display connection errors for Strava API without proper environment variables - this is expected behavior.

- **Headless mode** (for testing/CI):
  ```bash
  streamlit run main.py --server.headless true
  ```

- **With environment variables** (for full functionality):
  ```bash
  STRAVA_CLIENT_SECRET=your_secret STRAVA_ACCESS_TOKEN=your_token STRAVA_REFRESH_TOKEN=your_refresh streamlit run main.py
  ```

### Required Environment Variables
The application requires these Strava API credentials for full functionality:
- `STRAVA_CLIENT_SECRET`: Strava application client secret
- `STRAVA_ACCESS_TOKEN`: User access token
- `STRAVA_REFRESH_TOKEN`: Token refresh credential

**NOTE**: Application will start and display README content without these variables, but Strava athlete information will show connection errors.

### Testing and Validation
- **NO AUTOMATED TESTS**: This repository currently has no test suite.
- **Manual validation steps**:
  1. Start the application: `streamlit run main.py --server.headless true`
  2. Verify app responds: `curl http://localhost:8501` should return HTML content
  3. Check that README content is displayed in the web interface
  4. Verify Strava error handling when API credentials are missing (expected behavior)
  5. Stop the application: `pkill -f streamlit` or Ctrl+C

### Code Quality
- **NO LINTING TOOLS CONFIGURED**: Repository has no flake8, black, or other linting tools setup.
- **Manual code check**: Use `python3 -m py_compile` to verify syntax only.
- **IMPORTANT**: Always run syntax validation before committing changes.

## Project Structure

### Repository Layout
```
.
├── .devcontainer/
│   └── devcontainer.json      # Development container configuration
├── .github/
│   └── copilot-instructions.md # This file
├── .gitignore                 # Python gitignore rules
├── README.md                  # Project documentation
├── main.py                    # Main Streamlit application
└── strava_connect.py          # Strava API integration module
```

### Key Files
- **`main.py`**: Main Streamlit application that displays README content and athlete information
- **`strava_connect.py`**: Handles Strava API authentication and requests
- **`.devcontainer/devcontainer.json`**: Configured for Python 3.11 with automatic Streamlit startup

## Validation Scenarios

### Complete End-to-End Validation
After making any changes, always run through this complete scenario:

1. **Environment Setup**:
   ```bash
   pip3 install streamlit
   ```

2. **Syntax Validation**:
   ```bash
   python3 -m py_compile main.py strava_connect.py
   ```

3. **Application Startup**:
   ```bash
   streamlit run main.py --server.headless true &
   ```

4. **Functionality Testing**:
   ```bash
   sleep 8
   curl -s "http://localhost:8501" | head -10
   ```
   - Should return HTML content starting with `<!DOCTYPE html>`

5. **Cleanup**:
   ```bash
   pkill -f streamlit
   ```

### Network and API Dependencies
- **External Dependency**: Application connects to `www.strava.com` API
- **Expected Behavior**: Without valid API credentials, application shows connection errors but continues to function for README display
- **Testing Note**: Use mock environment variables for testing without real API access

## Development Environment

### Devcontainer Configuration
- **Base Image**: `mcr.microsoft.com/devcontainers/python:1-3.11-bullseye`
- **Auto-startup**: Streamlit automatically starts on container attach
- **Port**: Application exposed on port 8501
- **Extensions**: Python and Pylance extensions configured

### Common Commands Reference
```bash
# Start development server
streamlit run main.py

# Start with custom port
streamlit run main.py --server.port 8502

# Check Python syntax
python3 -m py_compile *.py

# Test API module standalone (requires network)
python3 strava_connect.py

# Install dependencies
pip3 install streamlit
```

## Troubleshooting

### Common Issues
1. **"streamlit not found"**: Run `pip3 install streamlit`
2. **"Connection error to Strava"**: Expected without valid API credentials
3. **"Port already in use"**: Use different port with `--server.port` option
4. **Application won't start**: Check Python syntax with `python3 -m py_compile`

### Performance Notes
- **Startup Time**: 5-8 seconds (fast)
- **Installation Time**: ~18 seconds for Streamlit
- **Resource Usage**: Minimal - single Python process
- **No long-running builds**: All operations complete quickly

## CI/CD Considerations
- **No automated workflows**: Repository has no GitHub Actions configured
- **Manual validation required**: Follow validation scenarios above
- **Dependencies**: Only Streamlit needs installation
- **Environment**: Requires Python 3.11+ environment