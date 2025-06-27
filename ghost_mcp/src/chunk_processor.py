"""
Chunk Processor - Creates base video chunks with GST logo
These chunks are then personalized with usernames during campaigns
"""

import os
import subprocess
from pathlib import Path
import random
import logging
import hashlib
import json
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class ChunkProcessor:
    def __init__(self):
        # Get the base directory (instagram_mcp)
        base_dir = Path(__file__).parent.parent
        media_dir = base_dir / "media"
        
        self.raw_dir = media_dir / "raw"
        self.chunks_dir = media_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        
        # GST logo
        self.gst_logo = media_dir / "gst.png"
        
        # Metadata tracking
        self.metadata_file = self.chunks_dir / "chunks_metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """Load chunk metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"chunks": {}, "sources": {}}
    
    def _save_metadata(self):
        """Save chunk metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration in seconds"""
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timeout for {video_path}")
            return None
        except Exception as e:
            logger.error(f"Error getting duration: {str(e)}")
            return None
    
    def get_available_raw_videos(self) -> List[Path]:
        """Get MP4 videos only for best compatibility"""
        videos = list(self.raw_dir.glob("*.mp4"))
        logger.info(f"Found {len(videos)} MP4 source videos")
        return videos
    
    def create_chunk(self, source_video: Optional[Path] = None, 
                    duration: Optional[int] = None,
                    chunk_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a single chunk with GST logo overlay
        
        Args:
            source_video: Optional specific video to use
            duration: Chunk duration in seconds (default: 15-25)
            chunk_id: Optional ID for the chunk
            
        Returns:
            Dict with chunk information
        """
        try:
            # Select source video
            if source_video is None:
                videos = self.get_available_raw_videos()
                if not videos:
                    return {"success": False, "message": "No MP4 videos available"}
                source_video = random.choice(videos)
            
            # Get duration
            total_duration = self.get_video_duration(source_video)
            if not total_duration:
                return {"success": False, "message": f"Could not read duration for {source_video.name}"}
            
            # Determine chunk duration (13-20 seconds)
            if duration is None:
                duration = random.randint(13, 20)
            
            # Calculate safe start time
            safe_start = 5
            safe_end = total_duration - duration - 5
            
            if safe_end <= safe_start:
                safe_start = 0
                safe_end = max(0, total_duration - duration)
                if safe_end <= 0:
                    return {"success": False, "message": "Video too short for chunking"}
            
            start_time = random.uniform(safe_start, safe_end)
            
            # Generate chunk ID
            if chunk_id is None:
                chunk_id = hashlib.md5(
                    f"{source_video.name}{start_time}{os.urandom(4).hex()}".encode()
                ).hexdigest()[:8]
            
            output_filename = f"chunk_{chunk_id}.mp4"
            output_path = self.chunks_dir / output_filename
            
            # Build FFmpeg command
            logger.info(f"Creating chunk from {source_video.name} [{start_time:.1f}s - {start_time + duration:.1f}s]")
            
            if self.gst_logo.exists():
                # With logo overlay from 7 seconds to end
                logo_start = 7
                
                cmd = [
                    'ffmpeg', '-y',
                    '-ss', str(start_time),
                    '-i', str(source_video),
                    '-i', str(self.gst_logo),
                    '-t', str(duration),
                    '-filter_complex', (
                        # Crop to vertical and scale
                        '[0:v]crop=ih*9/16:ih,scale=1080:1920[vid];'
                        # Scale logo and overlay
                        f'[1:v]scale=iw*0.88:ih*0.88[logo];'
                        f'[vid][logo]overlay=x=(W-w)/2:y=H*0.075:enable=\'gte(t,{logo_start})\''
                    ),
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    str(output_path)
                ]
            else:
                # Without logo
                cmd = [
                    'ffmpeg', '-y',
                    '-ss', str(start_time),
                    '-i', str(source_video),
                    '-t', str(duration),
                    '-vf', 'crop=ih*9/16:ih,scale=1080:1920',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    str(output_path)
                ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg error: {result.stderr}")
                    return {"success": False, "message": "Failed to create chunk", "error": result.stderr}
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg timeout after 120s creating chunk from {source_video.name}")
                return {"success": False, "message": f"FFmpeg timeout creating chunk from {source_video.name}"}
            
            # Update metadata
            self.metadata["chunks"][chunk_id] = {
                "filename": output_filename,
                "source": source_video.name,
                "start_time": start_time,
                "duration": duration,
                "created": os.path.getmtime(output_path)
            }
            self._save_metadata()
            
            # Get file size
            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            
            logger.info(f"Created chunk: {output_filename} ({file_size:.1f} MB)")
            
            return {
                "success": True,
                "chunk_id": chunk_id,
                "path": str(output_path),
                "filename": output_filename,
                "duration": duration,
                "size_mb": file_size,
                "source": source_video.name
            }
            
        except Exception as e:
            logger.error(f"Failed to create chunk: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def create_chunk_batch(self, count: int = 10) -> Dict[str, Any]:
        """Create multiple chunks at once"""
        results = {
            "success": True,
            "chunks_created": 0,
            "errors": [],
            "chunks": []
        }
        
        videos = self.get_available_raw_videos()
        if not videos:
            return {"success": False, "message": "No source videos available"}
        
        for i in range(count):
            # Rotate through source videos
            source = videos[i % len(videos)]
            
            result = self.create_chunk(source_video=source)
            
            if result["success"]:
                results["chunks_created"] += 1
                results["chunks"].append({
                    "chunk_id": result["chunk_id"],
                    "filename": result["filename"],
                    "duration": result["duration"]
                })
            else:
                results["errors"].append(result.get("message", "Unknown error"))
        
        return results
    
    def get_available_chunks(self) -> List[Dict[str, Any]]:
        """Get list of available chunks"""
        chunks = []
        
        for chunk_file in self.chunks_dir.glob("chunk_*.mp4"):
            chunk_id = chunk_file.stem.replace("chunk_", "")
            
            # Get metadata if available
            if chunk_id in self.metadata.get("chunks", {}):
                chunk_info = self.metadata["chunks"][chunk_id].copy()
                chunk_info["chunk_id"] = chunk_id
                chunk_info["path"] = str(chunk_file)
            else:
                # Basic info if no metadata
                chunk_info = {
                    "chunk_id": chunk_id,
                    "filename": chunk_file.name,
                    "path": str(chunk_file)
                }
            
            chunks.append(chunk_info)
        
        return chunks
    
    def cleanup_old_chunks(self, days: int = 30):
        """Remove chunks older than specified days"""
        import time
        current_time = time.time()
        
        for chunk_file in self.chunks_dir.glob("chunk_*.mp4"):
            file_age = current_time - chunk_file.stat().st_mtime
            if file_age > (days * 24 * 3600):
                try:
                    chunk_file.unlink()
                    logger.info(f"Deleted old chunk: {chunk_file.name}")
                    
                    # Remove from metadata
                    chunk_id = chunk_file.stem.replace("chunk_", "")
                    if chunk_id in self.metadata.get("chunks", {}):
                        del self.metadata["chunks"][chunk_id]
                        self._save_metadata()
                        
                except Exception as e:
                    logger.error(f"Failed to delete {chunk_file}: {e}")


# Singleton instance
chunk_processor = ChunkProcessor()