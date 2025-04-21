from flask import Flask, request, jsonify
from ytmusicapi import YTMusic
import requests
import random
import os
from functools import wraps
from cachetools import TTLCache, cached
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio
from datetime import datetime, timezone

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

app = Flask(__name__)

# Initialize caches with appropriate TTLs
song_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour for song data
artist_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour for artist data
search_cache = TTLCache(maxsize=100, ttl=1800)  # 30 minutes for search results
streams_cache = TTLCache(maxsize=100, ttl=300)  # 5 minutes for streams
playlist_cache = TTLCache(maxsize=50, ttl=1800)  # 30 minutes for playlists
lyrics_cache = TTLCache(maxsize=50, ttl=7200)  # 2 hours for lyrics
mood_cache = TTLCache(maxsize=20, ttl=86400)  # 24 hours for mood categories

# Initialize YTMusic client
try:
    if os.path.exists('oauth.json'):
        ytmusic = YTMusic('oauth.json')
    else:
        ytmusic = YTMusic()
except Exception as e:
    ytmusic = YTMusic()
    print(f"Using unauthenticated client due to: {str(e)}")

# Piped API instances
PIPED_INSTANCES = [
    'https://pipedapi.nosebs.ru',
    'https://piped-api.privacy.com.de',
    'https://pipedapi.adminforge.de',
    'https://api.piped.yt',
]

# Thread pool executor for blocking operations
executor = ThreadPoolExecutor(max_workers=4)

def cache_key(*args, **kwargs):
    """Generate a cache key from function arguments"""
    return str(args) + str(sorted(kwargs.items()))

def cache_with_ttl(cache):
    """Decorator for caching with TTL"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = cache_key(*args, **kwargs)
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            cache[key] = result
            return result
        return wrapper
    return decorator

def run_async(coro):
    """Helper function to run async code in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

async def get_streams_data_async(video_id, instance):
    """Asynchronous function to fetch streams data"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{instance}/streams/{video_id}", timeout=5) as response:
                if response.status == 200:
                    return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass
    return None

async def fetch_streams_from_instances(video_id):
    """Async function to fetch streams from all instances"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for instance in PIPED_INSTANCES:
            tasks.append(get_streams_data_async(video_id, instance))
        return await asyncio.gather(*tasks)

async def check_instance_health(instance):
    """Async function to check instance health"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{instance}/healthcheck", timeout=5) as response:
                return response.status == 200
        except:
            return False

async def get_working_instance_async():
    """Asynchronously find a working Piped instance"""
    tasks = [check_instance_health(instance) for instance in PIPED_INSTANCES]
    results = await asyncio.gather(*tasks)
    working_instances = [instance for instance, is_working in zip(PIPED_INSTANCES, results) if is_working]
    return random.choice(working_instances) if working_instances else random.choice(PIPED_INSTANCES)

# Basic health check endpoint
@app.route('/')
def home():
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    return jsonify({
        "status": "ok",
        "message": "YouTube Music API is running",
        "timestamp": current_time,
        "version": "2.0.0"
    })

# Search endpoint with caching
@app.route('/api/search')
@cache_with_ttl(search_cache)
def search():
    query = request.args.get('query', '')
    filter_param = request.args.get('filter', None)
    try:
        limit = int(request.args.get('limit', 20))
        results = executor.submit(ytmusic.search, query, filter=filter_param, limit=limit).result()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Search suggestions endpoint
@app.route('/api/search/suggestions')
def get_search_suggestions():
    query = request.args.get('query', '')
    try:
        results = executor.submit(ytmusic.get_search_suggestions, query).result()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Song information endpoint with caching
@app.route('/api/song/<video_id>')
@cache_with_ttl(song_cache)
def get_song_info(video_id):
    try:
        result = executor.submit(ytmusic.get_song, video_id).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "message": "Invalid video ID"}), 400

# Artist information endpoint with caching
@app.route('/api/artist/<channel_id>')
@cache_with_ttl(artist_cache)
def get_artist_info(channel_id):
    try:
        result = executor.submit(ytmusic.get_artist, channel_id).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "message": "Invalid channel ID"}), 400

# Playlist information endpoint with caching
@app.route('/api/playlist/<playlist_id>')
@cache_with_ttl(playlist_cache)
def get_playlist_info(playlist_id):
    try:
        limit = int(request.args.get('limit', 100))
        result = executor.submit(ytmusic.get_playlist, playlist_id, limit).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "message": "Invalid playlist ID"}), 400

# Album information endpoint with caching
@app.route('/api/album/<browse_id>')
@cache_with_ttl(song_cache)
def get_album_info(browse_id):
    try:
        result = executor.submit(ytmusic.get_album, browse_id).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "message": "Invalid browse ID"}), 400

# Lyrics endpoint with caching
@app.route('/api/lyrics/<browse_id>')
@cache_with_ttl(lyrics_cache)
def get_lyrics(browse_id):
    try:
        result = executor.submit(ytmusic.get_lyrics, browse_id).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "message": "Lyrics not found"}), 400

# Watch playlist endpoint
@app.route('/api/watch/playlist')
def get_watch_playlist():
    video_id = request.args.get('video_id')
    playlist_id = request.args.get('playlist_id')
    
    try:
        limit = int(request.args.get('limit', 25))
        radio = request.args.get('radio', 'false').lower() == 'true'
        shuffle = request.args.get('shuffle', 'false').lower() == 'true'
        
        if not (video_id or playlist_id):
            return jsonify({"error": "video_id or playlist_id required"}), 400
        
        kwargs = {
            "limit": limit,
            "radio": radio,
            "shuffle": shuffle
        }
        
        if video_id:
            kwargs["videoId"] = video_id
        if playlist_id:
            kwargs["playlistId"] = playlist_id
            
        result = executor.submit(ytmusic.get_watch_playlist, **kwargs).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Related songs endpoint with caching
@app.route('/api/related/<browse_id>')
@cache_with_ttl(song_cache)
def get_related_songs(browse_id):
    try:
        result = executor.submit(ytmusic.get_song_related, browse_id).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "message": "Invalid browse ID"}), 400

# Mood categories endpoint with caching
@app.route('/api/moods')
@cache_with_ttl(mood_cache)
def get_mood_categories():
    try:
        result = executor.submit(ytmusic.get_mood_categories).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Mood playlists endpoint with caching
@app.route('/api/moods/playlists/<params>')
@cache_with_ttl(mood_cache)
def get_mood_playlists(params):
    try:
        result = executor.submit(ytmusic.get_mood_playlists, params).result()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Audio stream endpoint with caching
@app.route('/api/audio')
@cache_with_ttl(streams_cache)
def get_audio_url():
    video_id = request.args.get('videoId')
    if not video_id:
        return jsonify({'error': 'Missing videoId parameter'}), 400
    
    try:
        results = run_async(fetch_streams_from_instances(video_id))
        
        for result, instance in zip(results, PIPED_INSTANCES):
            if result and 'audioStreams' in result and result['audioStreams']:
                return jsonify({
                    'audioUrl': result['audioStreams'][0]['url'],
                    'mimeType': result['audioStreams'][0]['mimeType'],
                    'quality': result['audioStreams'][0]['quality'],
                    'instance': instance
                })
        
        return jsonify({'error': 'Failed to fetch audio URL'}), 503
    except Exception as e:
        return jsonify({'error': f'Error fetching audio URL: {str(e)}'}), 500

# Stream URLs endpoint with caching
@app.route('/api/streams')
@cache_with_ttl(streams_cache)
def get_stream_urls():
    video_id = request.args.get('videoId')
    if not video_id:
        return jsonify({'error': 'Missing videoId parameter'}), 400
    
    try:
        results = run_async(fetch_streams_from_instances(video_id))
        
        for result, instance in zip(results, PIPED_INSTANCES):
            if result:
                return jsonify({
                    'videoStreams': result.get('videoStreams', []),
                    'audioStreams': result.get('audioStreams', []),
                    'instance': instance,
                    'title': result.get('title', ''),
                    'description': result.get('description', ''),
                    'uploader': result.get('uploader', ''),
                    'uploaderUrl': result.get('uploaderUrl', '')
                })
        
        return jsonify({'error': 'Failed to fetch streams'}), 503
    except Exception as e:
        return jsonify({'error': f'Error fetching streams: {str(e)}'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
