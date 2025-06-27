from fastmcp import FastMCP
from instagrapi import Client
from instagrapi.types import Usertag, UserShort
import argparse
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import logging
from pathlib import Path
import re
import json
import time
from datetime import datetime
import uuid
import subprocess
import tempfile
import requests
import random

# Load environment variables from .env file
load_dotenv()

# Set up logger to stderr for debugging
import sys
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set specific module logging levels to reduce noise
logging.getLogger('instagrapi').setLevel(logging.WARNING)
logging.getLogger('mcp.server.lowlevel.server').setLevel(logging.WARNING)
logging.getLogger('FastMCP.fastmcp.server.server').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)
logging.getLogger('account_pool').setLevel(logging.INFO)

# Set up media directory paths
BASE_DIR = Path(__file__).parent.parent  # ghost_mcp directory
MEDIA_DIR = BASE_DIR / "media"

# Import our account pool
from account_pool import AccountPool

# Import video processors - chunk creation and personalization
try:
    from chunk_processor import ChunkProcessor
    from personalization_processor import PersonalizationProcessor
    chunk_processor = ChunkProcessor()
    personalization_processor = PersonalizationProcessor()
    logger.info("Two-stage video processors loaded successfully")
    video_processors_available = True
except ImportError as e:
    logger.error(f"Failed to import video processors: {e}")
    chunk_processor = None
    personalization_processor = None
    video_processors_available = False

INSTRUCTIONS = """
This server provides Instagram automation capabilities including:
- Sending direct messages (text, photo)
- Uploading videos/reels with user tags
- Sharing posts to DMs
- Managing conversations and user data
- Multi-account support with automatic rotation
"""

# Initialize account pool (will be configured in main)
account_pool = None

# Keep single client for backwards compatibility
client = None

mcp = FastMCP(
   name="Instagram DMs",
   instructions=INSTRUCTIONS
)

def get_client(preferred_account: Optional[str] = None) -> Client:
    """Get a client instance, using account pool if available"""
    global client, account_pool
    
    # If account pool is available, use it
    if account_pool:
        selected_client = account_pool.get_client(preferred_account)
        if selected_client:
            return selected_client
        else:
            logger.error("Account pool returned None client")
    
    # Fall back to single client
    if client:
        return client
    
    logger.error(f"No Instagram client available. Account pool: {account_pool is not None}, Single client: {client is not None}")
    raise Exception("No Instagram client available")

# Helper functions for internal use (not exposed as MCP tools)
def _get_user_info_internal(username: str, client: Client) -> Dict[str, Any]:
    """Internal helper for getting user info without going through MCP tool.
    
    Args:
        username: Instagram username to get information about.
        client: Instagram client instance to use.
    Returns:
        A dictionary with success status and user information.
    """
    if not username:
        return {"success": False, "message": "Username must be provided."}
    
    try:
        user = client.user_info_by_username(username)
        if user:
            user_data = {
                "user_id": str(user.pk),
                "username": user.username,
                "full_name": user.full_name,
                "biography": user.biography,
                "follower_count": user.follower_count,
                "following_count": user.following_count,
                "media_count": user.media_count,
                "is_private": user.is_private,
                "is_verified": user.is_verified,
                "profile_pic_url": str(user.profile_pic_url) if user.profile_pic_url else None,
                "external_url": str(user.external_url) if user.external_url else None,
                "category": user.category,
            }
            return {"success": True, "user_info": user_data}
        else:
            return {"success": False, "message": f"User '{username}' not found."}
    except Exception as e:
        return {"success": False, "message": str(e)}

def _sync_user_to_web_data(url_key: str, username: str, user_data: Dict[str, Any]) -> None:
    """Sync user data to web app's users_data.json"""
    try:
        # Path to web app's users_data.json
        web_data_file = Path(__file__).parent.parent.parent / "users_data.json"
        
        # Load existing data
        users_web_data = {}
        if web_data_file.exists():
            with open(web_data_file, 'r') as f:
                users_web_data = json.load(f)
        
        # Update with new user data - include all Bright Data fields
        users_web_data[url_key] = {
            "username": username,
            "user_id": user_data.get("user_id"),
            "followers": user_data.get("followers", 0),
            "following": user_data.get("following", 0),
            "posts_count": user_data.get("posts_count", 0),
            "avg_engagement": user_data.get("avg_engagement", 0.0),
            "video": user_data.get("video", "default.mp4"),
            "video_sent": user_data.get("video", "default.mp4"),  # For compatibility
            "campaign_id": user_data.get("campaign_id"),
            "sent_at": datetime.utcnow().isoformat() + "Z",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "clicked": False
        }
        
        # Save updated data
        with open(web_data_file, 'w') as f:
            json.dump(users_web_data, f, indent=2)
            
    except Exception as e:
        print(f"Error syncing user data to web: {e}")

def _send_ghost_video_workflow(username: str, video_path: str, 
                              personalized_url: str, message_template: str,
                              client: Client, preferred_account: Optional[str] = None,
                              chunk_id: Optional[str] = None) -> Dict[str, Any]:
    """Internal helper for the ghost video workflow.
    
    This implements the 3-step process:
    1. Add username overlay to video with modular video processor
    2. Upload video as reel with user tag
    3. Share the reel to user's DM
    4. Send follow-up message with personalized URL
    
    Args:
        username: Target Instagram username
        video_path: Path to the video file (can be base clip path)
        personalized_url: Personalized vhs-ghost.com URL
        message_template: Message template with {username} placeholder
        client: Instagram client instance to use
        preferred_account: Optional preferred account for multi-account mode
        chunk_id: Optional specific chunk ID to use instead of random selection
    
    Returns:
        Dictionary with success status, post URL, and error messages
    """
    global account_pool
    
    try:
        # Step 1: Create personalized video
        temp_video_path = None
        cleanup_needed = False
        
        try:
            # Check if video_path is already personalized
            if video_path and video_path != "None" and video_path != "" and ("campaign_videos" in video_path or "campaign_temp" in video_path) and os.path.exists(video_path):
                # Already personalized, use as-is
                temp_video_path = video_path
                logger.info(f"Using pre-personalized video: {video_path}")
            else:
                # Use two-stage processor if available
                if video_processors_available and personalization_processor:
                    try:
                        logger.info(f"Creating personalized video for @{username} using two-stage processor")
                        
                        # Get chunk - specific or random
                        if chunk_id:
                            chunk_path = personalization_processor.get_chunk_by_id(chunk_id)
                            if not chunk_path:
                                logger.error(f"Specified chunk {chunk_id} not found, falling back to legacy method")
                                temp_video_path = None
                            else:
                                logger.info(f"Using specific chunk: {chunk_id}")
                        else:
                            chunk_path = personalization_processor.get_random_chunk()
                            if not chunk_path:
                                logger.error("No chunks available, falling back to legacy method")
                                temp_video_path = None
                        
                        if chunk_path:
                            # Extract campaign_id from context
                            campaign_id = video_path if video_path and video_path != "" else "default"
                            
                            # Personalize the chunk
                            result = personalization_processor.personalize_chunk(
                                username=username,
                                chunk_path=chunk_path,
                                campaign_id=campaign_id
                            )
                            
                            if result["success"]:
                                temp_video_path = result["path"]
                                cleanup_needed = False  # Keep personalized videos
                                logger.info(f"Created personalized video: {temp_video_path} from chunk: {result['chunk_used']}")
                            else:
                                logger.error(f"Personalization failed: {result.get('message')}")
                                temp_video_path = None
                    except Exception as e:
                        logger.error(f"Two-stage processor failed: {e}, falling back to legacy FFmpeg")
                        # Fall back to legacy method
                        temp_video_path = None
                
                # Legacy fallback - use FFmpeg directly
                if not temp_video_path:
                    # Need a source video for legacy fallback
                    source_video_path = None
                    
                    # Try to get a chunk first
                    if chunk_processor:
                        chunks = chunk_processor.get_available_chunks()
                        if chunks:
                            random_chunk = random.choice(chunks)
                            source_video_path = random_chunk.get("path")
                            logger.info(f"Using random chunk for legacy fallback: {source_video_path}")
                    
                    # If no chunks, try raw videos
                    if not source_video_path:
                        raw_dir = MEDIA_DIR / "raw"
                        if raw_dir.exists():
                            videos = list(raw_dir.glob("*.mp4"))
                            if videos:
                                source_video_path = str(random.choice(videos))
                                logger.info(f"Using random raw video for legacy fallback: {source_video_path}")
                    
                    if not source_video_path:
                        logger.error("No source videos available for legacy fallback")
                        return {"success": False, "message": "No video sources available. Please create chunks or add raw videos."}
                    
                    # Create temp file for personalized video
                    temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                    temp_video_path = temp_video.name
                    temp_video.close()
                    cleanup_needed = True
                    
                    # Build FFmpeg command for flashing text overlay (0-8 seconds)
                    # Note: This is simplified for legacy fallback
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', source_video_path,
                        '-vf', (
                            # Flash between username and message (simplified)
                            # Username (0-2, 4-6 seconds)
                            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:"
                            f"text='@{username}':fontcolor=#00ffff@0.7:fontsize=48:"
                            f"x=(w-text_w)/2-2:y=h/2-2:"
                            f"enable='between(t,0,2)+between(t,4,6)',"
                            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:"
                            f"text='@{username}':fontcolor=#ff00ff@0.7:fontsize=48:"
                            f"x=(w-text_w)/2+2:y=h/2+2:"
                            f"enable='between(t,0,2)+between(t,4,6)',"
                            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:"
                            f"text='@{username}':fontcolor=#00ff00:fontsize=48:"
                            f"x=(w-text_w)/2:y=h/2:"
                            f"enable='between(t,0,2)+between(t,4,6)',"
                            # Message (2-4, 6-8 seconds)
                            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:"
                            f"text='YOUVE BEEN CHOSEN':fontcolor=#00ffff@0.7:fontsize=48:"
                            f"x=(w-text_w)/2-2:y=h/2-2:"
                            f"enable='between(t,2,4)+between(t,6,8)',"
                            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:"
                            f"text='YOUVE BEEN CHOSEN':fontcolor=#ff00ff@0.7:fontsize=48:"
                            f"x=(w-text_w)/2+2:y=h/2+2:"
                            f"enable='between(t,2,4)+between(t,6,8)',"
                            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:"
                            f"text='YOUVE BEEN CHOSEN':fontcolor=#00ff00:fontsize=48:"
                            f"x=(w-text_w)/2:y=h/2:"
                            f"enable='between(t,2,4)+between(t,6,8)'"
                        ),
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-c:a', 'copy',
                        temp_video_path
                    ]
                    
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                        if result.returncode != 0:
                            logger.error(f"FFmpeg error: {result.stderr}")
                            return {"success": False, "message": f"Video personalization failed: {result.stderr}"}
                    except subprocess.TimeoutExpired:
                        logger.error(f"FFmpeg timeout after 60s personalizing video")
                        return {"success": False, "message": "FFmpeg timeout during video personalization"}
            
            # Step 2: Upload video as reel with user tag
            try:
                tagged_user = client.user_info_by_username(username)
                if not tagged_user:
                    return {"success": False, "message": f"User '{username}' not found"}
            except Exception as e:
                # Session might be invalid, try to refresh
                logger.warning(f"Failed to get user info for {username}, attempting session refresh: {e}")
                
                # Try to re-login using account pool
                if account_pool:
                    # Find which account this client belongs to
                    account_username = None
                    for acc_name, acc_data in account_pool.clients.items():
                        if acc_data.get("client") == client:
                            account_username = acc_name
                            break
                    
                    if account_username and account_pool.relogin_account(account_username):
                        # Re-login successful, try again
                        try:
                            tagged_user = client.user_info_by_username(username)
                            if not tagged_user:
                                return {"success": False, "message": f"User '{username}' not found"}
                        except Exception as retry_error:
                            logger.error(f"Failed after re-login: {retry_error}")
                            return {"success": False, "message": f"Failed to get user info after re-login: {str(retry_error)}"}
                    else:
                        logger.error(f"Session refresh failed for account")
                        return {"success": False, "message": f"Session expired and refresh failed: {str(e)}"}
                else:
                    logger.error("No account pool available for session refresh")
                    return {"success": False, "message": f"Session expired and no account pool available: {str(e)}"}
            
            # Create UserShort object for tagging
            user_short = UserShort(
                pk=tagged_user.pk,
                username=tagged_user.username,
                full_name=tagged_user.full_name,
                profile_pic_url=tagged_user.profile_pic_url
            )
            
            # Create usertag (center position)
            usertags = [Usertag(user=user_short, x=0.5, y=0.5)]
            
            # Upload as reel
            caption = f"The signal found @{username} 📼 #vhsghost"
            try:
                media = client.clip_upload(
                    Path(temp_video_path),
                    caption=caption,
                    usertags=usertags
                )
                
                if not media:
                    return {"success": False, "message": "Failed to upload video"}
            except Exception as e:
                logger.error(f"Failed to upload video: {e}")
                # Try one more time after a short delay
                try:
                    time.sleep(5)
                    media = client.clip_upload(
                        Path(temp_video_path),
                        caption=caption,
                        usertags=usertags
                    )
                    if not media:
                        return {"success": False, "message": "Failed to upload video after retry"}
                except Exception as retry_error:
                    return {"success": False, "message": f"Upload failed: {str(e)}"}
            
            post_url = f"https://instagram.com/p/{media.code}/"
            
            # Track action if using account pool
            if account_pool and hasattr(client, 'username'):
                account_pool.track_action(client.username, "upload")
            
            # Step 3: Share the reel to user's DM
            media_pk = media.pk
            user_id = tagged_user.pk
            
            try:
                share_result = client.direct_media_share(media_pk, [user_id])
                
                if account_pool and hasattr(client, 'username'):
                    account_pool.track_action(client.username, "dm")
                
                # Step 4: Send follow-up message
                message = message_template.format(username=username)
                client.direct_send(message, [user_id])
            except Exception as e:
                logger.error(f"Failed to send DM: {e}")
                # Try with a small delay
                try:
                    time.sleep(3)
                    share_result = client.direct_media_share(media_pk, [user_id])
                    time.sleep(2)
                    message = message_template.format(username=username)
                    client.direct_send(message, [user_id])
                except Exception as retry_error:
                    return {"success": False, "message": f"DM sending failed: {str(e)}", "post_url": post_url}
            
            if account_pool and hasattr(client, 'username'):
                account_pool.track_action(client.username, "dm")
            
            return {
                "success": True,
                "post_url": post_url,
                "media_id": str(media.pk),
                "message": "Ghost video sent successfully"
            }
            
        finally:
            # Clean up temp file if needed
            if cleanup_needed and temp_video_path and os.path.exists(temp_video_path):
                try:
                    os.unlink(temp_video_path)
                    logger.info(f"Cleaned up temporary video: {temp_video_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp video: {e}")
                
    except Exception as e:
        logger.error(f"Failed to send ghost video: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def send_message(username: str, message: str, preferred_account: Optional[str] = None) -> Dict[str, Any]:
    """Send an Instagram direct message to a user by username.

    Args:
        username: Instagram username of the recipient.
        message: The message text to send.
        preferred_account: Optional specific account to use for sending.
    Returns:
        A dictionary with success status and a status message.
    """
    if not username or not message:
        return {"success": False, "message": "Username and message must be provided."}
    try:
        client = get_client(preferred_account)
        user_id = client.user_id_from_username(username)
        if not user_id:
            return {"success": False, "message": f"User '{username}' not found."}
        dm = client.direct_send(message, [user_id])
        
        # Track action if using account pool
        if account_pool and hasattr(client, 'username'):
            account_pool.track_action(client.username, "dm")
        
        if dm:
            return {"success": True, "message": "Message sent to user.", "direct_message_id": getattr(dm, 'id', None)}
        else:
            return {"success": False, "message": "Failed to send message."}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def get_user_id_from_username(username: str) -> Dict[str, Any]:
    """Get the Instagram user ID for a given username.

    Args:
        username: Instagram username.
    Returns:
        A dictionary with success status and the user ID or error message.
    """
    if not username:
        return {"success": False, "message": "Username must be provided."}
    try:
        client = get_client()
        user_id = client.user_id_from_username(username)
        if user_id:
            return {"success": True, "user_id": user_id}
        else:
            return {"success": False, "message": f"User '{username}' not found."}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def get_user_info(username: str) -> Dict[str, Any]:
    """Get detailed information about an Instagram user.

    Args:
        username: Instagram username to get information about.
    Returns:
        A dictionary with success status and user information.
    """
    client = get_client()
    return _get_user_info_internal(username, client)

@mcp.tool()
def get_user_posts(username: str, count: int = 12) -> Dict[str, Any]:
    """Get recent posts from an Instagram user.

    Args:
        username: Instagram username to get posts from.
        count: Maximum number of posts to return (default 12).
    Returns:
        A dictionary with success status and posts list.
    """
    if not username:
        return {"success": False, "message": "Username must be provided."}
    
    try:
        client = get_client()
        user_id = client.user_id_from_username(username)
        if not user_id:
            return {"success": False, "message": f"User '{username}' not found."}
        
        medias = client.user_medias(user_id, amount=count)
        
        media_results = []
        for media in medias:
            media_data = {
                "media_id": str(media.pk),
                "media_type": media.media_type,  # 1=photo, 2=video, 8=album
                "caption": media.caption_text if media.caption_text else "",
                "like_count": media.like_count,
                "comment_count": media.comment_count,
                "taken_at": str(media.taken_at),
                "media_url": str(media.thumbnail_url) if media.thumbnail_url else None,
            }
            
            if media.media_type == 2 and media.video_url:
                media_data["video_url"] = str(media.video_url)
                media_data["video_duration"] = media.video_duration
            
            media_results.append(media_data)
        
        return {"success": True, "posts": media_results, "count": len(media_results)}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def upload_video_post(
    video_path: str, 
    caption: str, 
    tagged_username: str,
    tag_x: float = 0.5,
    tag_y: float = 0.5,
    preferred_account: Optional[str] = None
) -> Dict[str, Any]:
    """Upload a video as an Instagram reel with user tag.
    
    Args:
        video_path: Path to the MP4 video file
        caption: Post caption text (can include @mentions and hashtags)
        tagged_username: Username to tag in the video
        tag_x: X coordinate for tag placement (0-1, default 0.5 for center)
        tag_y: Y coordinate for tag placement (0-1, default 0.5 for center)
        preferred_account: Optional specific account to use for uploading
    
    Returns:
        Dictionary with success status, media_id, post URL, and error message if failed
    """
    if not video_path or not caption or not tagged_username:
        return {"success": False, "message": "video_path, caption, and tagged_username must be provided."}
    
    if not os.path.exists(video_path):
        return {"success": False, "message": f"Video file not found: {video_path}"}
    
    try:
        client = get_client(preferred_account)
        
        # Get user info for tagging
        tagged_user = client.user_info_by_username(tagged_username)
        if not tagged_user:
            return {"success": False, "message": f"User '{tagged_username}' not found"}
        
        # Create UserShort object for tagging
        user_short = UserShort(
            pk=tagged_user.pk,
            username=tagged_user.username,
            full_name=tagged_user.full_name,
            profile_pic_url=tagged_user.profile_pic_url
        )
        
        # Create usertag
        usertags = [Usertag(user=user_short, x=tag_x, y=tag_y)]
        
        # Upload as reel (better for viral content)
        media = client.clip_upload(
            Path(video_path),
            caption=caption,
            usertags=usertags
        )
        
        # Track action if using account pool
        if account_pool and hasattr(client, 'username'):
            account_pool.track_action(client.username, "upload")
        
        return {
            "success": True,
            "media_id": str(media.pk),
            "media_code": media.code,
            "post_url": f"https://instagram.com/p/{media.code}/",
            "message": "Video posted successfully"
        }
    except Exception as e:
        logger.error(f"Failed to upload video: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def share_post_to_dm(
    username: str, 
    post_url: str,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Share an Instagram post to a user's DM with optional message.
    
    Args:
        username: Instagram username to send to
        post_url: URL of the Instagram post to share
        message: Optional text message to include with the share
    
    Returns:
        Dictionary with success status and message
    """
    if not username or not post_url:
        return {"success": False, "message": "username and post_url must be provided."}
    
    try:
        client = get_client()
        # Extract media code from URL
        match = re.search(r'/p/([A-Za-z0-9_-]+)/', post_url)
        if not match:
            # Try reel format
            match = re.search(r'/reel/([A-Za-z0-9_-]+)/', post_url)
        
        if not match:
            return {"success": False, "message": "Invalid Instagram post URL"}
        
        media_code = match.group(1)
        media_pk = client.media_pk_from_code(media_code)
        
        # Get user ID
        user_id = client.user_id_from_username(username)
        if not user_id:
            return {"success": False, "message": f"User '{username}' not found"}
        
        # Share the media
        result = client.direct_media_share(media_pk, [user_id])
        
        # Send follow-up message if provided
        if message and result:
            client.direct_send(message, [user_id])
        
        return {
            "success": True,
            "message": "Post shared successfully",
            "thread_id": str(getattr(result, 'id', None)) if result else None
        }
    except Exception as e:
        logger.error(f"Failed to share post: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def get_account_posts(count: int = 12) -> Dict[str, Any]:
    """Get recent posts from the authenticated account.
    
    Args:
        count: Number of posts to retrieve (default 12, max 50)
    
    Returns:
        Dictionary with list of posts including media_id, code, caption, and URL
    """
    try:
        active_client = get_client()
        user_id = active_client.user_id
        medias = active_client.user_medias(user_id, amount=min(count, 50))
        
        posts = []
        for media in medias:
            posts.append({
                "media_id": str(media.pk),
                "media_code": media.code,
                "caption": media.caption_text or "",
                "post_url": f"https://instagram.com/p/{media.code}/",
                "media_type": media.media_type,  # 1=photo, 2=video, 8=album
                "created_at": str(media.taken_at)
            })
        
        return {"success": True, "posts": posts, "count": len(posts)}
    except Exception as e:
        logger.error(f"Failed to get posts: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def create_campaign(
    name: str,
    user_list: List[str],
    video_folder: str = None,
    message_template: str = "SYSTEM DIAGNOSTIC INITIATED\nACCESS: vhs-ghost.com/{username}\nTIME REMAINING: 72:00:00"
) -> Dict[str, Any]:
    """Initialize a new ghost campaign with target users and videos.
    
    Args:
        name: Campaign name for tracking
        user_list: List of Instagram usernames to target
        video_folder: Path to folder containing processed videos
        message_template: Message template with {username} placeholder
    
    Returns:
        Dictionary with campaign_id and initialization status
    """
    try:
        campaign_id = f"campaign_{uuid.uuid4().hex[:8]}"
        
        # Load existing campaigns
        campaign_file = Path("campaigns.json")
        if campaign_file.exists():
            with open(campaign_file, 'r') as f:
                campaigns_data = json.load(f)
        else:
            campaigns_data = {"campaigns": {}}
        
        # Check for available chunks
        if chunk_processor:
            chunks = chunk_processor.get_available_chunks()
            if len(chunks) < 5:
                logger.warning(f"Only {len(chunks)} chunks available. Recommend creating more with create_video_chunks tool.")
            else:
                logger.info(f"Found {len(chunks)} chunks available for campaign")
        
        # Initialize campaign
        campaign = {
            "name": name,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "active",
            "message_template": message_template,
            "video_folder": video_folder,
            "stats": {
                "total_users": len(user_list),
                "sent": 0,
                "errors": 0,
                "clicks": 0
            },
            "users": {}
        }
        
        # Initialize user entries (videos will be created dynamically)
        for username in user_list:
            campaign["users"][username] = {
                "status": "pending",
                "video": None,  # Will be created dynamically
                "user_id": None,
                "post_url": None,
                "sent_at": None,
                "error": None
            }
        
        # Save campaign
        campaigns_data["campaigns"][campaign_id] = campaign
        with open(campaign_file, 'w') as f:
            json.dump(campaigns_data, f, indent=2)
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "message": f"Campaign created with {len(user_list)} users. Videos will be generated dynamically.",
            "users_count": len(user_list),
            "video_mode": "dynamic"
        }
    except Exception as e:
        logger.error(f"Failed to create campaign: {str(e)}")
        return {"success": False, "message": str(e)}

# Note: send_ghost_video was removed because MCP tools cannot call other MCP tools
# The workflow should be orchestrated by calling the individual tools in sequence:
# 1. create_campaign() - Create campaign with user list
# 2. create_video_chunks() - Create base video chunks with GST logo
# 3. personalize_specific_chunk() - Add username overlay to chunk
# 4. upload_video_post() - Upload video with user tag
# 5. share_post_to_dm() - Share the post to user's DM
# 6. send_message() - Send personalized cryptic message
# OR use send_ghost_video_with_specific_chunk() which combines steps 3-6

@mcp.tool()
def get_campaign_status(campaign_id: Optional[str] = None) -> Dict[str, Any]:
    """Get status of campaigns including completion rate and errors.
    
    Args:
        campaign_id: Optional specific campaign ID. If None, returns all campaigns.
    
    Returns:
        Dictionary with campaign status information
    """
    try:
        campaign_file = Path("campaigns.json")
        if not campaign_file.exists():
            return {"success": True, "campaigns": {}, "message": "No campaigns found"}
        
        with open(campaign_file, 'r') as f:
            campaigns_data = json.load(f)
        
        if campaign_id and campaign_id != "null":
            if campaign_id not in campaigns_data["campaigns"]:
                return {"success": False, "message": f"Campaign {campaign_id} not found"}
            
            campaign = campaigns_data["campaigns"][campaign_id]
            
            # Calculate simplified stats (3 states: pending, completed, failed)
            pending = sum(1 for u in campaign["users"].values() if u["status"] in ["pending", "personalized"])
            completed = sum(1 for u in campaign["users"].values() if u["status"] == "sent")
            failed = sum(1 for u in campaign["users"].values() if u["status"] == "error")
            
            return {
                "success": True,
                "campaign": {
                    "id": campaign_id,
                    "name": campaign["name"],
                    "status": campaign["status"],
                    "created_at": campaign["created_at"],
                    "stats": {
                        "total": campaign["stats"]["total_users"],
                        "completed": completed,
                        "pending": pending,
                        "failed": failed,
                        "completion_rate": f"{(completed/campaign['stats']['total_users']*100):.1f}%" if campaign['stats']['total_users'] > 0 else "0%"
                    }
                }
            }
        else:
            # Return summary of all campaigns
            campaigns_summary = []
            for cid, campaign in campaigns_data["campaigns"].items():
                # Simplified status tracking: pending, completed, failed
                pending = sum(1 for u in campaign["users"].values() if u["status"] in ["pending", "personalized"])
                completed = sum(1 for u in campaign["users"].values() if u["status"] == "sent")
                failed = sum(1 for u in campaign["users"].values() if u["status"] == "error")
                
                campaigns_summary.append({
                    "id": cid,
                    "name": campaign["name"],
                    "status": campaign["status"],
                    "created_at": campaign["created_at"],
                    "total_users": campaign["stats"]["total_users"],
                    "completed": completed,
                    "pending": pending,
                    "failed": failed,
                    "completion_rate": f"{(completed/campaign['stats']['total_users']*100):.1f}%" if campaign['stats']['total_users'] > 0 else "0%"
                })
            
            return {
                "success": True,
                "campaigns": campaigns_summary,
                "total_campaigns": len(campaigns_summary)
            }
            
    except Exception as e:
        logger.error(f"Failed to get campaign status: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def delete_campaigns(campaign_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Delete campaigns by ID or all campaigns if no IDs provided.
    
    Args:
        campaign_ids: Optional list of campaign IDs to delete. If None, deletes ALL campaigns.
    
    Returns:
        Dictionary with deletion status and count of deleted campaigns
    """
    try:
        campaign_file = Path("campaigns.json")
        if not campaign_file.exists():
            return {"success": True, "message": "No campaigns file found", "deleted_count": 0}
        
        with open(campaign_file, 'r') as f:
            campaigns_data = json.load(f)
        
        if not campaigns_data.get("campaigns"):
            return {"success": True, "message": "No campaigns to delete", "deleted_count": 0}
        
        if campaign_ids is None:
            # Delete all campaigns
            deleted_count = len(campaigns_data["campaigns"])
            campaigns_data["campaigns"] = {}
            
            with open(campaign_file, 'w') as f:
                json.dump(campaigns_data, f, indent=2)
            
            logger.info(f"Deleted all {deleted_count} campaigns")
            return {
                "success": True,
                "message": f"Deleted all {deleted_count} campaigns",
                "deleted_count": deleted_count
            }
        else:
            # Delete specific campaigns
            deleted = []
            not_found = []
            
            for campaign_id in campaign_ids:
                if campaign_id in campaigns_data["campaigns"]:
                    del campaigns_data["campaigns"][campaign_id]
                    deleted.append(campaign_id)
                else:
                    not_found.append(campaign_id)
            
            with open(campaign_file, 'w') as f:
                json.dump(campaigns_data, f, indent=2)
            
            result = {
                "success": True,
                "deleted_count": len(deleted),
                "deleted_campaigns": deleted
            }
            
            if not_found:
                result["not_found"] = not_found
                result["message"] = f"Deleted {len(deleted)} campaigns, {len(not_found)} not found"
            else:
                result["message"] = f"Successfully deleted {len(deleted)} campaigns"
            
            logger.info(f"Deleted campaigns: {deleted}")
            return result
            
    except Exception as e:
        logger.error(f"Failed to delete campaigns: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def fetch_bright_data_users(
    hashtags: List[str],
    min_followers: int = 100,
    max_followers: int = 50000,
    count: int = 200
) -> Dict[str, Any]:
    """Query Bright Data API for new Instagram users matching criteria.
    
    Args:
        hashtags: List of hashtags to search for (e.g., ["nostalgia", "liminalspaces"])
        min_followers: Minimum follower count
        max_followers: Maximum follower count  
        count: Number of users to fetch
    
    Returns:
        Dictionary with user list and save status
    """
    try:
        # Check for Bright Data credentials
        api_key = os.getenv("BRIGHT_DATA_API_KEY")
        dataset_id = os.getenv("BRIGHT_DATA_DATASET_ID", "gd_lpg8yd0y1b23u0pel")
        
        if not api_key:
            return {"success": False, "message": "BRIGHT_DATA_API_KEY not found in environment"}
        
        # Build filter query for Bright Data API
        filter_query = {
            "operator": "and",
            "filters": [
                {
                    "operator": "or",
                    "filters": [
                        {
                            "name": "post_hashtags",
                            "operator": "includes",
                            "value": hashtags
                        },
                        {
                            "name": "bio_hashtags",
                            "operator": "includes", 
                            "value": hashtags
                        }
                    ]
                },
                {
                    "name": "followers",
                    "operator": ">",
                    "value": min_followers
                },
                {
                    "name": "followers",
                    "operator": "<",
                    "value": max_followers
                },
                {
                    "name": "is_business_account",
                    "operator": "=",
                    "value": False
                },
                {
                    "name": "posts_count",
                    "operator": ">",
                    "value": 10
                }
            ]
        }
        
        # Make API request using multipart/form-data
        url = f"https://api.brightdata.com/datasets/filter?dataset_id={dataset_id}&records_limit={count}"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        # Send as form data
        files = {
            'filter': (None, json.dumps(filter_query))
        }
        
        response = requests.post(url, headers=headers, files=files)
        
        if response.status_code != 200:
            return {"success": False, "message": f"API error: {response.status_code} - {response.text}"}
        
        # Response could be snapshot ID or direct data
        data = response.json()
        
        if isinstance(data, dict) and 'snapshot_id' in data:
            # Snapshot workflow - return snapshot info for manual download later
            snapshot_id = data['snapshot_id']
            logger.info(f"Bright Data returned snapshot ID: {snapshot_id}")
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "message": f"Snapshot created. Use 'download_bright_data_snapshot' tool with ID: {snapshot_id}",
                "instructions": "Snapshots typically take 1-5 minutes to process. Download when ready."
            }
        else:
            # Direct data response (might happen with small datasets)
            users = data if isinstance(data, list) else []
        
        # Filter out private accounts
        public_users = [u for u in users if not u.get("is_private", True)]
        
        # Save to file - save the raw data directly as returned by Bright Data
        output_file = Path("datasets") / f"bright_data_users_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(exist_ok=True)
        
        # Save the full user list (matching the format of existing file)
        with open(output_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        # Create a separate filtered file for easy campaign creation
        filtered_file = Path("datasets") / f"filtered_users_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filtered_file, 'w') as f:
            json.dump({
                "source": "bright_data_api",
                "query": {
                    "hashtags": hashtags,
                    "min_followers": min_followers,
                    "max_followers": max_followers
                },
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "total_raw": len(users),
                "total_filtered": len(public_users),
                "users": [
                    {
                        "username": u.get("account"),
                        "user_id": u.get("id"),
                        "followers": u.get("followers", 0),
                        "following": u.get("following", 0),
                        "posts_count": u.get("posts_count", 0),
                        "avg_engagement": u.get("avg_engagement", 0),
                        "full_name": u.get("full_name", ""),
                        "biography": u.get("biography", ""),
                        "post_hashtags": u.get("post_hashtags", [])[:10] if u.get("post_hashtags") else []
                    }
                    for u in public_users
                ]
            }, f, indent=2)
        
        return {
            "success": True,
            "users_found": len(public_users),
            "file_path": str(output_file),
            "filtered_file_path": str(filtered_file),
            "message": f"Found {len(public_users)} public users matching criteria",
            "sample_users": [u.get("account", "unknown") for u in public_users[:5]]
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Bright Data API request failed: {str(e)}")
        return {"success": False, "message": f"API request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Failed to fetch Bright Data users: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def download_bright_data_snapshot(snapshot_id: str) -> Dict[str, Any]:
    """Download a Bright Data snapshot once it's ready.
    
    Args:
        snapshot_id: The snapshot ID returned by fetch_bright_data_users
    
    Returns:
        Dictionary with download status and file paths
    """
    try:
        api_key = os.getenv("BRIGHT_DATA_API_KEY")
        if not api_key:
            return {"success": False, "message": "BRIGHT_DATA_API_KEY not found in environment"}
        
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # First check snapshot status
        status_url = f"https://api.brightdata.com/datasets/snapshot/{snapshot_id}"
        status_response = requests.get(status_url, headers=headers)
        
        if status_response.status_code != 200:
            return {"success": False, "message": f"Failed to check snapshot status: {status_response.text}"}
        
        status_data = status_response.json()
        snapshot_status = status_data.get('status', 'unknown')
        
        if snapshot_status != 'ready':
            return {
                "success": False, 
                "status": snapshot_status,
                "message": f"Snapshot not ready yet. Status: {snapshot_status}. Try again in a minute."
            }
        
        # Download the snapshot
        download_url = f"https://api.brightdata.com/datasets/snapshot/{snapshot_id}/download"
        download_response = requests.get(download_url, headers=headers)
        
        if download_response.status_code != 200:
            return {"success": False, "message": f"Failed to download snapshot: {download_response.text}"}
        
        # Parse the data - handle both JSON and NDJSON formats
        try:
            # First try to parse as regular JSON
            users = download_response.json()
            if not isinstance(users, list):
                return {"success": False, "message": "Unexpected data format from snapshot"}
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try NDJSON (newline-delimited JSON)
            logger.info(f"Regular JSON parsing failed, trying NDJSON format: {str(e)}")
            users = []
            for line_num, line in enumerate(download_response.text.strip().split('\n'), 1):
                if line.strip():  # Skip empty lines
                    try:
                        users.append(json.loads(line))
                    except json.JSONDecodeError as line_error:
                        logger.error(f"Failed to parse NDJSON line {line_num}: {line_error}")
                        logger.error(f"Problematic line: {line[:100]}...")  # Log first 100 chars
            
            if not users:
                return {"success": False, "message": "Failed to parse response in either JSON or NDJSON format"}
        
        # Save the data (same format as direct response)
        output_file = Path("datasets") / f"bright_data_users_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        # Filter and create processed file
        public_users = [u for u in users if not u.get("is_private", True)]
        
        filtered_file = Path("datasets") / f"filtered_users_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filtered_file, 'w') as f:
            json.dump({
                "source": "bright_data_snapshot",
                "snapshot_id": snapshot_id,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "total_raw": len(users),
                "total_filtered": len(public_users),
                "users": [
                    {
                        "username": u.get("account"),
                        "user_id": u.get("id"),
                        "followers": u.get("followers", 0),
                        "following": u.get("following", 0),
                        "posts_count": u.get("posts_count", 0),
                        "avg_engagement": u.get("avg_engagement", 0),
                        "full_name": u.get("full_name", ""),
                        "biography": u.get("biography", ""),
                        "post_hashtags": u.get("post_hashtags", [])[:10] if u.get("post_hashtags") else []
                    }
                    for u in public_users
                ]
            }, f, indent=2)
        
        return {
            "success": True,
            "users_found": len(public_users),
            "file_path": str(output_file),
            "filtered_file_path": str(filtered_file),
            "message": f"Downloaded {len(public_users)} public users from snapshot",
            "sample_users": [u.get("account", "unknown") for u in public_users[:5]]
        }
        
    except Exception as e:
        logger.error(f"Failed to download Bright Data snapshot: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def select_random_users(
    count: int = 10,
    dataset_path: Optional[str] = None,
    exclude_used: bool = True,
    filter_criteria: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Select random users from datasets with optional filtering and history tracking.
    
    This tool helps avoid repeatedly selecting the same users by maintaining
    a history of previously selected users.
    
    Args:
        count: Number of users to select (default 10)
        dataset_path: Path to specific dataset file. If not provided, uses
                     the latest filtered_users_for_campaign.json
        exclude_used: If True, excludes previously selected users (default True)
        filter_criteria: Optional dictionary with filtering criteria:
                        - min_followers: Minimum follower count
                        - max_followers: Maximum follower count
                        - min_engagement: Minimum engagement rate
                        - has_biography: If True, only users with bios
                        - hashtags: List of hashtags user should have posted
    
    Returns:
        Dictionary with selected users and statistics
    """
    try:
        # Determine dataset path
        if dataset_path:
            data_path = Path(dataset_path)
        else:
            # Use default filtered dataset
            data_path = BASE_DIR.parent / "datasets" / "filtered_users_for_campaign.json"
        
        if not data_path.exists():
            return {
                "success": False,
                "message": f"Dataset not found: {data_path}"
            }
        
        # Load dataset
        with open(data_path, 'r') as f:
            dataset = json.load(f)
        
        users = dataset.get("users", [])
        if not users:
            return {
                "success": False,
                "message": "No users found in dataset"
            }
        
        # Load selection history
        history_path = BASE_DIR / "user_selection_history.json"
        if history_path.exists() and exclude_used:
            with open(history_path, 'r') as f:
                history = json.load(f)
        else:
            history = {"selected_users": {}, "selection_log": []}
        
        # Filter users based on criteria
        available_users = []
        for user in users:
            # Skip if already used (if exclude_used is True)
            if exclude_used and user["username"] in history["selected_users"]:
                continue
            
            # Apply filter criteria
            if filter_criteria:
                # Check follower count
                if "min_followers" in filter_criteria:
                    if user.get("followers", 0) < filter_criteria["min_followers"]:
                        continue
                if "max_followers" in filter_criteria:
                    if user.get("followers", 0) > filter_criteria["max_followers"]:
                        continue
                
                # Check engagement rate
                if "min_engagement" in filter_criteria:
                    if user.get("avg_engagement", 0) < filter_criteria["min_engagement"]:
                        continue
                
                # Check biography
                if filter_criteria.get("has_biography"):
                    if not user.get("biography"):
                        continue
                
                # Check hashtags
                if "hashtags" in filter_criteria:
                    user_hashtags = set(user.get("post_hashtags", []))
                    required_hashtags = set(filter_criteria["hashtags"])
                    if not user_hashtags.intersection(required_hashtags):
                        continue
            
            available_users.append(user)
        
        # Check if we have enough users
        if len(available_users) < count:
            if exclude_used:
                # Try without excluding used users
                logger.warning(f"Not enough new users ({len(available_users)}). Including previously used users.")
                return select_random_users(
                    count=count,
                    dataset_path=dataset_path,
                    exclude_used=False,
                    filter_criteria=filter_criteria
                )
            else:
                return {
                    "success": False,
                    "message": f"Only {len(available_users)} users available, requested {count}"
                }
        
        # Random selection
        selected = random.sample(available_users, count)
        
        # Update history
        timestamp = datetime.now().isoformat()
        for user in selected:
            username = user["username"]
            if username not in history["selected_users"]:
                history["selected_users"][username] = {
                    "first_selected": timestamp,
                    "times_selected": 0,
                    "campaigns": []
                }
            history["selected_users"][username]["times_selected"] += 1
            history["selected_users"][username]["last_selected"] = timestamp
        
        # Add to selection log
        history["selection_log"].append({
            "timestamp": timestamp,
            "count": count,
            "usernames": [u["username"] for u in selected],
            "filter_criteria": filter_criteria,
            "dataset": str(data_path)
        })
        
        # Save updated history
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Prepare response
        return {
            "success": True,
            "count": len(selected),
            "users": selected,
            "stats": {
                "total_available": len(available_users),
                "total_in_dataset": len(users),
                "previously_used": len(history["selected_users"]),
                "excluded_users": len(users) - len(available_users)
            },
            "usernames": [u["username"] for u in selected],
            "message": f"Selected {len(selected)} random users"
        }
        
    except Exception as e:
        logger.error(f"Failed to select random users: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def create_video_chunks(
    count: int = 10,
    duration: Optional[int] = None,
    source_video: Optional[str] = None
) -> Dict[str, Any]:
    """Create video chunks from raw footage with GST logo.
    
    These chunks are pre-processed base videos that can be quickly
    personalized with usernames during campaigns.
    
    Args:
        count: Number of chunks to create (default 10)
        duration: Optional duration for chunks in seconds (default 15-25)
        source_video: Optional specific video file to use (e.g., "Wendys Grill Skills.mp4")
                     If not provided, randomly selects from available videos
    
    Returns:
        Dictionary with creation results
    """
    if not chunk_processor:
        return {"success": False, "message": "Chunk processor not available"}
    
    try:
        logger.info(f"Creating {count} video chunks...")
        
        # Handle source video path if provided
        video_path = None
        if source_video:
            # Check if it's just a filename or a full path
            if "/" not in source_video and "\\" not in source_video:
                video_path = MEDIA_DIR / "raw" / source_video
            else:
                video_path = Path(source_video)
            
            # Validate the video path
            if not video_path.exists():
                return {"success": False, "message": f"Video file not found: {video_path}"}
            if video_path.suffix.lower() not in ['.mp4', '.avi', '.mkv']:
                return {"success": False, "message": f"Invalid video format. Please use MP4, AVI, or MKV files."}
            
            logger.info(f"Using specific source video: {video_path}")
        
        if duration or source_video:
            # Create chunks with specific duration and/or source video
            results = {
                "success": True,
                "chunks_created": 0,
                "errors": [],
                "chunks": []
            }
            
            for i in range(count):
                result = chunk_processor.create_chunk(
                    source_video=video_path,
                    duration=duration
                )
                if result["success"]:
                    results["chunks_created"] += 1
                    results["chunks"].append({
                        "chunk_id": result["chunk_id"],
                        "filename": result["filename"],
                        "duration": result["duration"],
                        "size_mb": result["size_mb"]
                    })
                else:
                    results["errors"].append(result.get("message"))
            
            return results
        else:
            # Use batch creation for varied durations with random sources
            return chunk_processor.create_chunk_batch(count)
            
    except Exception as e:
        logger.error(f"Failed to create chunks: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def list_video_chunks(limit: int = 50, source_filter: Optional[str] = None) -> Dict[str, Any]:
    """List available pre-processed video chunks.
    
    Args:
        limit: Maximum number of chunks to return (default: 50)
        source_filter: Optional filter by source video name
    
    Returns:
        Dictionary with available chunks information
    """
    if not chunk_processor:
        return {"success": False, "message": "Chunk processor not available"}
    
    try:
        chunks = chunk_processor.get_available_chunks()
        
        # Apply source filter if provided
        if source_filter:
            chunks = [c for c in chunks if source_filter.lower() in c.get("source", "").lower()]
        
        # Apply limit
        chunks = chunks[:limit]
        
        return {
            "success": True,
            "count": len(chunks),
            "chunks": chunks
        }
    except Exception as e:
        logger.error(f"Failed to list chunks: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def get_chunk_info(chunk_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific video chunk.
    
    Args:
        chunk_id: The chunk ID to get information for
        
    Returns:
        Dictionary with chunk details
    """
    if not chunk_processor:
        return {"success": False, "message": "Chunk processor not available"}
    
    try:
        chunks = chunk_processor.get_available_chunks()
        chunk_info = next((c for c in chunks if c.get("chunk_id") == chunk_id), None)
        
        if chunk_info:
            return {
                "success": True,
                "chunk": chunk_info
            }
        else:
            return {"success": False, "message": f"Chunk {chunk_id} not found"}
            
    except Exception as e:
        logger.error(f"Failed to get chunk info: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def prepare_campaign_videos(
    campaign_id: str,
    usernames: List[str],
    ensure_chunks: Optional[int] = None
) -> Dict[str, Any]:
    """Pre-personalize videos for campaign users using available chunks.
    
    This creates personalized videos by adding username overlays to chunks
    before the campaign starts, improving performance during execution.
    
    Args:
        campaign_id: Campaign identifier
        usernames: List of Instagram usernames to create videos for
        ensure_chunks: If specified, create this many chunks if not enough available
    
    Returns:
        Dictionary with preparation results
    """
    if not video_processors_available:
        return {"success": False, "message": "Video processors not available"}
    
    try:
        # Load campaign data to update with tracking info
        campaign_file = Path("campaigns.json")
        campaigns_data = {"campaigns": {}}
        if campaign_file.exists():
            with open(campaign_file, 'r') as f:
                campaigns_data = json.load(f)
        
        # Check if campaign exists
        if campaign_id not in campaigns_data["campaigns"]:
            logger.warning(f"Campaign {campaign_id} not found, creating minimal entry")
            campaigns_data["campaigns"][campaign_id] = {
                "name": campaign_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "status": "active",
                "users": {}
            }
        
        campaign = campaigns_data["campaigns"][campaign_id]
        
        # Check chunk availability
        chunks = chunk_processor.get_available_chunks()
        logger.info(f"Found {len(chunks)} chunks available")
        
        # Create more chunks if requested
        if ensure_chunks and len(chunks) < ensure_chunks:
            needed = ensure_chunks - len(chunks)
            logger.info(f"Creating {needed} additional chunks...")
            
            create_result = chunk_processor.create_chunk_batch(count=needed)
            if create_result["success"]:
                logger.info(f"Created {create_result['chunks_created']} new chunks")
                chunks = chunk_processor.get_available_chunks()
            else:
                logger.warning("Failed to create additional chunks")
        
        if len(chunks) == 0:
            return {"success": False, "message": "No chunks available. Create chunks first with create_video_chunks tool."}
        
        # Personalize videos for users
        results = {
            "success": True,
            "campaign_id": campaign_id,
            "total_users": len(usernames),
            "videos_created": 0,
            "errors": []
        }
        
        # Process users
        # Shuffle chunks for better randomization
        import random
        random.shuffle(chunks)
        chunk_index = 0
        
        for username in usernames:
            try:
                # Round-robin through shuffled chunks
                chunk = chunks[chunk_index % len(chunks)]
                chunk_path = Path(chunk["path"])
                
                # Personalize the chunk
                result = personalization_processor.personalize_chunk(
                    username=username,
                    chunk_path=chunk_path,
                    campaign_id=campaign_id
                )
                
                if result["success"]:
                    results["videos_created"] += 1
                    
                    # Update campaign data with tracking info
                    if "users" not in campaign:
                        campaign["users"] = {}
                    
                    # Initialize user data if not exists
                    if username not in campaign["users"]:
                        campaign["users"][username] = {}
                    
                    # Update with personalization tracking data
                    campaign["users"][username].update({
                        "status": "personalized",
                        "chunk_id": chunk.get("chunk_id"),
                        "chunk_source": chunk.get("source"),
                        "personalized_video_path": result["path"],
                        "personalized_url": f"vhs-ghost.com/{username}",
                        "personalized_at": datetime.utcnow().isoformat() + "Z"
                    })
                    
                else:
                    results["errors"].append({
                        "username": username,
                        "error": result.get("message", "Unknown error")
                    })
                
                chunk_index += 1
                
            except Exception as e:
                results["errors"].append({
                    "username": username,
                    "error": str(e)
                })
        
        # Save updated campaign data
        with open(campaign_file, 'w') as f:
            json.dump(campaigns_data, f, indent=2)
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to prepare campaign videos: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def personalize_specific_chunk(
    chunk_id: str,
    username: str,
    campaign_id: str = "default"
) -> Dict[str, Any]:
    """Personalize a specific video chunk for a user.
    
    This tool allows personalizing a specific chunk by its ID rather than
    using a random chunk. Useful for testing or specific requirements.
    
    Args:
        chunk_id: The ID of the chunk to personalize (e.g., "72568e3f")
        username: Instagram username to personalize for
        campaign_id: Campaign identifier (default: "default")
    
    Returns:
        Dictionary with success status and personalized video path
    """
    if not video_processors_available or not personalization_processor:
        return {"success": False, "message": "Video processors not available"}
    
    try:
        # Get the specific chunk
        chunk_path = personalization_processor.get_chunk_by_id(chunk_id)
        if not chunk_path:
            return {"success": False, "message": f"Chunk {chunk_id} not found"}
        
        logger.info(f"Personalizing chunk {chunk_id} for @{username}")
        
        # Personalize the chunk
        result = personalization_processor.personalize_chunk(
            username=username,
            chunk_path=chunk_path,
            campaign_id=campaign_id
        )
        
        if result["success"]:
            logger.info(f"Successfully personalized chunk {chunk_id} for @{username}")
            return {
                "success": True,
                "path": result["path"],
                "filename": result["filename"],
                "size_mb": result["size_mb"],
                "chunk_id": chunk_id,
                "message": f"Personalized chunk {chunk_id} for @{username}"
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Failed to personalize specific chunk: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def get_account_status() -> Dict[str, Any]:
    """Get status of all configured Instagram accounts.
    
    Returns:
        Dictionary with account statuses including daily action counts
    """
    if not account_pool:
        # Single account mode
        proxy_status = "configured" if os.getenv('PROXY') else "not configured"
        return {
            "success": True,
            "mode": "single_account",
            "accounts": {
                "default": {
                    "status": "active" if client else "not_configured",
                    "proxy": proxy_status
                }
            }
        }
    
    try:
        status = account_pool.get_account_status()
        # Add proxy info to each account
        for username, account_info in status.items():
            if username in account_pool.accounts:
                has_proxy = bool(account_pool.accounts[username].get('proxy'))
                account_info['proxy'] = "configured" if has_proxy else "not configured"
        return {
            "success": True,
            "mode": "multi_account", 
            "accounts": status
        }
    except Exception as e:
        logger.error(f"Failed to get account status: {str(e)}")
        return {"success": False, "message": str(e)}

@mcp.tool()
def mark_operation_complete() -> Dict[str, Any]:
    """
    Mark the current Instagram operation as complete and trigger account cooldown.
    
    Call this after completing a full operation (e.g., post + DM combo) to:
    - Put the active account into cooldown (5 minutes)
    - Free up the account pool to select a new account
    - Ensure proper rotation and avoid detection
    
    Returns:
        Dictionary with success status and cooldown information
    """
    global account_pool
    
    if not account_pool:
        return {
            "success": False, 
            "message": "No account pool available"
        }
    
    try:
        success = account_pool.mark_operation_complete()
        if success:
            logger.info("Operation marked complete")
            return {
                "success": True,
                "message": "Operation complete"
            }
        else:
            return {
                "success": False,
                "message": "No active account to mark complete"
            }
    except Exception as e:
        logger.error(f"Failed to mark operation complete: {str(e)}")
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
   parser = argparse.ArgumentParser()
   parser.add_argument("--username", type=str, help="Instagram username (can also be set via INSTAGRAM_USERNAME env var)")
   parser.add_argument("--password", type=str, help="Instagram password (can also be set via INSTAGRAM_PASSWORD env var)")
   # Default to accounts.json in the instagram_mcp directory
   default_accounts_file = str(BASE_DIR / "accounts.json")
   parser.add_argument("--accounts-file", type=str, default=default_accounts_file, help="Path to accounts configuration file (default: accounts.json in instagram_mcp dir)")
   parser.add_argument("--use-account-pool", action="store_true", help="Enable multi-account support using accounts.json")
   args = parser.parse_args()

   # Check if we should use account pool
   if args.use_account_pool or os.path.exists(args.accounts_file):
       # Multi-account mode
       logger.info(f"Starting in multi-account mode using {args.accounts_file}")
       # Use on-demand loading - accounts authenticate when first used
       sessions_dir = str(BASE_DIR / "sessions")
       account_pool = AccountPool(
           config_path=args.accounts_file,
           sessions_dir=sessions_dir
       )
       logger.info("Account pool configured with on-demand authentication")
   else:
       # Single account mode (backwards compatibility)
       username = args.username or os.getenv("INSTAGRAM_USERNAME")
       password = args.password or os.getenv("INSTAGRAM_PASSWORD")

       if not username or not password:
           logger.error("Instagram credentials not provided. Please set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables in a .env file, or provide --username and --password arguments.")
           print("Error: Instagram credentials not provided.")
           print("Please either:")
           print("1. Create a .env file with INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD")
           print("2. Use --username and --password command line arguments")
           print("3. Create accounts.json for multi-account support")
           exit(1)

       try:
           logger.info("Starting in single account mode")
           logger.info("Attempting to login to Instagram...")
           client = Client()
           
           # Set proxy if configured
           proxy = os.getenv('PROXY')
           if proxy:
               client.set_proxy(proxy)
               logger.info(f"Set proxy for single account")
           
           client.login(username, password)
           logger.info("Successfully logged in to Instagram")
       except Exception as e:
           logger.error(f"Failed to login to Instagram: {str(e)}")
           print(f"Error: Failed to login to Instagram - {str(e)}")
           exit(1)

   # Verify video processors if available
   if video_processors_available:
       logger.info("Verifying two-stage video processor setup...")
       
       # Check for existing chunks
       if chunk_processor:
           chunks = chunk_processor.get_available_chunks()
           if chunks:
               logger.info(f"Found {len(chunks)} pre-processed chunks ready for use")
           else:
               logger.warning("No video chunks found. Use create_video_chunks tool to create some.")
       
       logger.info("Two-stage video processing ready")
   else:
       logger.warning("Video processors not available - using legacy FFmpeg for video personalization")

   # Run the MCP server
   try:
       mcp.run(transport="stdio")
   except Exception as e:
       logger.error(f"MCP server error: {str(e)}")
       print(f"Error: MCP server failed - {str(e)}")
       exit(1)
