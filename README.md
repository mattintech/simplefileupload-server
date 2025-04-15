# Simple File Upload Server

A lightweight Flask-based file upload and download server with a modern UI. Perfect for temporary file sharing and mobile app log uploads.

## Features
- Clean, modern UI for file downloads
- Secure API authentication for uploads
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
1. Clone the repository
2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Set your `CLIENT_KEY` in the `.env` file
   - Adjust other settings as needed

5. Run the server:
```bash
python src/app.py
```

### Docker Deployment
1. Build the image:
```bash
docker build -t file-upload-server .
```

2. Run the container:
```bash
docker run -p 7777:7777 \
  -e CLIENT_KEY=your-secret-key \
  -v $(pwd)/tmp:/app/tmp \
  file-upload-server
```

## API Endpoints

### POST /upload
Upload a file and receive a download code.

**Authentication:**
- Required: `X-Client-Key` header with your API key

**Form Fields:**
- `file`: File to upload (required)
- `max_downloads`: Maximum download count (optional, default: 1)
- `expiry_hours`: Hours until expiry (optional, default: 24)

**Response:**
```json
{
  "code": "ABC123"
}
```

**Error Responses:**
- 401: Invalid or missing client key
- 400: Missing file or invalid request
```json
{
  "error": "Error message here"
}
```

### GET /download/{code}
Download a file using a 6-character code.

**Responses:**
- 200: File download starts
- 404: File not found with specific error pages for:
  - Invalid code
  - Expired file
  - Download limit reached
  - File no longer exists

### DELETE /delete/{code}
Delete a file using its code.

**Responses:**
- 200: File deleted successfully
- 404: File not found or expired

## Security Features
- **API Authentication**: Client key required for file uploads
- **Secure Downloads**: 6-digit alphanumeric codes
- **Auto Cleanup**: Files are automatically deleted after:
  - Reaching download limit
  - Exceeding expiry time
  - Server restart (temporary storage)
- **Upload Security**:
  - Secure filename handling
  - No file execution permissions
  - File size limits

## Configuration
All configuration is handled through environment variables:

### Required Settings
- `CLIENT_KEY`: API key for file uploads (required for production)

### Optional Settings
- `UPLOAD_FOLDER`: Upload directory path (default: tmp/uploads)
- `MAX_CONTENT_LENGTH`: Maximum file size (default: 16MB)
- `DEBUG`: Enable debug mode (default: False)

### Environment File
The application supports `.env` file for configuration:
```env
CLIENT_KEY=your-secret-key-here
UPLOAD_FOLDER=tmp/uploads
DEBUG=False
MAX_CONTENT_LENGTH=16777216
```

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Security Best Practices
- Always change the default client key
- Use HTTPS in production
- Regularly monitor disk usage
- Set appropriate file size limits
- Keep dependencies updated
