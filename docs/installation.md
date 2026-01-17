# Installation

Interview Tracker is available for Windows, Linux, and macOS.

## Download

Go to the [Releases](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY/releases) page and download the latest version for your operating system.

- **Windows**: Download `interview-tracker-windows.zip`.
- **Linux**: Download `interview-tracker-linux.tar.gz`.
- **macOS**: Download `interview-tracker-macos.zip`.

## Setup

### Windows
1. Extract the downloaded zip file.
2. Run `Interview Tracker.exe`.
3. The application will start immediately.

### Linux
1. Extract the tarball: `tar -xzf interview-tracker-linux.tar.gz`.
2. Run the executable: `./Interview Tracker/Interview Tracker`.

### macOS
1. Extract the zip file.
2. Run `Interview Tracker.app`.

## Google Integration (Optional)

To enable syncing with Google Sheets and Calendar, you need a `credentials.json` file.

1. **Obtain Credentials**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a project and enable **Google Sheets API** and **Google Calendar API**.
   - Create OAuth 2.0 Desktop App credentials and download the JSON file.

2. **Upload to App**:
   - Open Interview Tracker.
   - Go to **Settings**.
   - Click **Upload credentials.json** and select your downloaded file.
   - Click **Authenticate with Google**.
