# Simple File Upload Server

A lightweight Flask-based file upload and download server with a modern UI. Perfect for temporary file sharing and mobile app log uploads.

The Android mobile app for this server can be found at: https://github.com/mattintech/simplefileupload-android

## Features
- Clean, modern UI for file downloads
- Secure API authentication for uploads
- Mobile-friendly upload endpoint
- Chunked upload support for large files
- Specifically designed for the simplefileupload-android app
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

4. Set environment variables (optional):
```bash
export CLIENT_KEY=your-secret-key  # If not set, defaults to default-secret-key
```

5. Run the server:
```bash
python src/app.py
```

### Docker Deployment
1. Build the image:
```bash
docker build -t simplefileupload-server .
```

2. Generate SSL Certificate (Required for Mobile App):
The mobile app requires SSL connections, so you'll need to generate a self-signed certificate or use your own certificate. To create a self-signed certificate:
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

3. Run the container:

Without SSL (Not compatible with mobile app):
```bash
docker run -p 7777:7777 simplefileupload-server
```

With SSL (Required for mobile app):
```bash
docker run -p 7777:7777 \
  -v $(pwd)/cert.pem:/app/cert.pem \
  -v $(pwd)/key.pem:/app/key.pem \
  simplefileupload-server
```

You can combine the SSL certificates with other options like CLIENT_KEY and upload folder:
```bash
docker run -p 7777:7777 \
  -e CLIENT_KEY=your-secret-key \
  -v $(pwd)/cert.pem:/app/cert.pem \
  -v $(pwd)/key.pem:/app/key.pem \
  -v $(pwd)/tmp:/app/tmp \
  simplefileupload-server
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

**Example using curl:**
```bash
# Basic upload with default settings
curl -X POST http://localhost:7777/upload \
  -H "X-Client-Key: your-secret-key" \
  -F "file=@/path/to/your/file.txt"

# Upload with custom download limit and expiry time
curl -X POST http://localhost:7777/upload \
  -H "X-Client-Key: your-secret-key" \
  -F "file=@/path/to/your/file.txt" \
  -F "max_downloads=5" \
  -F "expiry_hours=48"

# Upload with SSL (for mobile app compatibility)
curl -X POST https://localhost:7777/upload \
  -H "X-Client-Key: your-secret-key" \
  -F "file=@/path/to/your/file.txt" \
  --cacert cert.pem
```

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

### POST /upload/start
Start a chunked upload session for large files.

**Authentication:**
- Required: `X-Client-Key` header with your API key

**Form Fields:**
- `filename`: Name of the file being uploaded (required)
- `total_chunks`: Total number of chunks to expect (required)
- `max_downloads`: Maximum download count (optional, default: 1)
- `expiry_hours`: Hours until expiry (optional, default: 24)

**Example using curl:**
```bash
# Start a chunked upload session
curl -X POST http://localhost:7777/upload/start \
  -H "X-Client-Key: your-secret-key" \
  -F "filename=largefile.zip" \
  -F "total_chunks=10" \
  -F "max_downloads=5" \
  -F "expiry_hours=48"
```

**Response:**
```json
{
  "upload_id": "abC123dEf456gHij"
}
```

### POST /upload/chunk
Upload a single chunk of a file.

**Authentication:**
- Required: `X-Client-Key` header with your API key

**Form Fields:**
- `upload_id`: Upload session ID from /upload/start (required)
- `chunk_index`: Index of this chunk, starting from 0 (required)
- `chunk`: The file chunk data (required)

**Example using curl:**
```bash
# Upload chunk 0
curl -X POST http://localhost:7777/upload/chunk \
  -H "X-Client-Key: your-secret-key" \
  -F "upload_id=abC123dEf456gHij" \
  -F "chunk_index=0" \
  -F "chunk=@chunk_0.bin"
```

**Response:**
```json
{
  "success": true,
  "received_chunks": 5,
  "total_chunks": 10
}
```

### POST /upload/complete
Complete a chunked upload session.

**Authentication:**
- Required: `X-Client-Key` header with your API key

**Form Fields:**
- `upload_id`: Upload session ID from /upload/start (required)

**Example using curl:**
```bash
# Complete the chunked upload
curl -X POST http://localhost:7777/upload/complete \
  -H "X-Client-Key: your-secret-key" \
  -F "upload_id=abC123dEf456gHij"
```

**Response:**
```json
{
  "code": "ABC123"
}
```

**Error Responses for Chunked Upload Endpoints:**
- 401: Invalid or missing client key
- 400: Missing required parameters or invalid request
- 404: Invalid upload session ID
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
None - all settings have defaults for easy testing

### Optional Settings
- `CLIENT_KEY`: API key for file uploads (default: default-secret-key)
- `UPLOAD_FOLDER`: Upload directory path (default: tmp/uploads)
- `MAX_CONTENT_LENGTH`: Maximum file size (default: 16MB)
- `DEBUG`: Enable debug mode (default: False)

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Security Best Practices
- Set a strong CLIENT_KEY in production
- Use HTTPS in production
- Regularly monitor disk usage
- Set appropriate file size limits
- Keep dependencies updated
