"""
Personalization Processor - Adds username overlays to pre-made chunks
Fast and simple - only does text overlay during campaigns
"""

import os
import subprocess
from pathlib import Path
import random
import logging
import tempfile
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class PersonalizationProcessor:
    def __init__(self):
        # Get the base directory (instagram_mcp)
        base_dir = Path(__file__).parent.parent
        media_dir = base_dir / "media"
        
        self.chunks_dir = media_dir / "chunks"
        self.campaign_dir = media_dir / "campaign_videos"
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        
        # Font settings
        self.font = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
        if not Path(self.font).exists():
            self.font = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"
    
    def personalize_chunk(self, username: str, chunk_path: Path, 
                         campaign_id: str = "default") -> Dict[str, Any]:
        """
        Add username overlay to a pre-made chunk
        
        This is fast because it only adds text overlay, no complex processing
        
        Args:
            username: Instagram username (without @)
            chunk_path: Path to the chunk video
            campaign_id: Campaign identifier
            
        Returns:
            Dict with success status and output path
        """
        try:
            if not chunk_path.exists():
                return {"success": False, "message": f"Chunk not found: {chunk_path}"}
            
            # Output filename
            output_filename = f"{campaign_id}_{username}_{os.urandom(4).hex()}.mp4"
            output_path = self.campaign_dir / output_filename
            
            # Build flashing text overlay command (0-8 seconds)
            # Flash between username and messages
            messages = [
                f"@{username}",
                "YOUVE BEEN CHOSEN",
                "FIND THE GHOST",
                "FOLLOW THE TRACE"
            ]
            
            # Build filter for flashing text
            filters = []
            flash_duration = 0.5  # Each message shows for 0.5 seconds
            current_time = 0.0
            
            # Repeat sequence to fill 8 seconds
            for i in range(16):  # 16 * 0.5 = 8 seconds
                msg = messages[i % len(messages)]
                start_t = current_time
                end_t = current_time + flash_duration
                
                # Three layers for VHS effect
                # Cyan offset
                filters.append(
                    f"drawtext=text='{msg}':fontfile={self.font}:fontsize=56:"
                    f"fontcolor=#00ffff@0.7:x=(w-text_w)/2-2:y=h/2-2:"
                    f"enable='between(t,{start_t},{end_t})'"
                )
                # Magenta offset
                filters.append(
                    f"drawtext=text='{msg}':fontfile={self.font}:fontsize=56:"
                    f"fontcolor=#ff00ff@0.7:x=(w-text_w)/2+2:y=h/2+2:"
                    f"enable='between(t,{start_t},{end_t})'"
                )
                # Green base
                filters.append(
                    f"drawtext=text='{msg}':fontfile={self.font}:fontsize=56:"
                    f"fontcolor=#00ff00:x=(w-text_w)/2:y=h/2:"
                    f"enable='between(t,{start_t},{end_t})'"
                )
                
                current_time = end_t
            
            # Join all filters
            filter_string = ",".join(filters)
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(chunk_path),
                '-vf', filter_string,
                '-c:v', 'libx264',
                '-preset', 'veryfast',  # Very fast since we're just adding text
                '-crf', '23',
                '-c:a', 'copy',  # Copy audio without re-encoding
                str(output_path)
            ]
            
            logger.info(f"Personalizing chunk for @{username}...")
            try:
                # Add timeout to prevent hanging (60 seconds should be plenty)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg error: {result.stderr}")
                    return {"success": False, "message": "Failed to personalize chunk", "error": result.stderr}
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg timeout after 60s for chunk {chunk_path.name}")
                return {"success": False, "message": f"FFmpeg timeout processing chunk {chunk_path.name}"}
            
            # Get file size
            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            
            logger.info(f"Created personalized video: {output_filename} ({file_size:.1f} MB)")
            
            return {
                "success": True,
                "path": str(output_path),
                "filename": output_filename,
                "size_mb": file_size,
                "chunk_used": chunk_path.name
            }
            
        except Exception as e:
            logger.error(f"Failed to personalize chunk: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def get_random_chunk(self) -> Optional[Path]:
        """Get a random available chunk"""
        chunks = list(self.chunks_dir.glob("chunk_*.mp4"))
        if chunks:
            return random.choice(chunks)
        return None
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Path]:
        """Get a specific chunk by its ID"""
        chunk_path = self.chunks_dir / f"chunk_{chunk_id}.mp4"
        if chunk_path.exists():
            return chunk_path
        return None


# Singleton instance
personalization_processor = PersonalizationProcessor()