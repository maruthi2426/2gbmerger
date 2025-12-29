import subprocess
import os
import logging
import asyncio

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Handle all video processing operations using FFmpeg"""
    
    def __init__(self):
        self.temp_dir = 'temp'
        self.output_dir = 'output'
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def merge_videos(self, video_files: list, status_msg=None) -> str:
        """Merge multiple videos into one"""
        try:
            if status_msg:
                if hasattr(status_msg, 'edit'):
                    await status_msg.edit(
                        "🔄 Processing...\n"
                        f"📹 Step 1/3: Verifying {len(video_files)} videos...\n"
                        "⏳ Checking files..."
                    )
            
            # Verify all video files exist
            for idx, video in enumerate(video_files):
                if not os.path.exists(video):
                    raise Exception(f"Video file not found: {video}")
                size = os.path.getsize(video)
                logger.info(f"Video {idx + 1}: {video} ({size / (1024*1024):.2f} MB)")
            
            if status_msg and hasattr(status_msg, 'edit'):
                await status_msg.edit(
                    "🔄 Processing...\n"
                    f"📹 Step 2/3: Creating merge list...\n"
                    "⏳ Preparing files..."
                )
            
            list_file = os.path.join(self.temp_dir, 'videos.txt')
            with open(list_file, 'w', encoding='utf-8') as f:
                for video in video_files:
                    # Use absolute path and proper escaping
                    abs_path = os.path.abspath(video)
                    # For Windows, convert backslashes to forward slashes
                    normalized_path = abs_path.replace('\\', '/')
                    # Escape single quotes for FFmpeg
                    escaped_path = normalized_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            logger.info(f"Created concat file list: {list_file}")
            
            # Log the list file contents for debugging
            with open(list_file, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"List file contents:\n{content}")
            
            output_file = os.path.join(self.output_dir, 'merged_output.mp4')
            
            if status_msg and hasattr(status_msg, 'edit'):
                await status_msg.edit(
                    "🔄 Processing...\n"
                    f"📹 Step 3/3: Merging {len(video_files)} videos...\n"
                    "⏳ This may take several minutes...\n"
                    "🔧 FFmpeg is working..."
                )
            
            # Try copy first (faster), if it fails, re-encode
            cmd_copy = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',  # Copy streams without re-encoding (faster)
                '-movflags', '+faststart',
                '-y',
                output_file
            ]
            
            logger.info(f"Trying fast merge (copy): {' '.join(cmd_copy)}")
            result = subprocess.run(cmd_copy, capture_output=True, text=True)
            
            if result.returncode != 0 or not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                logger.warning(f"Fast merge failed, re-encoding... Error: {result.stderr}")
                
                if status_msg and hasattr(status_msg, 'edit'):
                    await status_msg.edit(
                        "🔄 Processing...\n"
                        f"📹 Re-encoding for compatibility...\n"
                        "⏳ This will take longer but ensures quality...\n"
                        "🔧 FFmpeg is re-encoding..."
                    )
                
                # Remove failed output if exists
                if os.path.exists(output_file):
                    os.remove(output_file)
                
                cmd_encode = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_file,
                    '-c:v', 'libx264',
                    '-preset', 'veryfast',  # Balance between speed and quality
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-max_muxing_queue_size', '9999',  # Handle large files
                    '-y',
                    output_file
                ]
                
                logger.info(f"Running re-encode: {' '.join(cmd_encode)}")
                result = subprocess.run(cmd_encode, capture_output=True, text=True, timeout=3600)
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg stderr: {result.stderr}")
                    logger.error(f"FFmpeg stdout: {result.stdout}")
                    raise Exception(f"FFmpeg merge failed: {result.stderr[-500:]}")  # Last 500 chars
            
            if not os.path.exists(output_file):
                raise Exception("Output file was not created by FFmpeg")
            
            file_size = os.path.getsize(output_file)
            if file_size == 0:
                raise Exception("Output file is empty (0 bytes)")
            
            logger.info(f"✅ Videos merged successfully: {output_file} ({file_size / (1024*1024):.2f} MB)")
            
            # Cleanup temp file
            try:
                if os.path.exists(list_file):
                    os.remove(list_file)
            except Exception as e:
                logger.warning(f"Could not remove temp file: {e}")
            
            return output_file
        
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg process timed out after 1 hour")
            raise Exception("Video merge timed out - videos may be too large or complex")
        except Exception as e:
            logger.error(f"Error merging videos: {e}", exc_info=True)
            raise
    
    async def merge_video_audio(self, video_file: str, audio_file: str, status_msg=None) -> str:
        """Replace video's audio with new audio"""
        try:
            if status_msg and hasattr(status_msg, 'edit'):
                await status_msg.edit(
                    "🔄 Processing...\n"
                    "🔊 Analyzing video and audio files...\n"
                    "⏳ Please wait..."
                )
            
            output_file = os.path.join(self.output_dir, 'video_with_audio.mp4')
            
            if status_msg and hasattr(status_msg, 'edit'):
                await status_msg.edit(
                    "🔄 Processing...\n"
                    "🔊 Merging audio with video...\n"
                    "⏳ This may take a few minutes..."
                )
            
            cmd = [
                'ffmpeg',
                '-i', video_file,
                '-i', audio_file,
                '-c:v', 'libx264',  # Re-encode video
                '-preset', 'ultrafast',  # Fastest encoding
                '-crf', '23',
                '-c:a', 'aac',   # Encode audio to AAC
                '-b:a', '128k',
                '-map', '0:v:0', # Map video from first input
                '-map', '1:a:0', # Map audio from second input
                '-shortest',     # Finish when shortest stream ends
                '-movflags', '+faststart',
                '-y',
                output_file
            ]
            
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"FFmpeg error: {result.stderr}")
            
            logger.info(f"✅ Video and audio merged successfully: {output_file}")
            return output_file
        
        except Exception as e:
            logger.error(f"Error merging video and audio: {e}", exc_info=True)
            raise
    
    async def add_subtitles(self, video_file: str, subtitle_file: str, status_msg=None) -> str:
        """Add subtitles to video (burn them in)"""
        try:
            if status_msg and hasattr(status_msg, 'edit'):
                await status_msg.edit(
                    "🔄 Processing...\n"
                    "📝 Loading subtitle file...\n"
                    "⏳ Please wait..."
                )
            
            output_file = os.path.join(self.output_dir, 'video_with_subtitles.mp4')
            
            subtitle_path = os.path.abspath(subtitle_file).replace('\\', '/').replace(':', '\\:').replace("'", "'\\''")
            
            if status_msg and hasattr(status_msg, 'edit'):
                await status_msg.edit(
                    "🔄 Processing...\n"
                    "📝 Burning subtitles into video...\n"
                    "⏳ This may take several minutes..."
                )
            
            cmd = [
                'ffmpeg',
                '-i', video_file,
                '-vf', f"subtitles='{subtitle_path}'",
                '-preset', 'ultrafast',
                '-crf', '23',
                '-c:a', 'copy',  # Copy audio
                '-movflags', '+faststart',
                '-y',
                output_file
            ]
            
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"FFmpeg error: {result.stderr}")
            
            logger.info(f"✅ Subtitles added successfully: {output_file}")
            return output_file
        
        except Exception as e:
            logger.error(f"Error adding subtitles: {e}", exc_info=True)
            raise
    
    async def extract_audio(self, video_file: str, status_msg=None) -> str:
        """Extract audio from video without re-encoding"""
        try:
            if status_msg and hasattr(status_msg, 'edit'):
                await status_msg.edit(
                    "🔄 Processing...\n"
                    "🎵 Detecting audio format...\n"
                    "⏳ Please wait..."
                )
            
            # Detect audio codec
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'default=nw=1:nk=1',
                video_file
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            codec = result.stdout.strip()
            
            # Map codec to file extension
            extension_map = {
                'aac': 'm4a',
                'mp3': 'mp3',
                'opus': 'opus',
                'vorbis': 'ogg',
                'flac': 'flac',
                'alac': 'm4a',
                'ac3': 'ac3',
                'eac3': 'eac3',
                'dts': 'dts',
                'pcm_s16le': 'wav',
                'pcm_s24le': 'wav',
                'wavpack': 'wav',
                'amr_nb': 'amr',
                'amr_wb': 'amr',
                'gsm': 'gsm'
            }
            
            extension = extension_map.get(codec, 'm4a')
            output_file = os.path.join(self.output_dir, f'extracted_audio.{extension}')
            
            if status_msg and hasattr(status_msg, 'edit'):
                await status_msg.edit(
                    "🔄 Processing...\n"
                    f"🎵 Extracting audio as .{extension}...\n"
                    "⏳ Almost done..."
                )
            
            cmd = [
                'ffmpeg',
                '-i', video_file,
                '-vn',  # No video
                '-acodec', 'copy',  # Copy audio without re-encoding
                '-y',
                output_file
            ]
            
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"FFmpeg error: {result.stderr}")
            
            logger.info(f"✅ Audio extracted successfully: {output_file}")
            return output_file
        
        except Exception as e:
            logger.error(f"Error extracting audio: {e}", exc_info=True)
            raise
