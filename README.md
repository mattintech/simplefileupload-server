# Simple File Upload Server

A lightweight Flask-based file upload and download server with a modern UI. Perfect for temporary file sharing and mobile app log uploads.

## Features
- Clean, modern UI for file downloads
- Mobile-friendly upload endpoint
- Secure 6-digit alphanumeric code system
- Automatic file cleanup
- Configurable download limits and expiry times
- User-friendly error pages
- Docker support

## Architecture
Built using the MVC design pattern:
- **Model**: File metadata management (code, path, downloads, expiry)
- **View**: Modern HTML templates with client-side validation
- **Controller**: Upload/download logic with error handling

## Getting Started

### Local Development
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python src/app.py
```

### Docker Deployment
```bash
# Build the image
docker build -t file-upload-server .

# Run the container
docker run -p 7777:7777 -v $(pwd)/tmp:/app/tmp file-upload-server
```

## API Endpoints

### POST /upload
Upload a file and receive a download code.

**Form Fields:**
- `file`: File to upload (required)
- `max_downloads`: Maximum download count (optional, default: 1)
- `expiry_hours`: Hours until expiry (optional, default: 24, max: 24)

**Response:**
```json
{
  "code": "ABC123"
}
```

### GET /download/{code}
Download a file using a 6-character code.

**Responses:**
- 200: File download starts
- 404: File not found with specific error page for:
  - Invalid code
  - Expired file
  - Download limit reached
  - File no longer exists

## Security Notes
- Files are automatically deleted after:
  - Reaching download limit
  - Exceeding expiry time
  - Server restart (temporary storage)
- No file execution permissions in upload directory
- Secure filename handling

## Configuration
All configuration is handled through environment variables:
- `UPLOAD_FOLDER`: Upload directory path (default: tmp/uploads)
- `MAX_CONTENT_LENGTH`: Maximum file size (default: 16MB)
- `DEBUG`: Enable debug mode (default: False)

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
