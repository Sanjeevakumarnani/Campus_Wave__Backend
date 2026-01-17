# CampusWave Backend

College Radio Application Backend built with Flask.

## Quick Setup (Windows)

1. **Copy the `.env.example` to `.env`** and update with your database credentials:
   ```
   copy .env.example .env
   notepad .env
   ```

2. **Run the setup script:**
   ```
   setup.bat
   ```

3. **Start the server:**
   ```
   venv\Scripts\activate
   python app.py
   ```

The server will run on `http://0.0.0.0:5000`

## Manual Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

## API Endpoints

- **Auth**: `/api/auth/` - Login, Register, OTP verification
- **Radios**: `/api/radios/` - CRUD for radio content
- **Updates**: `/api/updates/` - College updates/announcements
- **Banners**: `/api/banners/` - Banner management
- **Placements**: `/api/placements/` - Career opportunities
- **Live Stream**: `/api/live-stream/` - 24/7 radio control

## Android Configuration

Update `ApiConfig.kt` with your server's IP address:
```kotlin
const val BASE_URL = "http://YOUR_IP:5000/api/"
const val UPLOADS_URL = "http://YOUR_IP:5000/uploads/"
```

## Requirements

- Python 3.9+
- MySQL 8.0+
