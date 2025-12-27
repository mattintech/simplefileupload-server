# API Documentation

## Overview
The Simple File Upload Server provides a RESTful API for file uploads and downloads, with special support for chunked uploads of large files. All upload endpoints require API key authentication.

## Authentication
All upload endpoints require the `X-Client-Key` header with a valid API key.

Example:
```http
X-Client-Key: your-secret-key
```

## Endpoints

### File Upload

#### POST /upload
Upload a single file in one request.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Authentication: Required

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| file | File | Yes | The file to upload |
| max_downloads | Integer | No | Maximum number of downloads (default: 1) |
| expiry_hours | Integer | No | Hours until file expires (default: 24) |

**Response:**
```json
{
    "code": "ABC123"
}
```

### Chunked Upload

#### POST /upload/start
Initialize a chunked upload session.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Authentication: Required

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| filename | String | Yes | Name of the file being uploaded |
| total_chunks | Integer | Yes | Total number of chunks to expect |
| max_downloads | Integer | No | Maximum number of downloads (default: 1) |
| expiry_hours | Integer | No | Hours until file expires (default: 24) |

**Response:**
```json
{
    "upload_id": "abC123dEf456gHij"
}
```

#### POST /upload/chunk
Upload a single chunk of a file.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Authentication: Required

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| upload_id | String | Yes | Upload session ID from /upload/start |
| chunk_index | Integer | Yes | Index of this chunk (0-based) |
| chunk | File | Yes | The chunk data |

**Response:**
```json
{
    "success": true,
    "received_chunks": 5,
    "total_chunks": 10,
    "chunk_index": 4
}
```

#### POST /upload/verify
Verify the status of uploaded chunks.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Authentication: Required

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| upload_id | String | Yes | Upload session ID |

**Response:**
```json
{
    "total_chunks": 10,
    "received_chunks": 5,
    "missing_chunks": [5,6,7,8,9]
}
```

#### POST /upload/complete
Complete a chunked upload session.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Authentication: Required

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| upload_id | String | Yes | Upload session ID |

**Response:**
```json
{
    "code": "ABC123"
}
```

### File Download

#### GET /download/{code}
Download a file using its 6-character code.

**Request:**
- Method: `GET`
- Authentication: Not required

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| code | String | Yes | 6-character download code |

**Response:**
- Success: File download begins
- Error: HTML error page with user-friendly message

### File Management

#### DELETE /delete/{code}
Delete a file using its code.

**Request:**
- Method: `DELETE`
- Authentication: Not required

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| code | String | Yes | 6-character download code |

**Response:**
```json
{
    "message": "File deleted successfully"
}
```

## Error Responses

### Common Error Format
```json
{
    "error": "Error message description"
}
```

### HTTP Status Codes
- 200: Success
- 400: Bad Request (missing parameters, invalid format)
- 401: Unauthorized (invalid or missing API key)
- 404: Not Found (invalid code, expired file)
- 500: Server Error

## Rate Limits
Currently not implemented. See future enhancements in TASK.md.