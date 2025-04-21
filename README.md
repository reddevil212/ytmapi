# YouTube Music API Server

A Flask-based REST API server that interfaces with YouTube Music, providing cached access to music data, streams, and related information.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup](#setup)
- [Cache Configuration](#cache-configuration)
- [API Endpoints](#api-endpoints)
  - [Health Check](#health-check)
  - [Search](#search)
  - [Song Information](#song-information)
  - [Artist Information](#artist-information)
  - [Playlist Information](#playlist-information)
  - [Audio and Streams](#audio-and-streams)
  - [Other Endpoints](#other-endpoints)

## Features

- Cached responses for improved performance
- Asynchronous stream fetching
- Multiple Piped API instance support
- TTL-based caching for different types of data
- Error handling and rate limiting
- Thread pool execution for blocking operations

## Requirements

```plaintext
flask
ytmusicapi
requests
cachetools
aiohttp
nest_asyncio
```

## Setup

1. Install dependencies:
```bash
pip install flask ytmusicapi requests cachetools aiohttp nest_asyncio
```

2. (Optional) Set up YouTube Music authentication:
   - Create an `oauth.json` file in the root directory
   - If not provided, the server will use an unauthenticated client

3. Run the server:
```bash
python app.py
```

The server will start on `http://0.0.0.0:5000`

## Cache Configuration

The server implements various TTL (Time To Live) caches for different types of data:

| Cache Type | TTL | Max Size | Description |
|------------|-----|----------|-------------|
| Song Cache | 1 hour | 100 | Song details and related data |
| Artist Cache | 1 hour | 100 | Artist information |
| Search Cache | 30 minutes | 100 | Search results |
| Streams Cache | 5 minutes | 100 | Audio/video streams |
| Playlist Cache | 30 minutes | 50 | Playlist information |
| Lyrics Cache | 2 hours | 50 | Song lyrics |
| Mood Cache | 24 hours | 20 | Mood categories |

## API Endpoints

### Health Check

```http
GET /
```

Returns basic server status and version information.

### Search

#### Search for Content
```http
GET /api/search
```

Query Parameters:
- `query` (required): Search term
- `filter` (optional): Filter type
- `limit` (optional, default: 20): Maximum number of results

#### Search Suggestions
```http
GET /api/search/suggestions
```

Query Parameters:
- `query` (required): Search term

### Song Information

#### Get Song Details
```http
GET /api/song/<video_id>
```

#### Get Related Songs
```http
GET /api/related/<browse_id>
```

### Artist Information

```http
GET /api/artist/<channel_id>
```

Returns detailed information about an artist.

### Playlist Information

```http
GET /api/playlist/<playlist_id>
```

Query Parameters:
- `limit` (optional, default: 100): Maximum number of tracks

### Audio and Streams

#### Get Audio URL
```http
GET /api/audio
```

Query Parameters:
- `videoId` (required): YouTube video ID

#### Get Stream URLs
```http
GET /api/streams
```

Query Parameters:
- `videoId` (required): YouTube video ID

### Other Endpoints

#### Album Information
```http
GET /api/album/<browse_id>
```

#### Lyrics
```http
GET /api/lyrics/<browse_id>
```

#### Watch Playlist
```http
GET /api/watch/playlist
```

Query Parameters:
- `video_id` (optional): YouTube video ID
- `playlist_id` (optional): YouTube playlist ID
- `limit` (optional, default: 25): Maximum number of items
- `radio` (optional, default: false): Radio mode
- `shuffle` (optional, default: false): Shuffle mode

#### Mood Categories
```http
GET /api/moods
```

#### Mood Playlists
```http
GET /api/moods/playlists/<params>
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- 200: Successful request
- 400: Bad request (missing parameters or invalid input)
- 404: Resource not found
- 500: Internal server error
- 503: Service unavailable (stream fetching failed)

Error responses are in JSON format:
```json
{
    "error": "Error message description"
}
```

## Notes

- The server uses multiple Piped API instances for redundancy
- Asynchronous operations are used for stream fetching
- Nested event loops are supported via nest_asyncio
- All responses are in JSON format
- The server includes automatic caching for improved performance



Made with 🩷 by reddevil212
