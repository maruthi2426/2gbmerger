import os
import logging
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeAudio
from video_processor import VideoProcessor
import asyncio

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get credentials from environment
API_ID = int(os.getenv('API_ID', '24663402'))
API_HASH = os.getenv('API_HASH', '3ca4ba0a56c360004a0048d51d385529')
BOT_TOKEN = os.getenv('BOT_TOKEN', '7555240264:AAHeRCnbGIjGMEq8To1Cx74vICy3Qf4jiZY')

class VideoMergerBot:
    def __init__(self):
        self.client = TelegramClient('bot_session', API_ID, API_HASH)
        self.processor = VideoProcessor()
        self.user_data = {}
        
    async def start(self):
        """Start the bot"""
        await self.client.start(bot_token=BOT_TOKEN)
        logger.info("✅ Bot started successfully with MTProto API!")
        logger.info(f"✅ Supporting files up to 2GB!")
        
        # Register handlers
        self.client.add_event_handler(self.start_command, events.NewMessage(pattern='/start'))
        self.client.add_event_handler(self.help_command, events.NewMessage(pattern='/help'))
        self.client.add_event_handler(self.tools_command, events.NewMessage(pattern='/tools'))
        self.client.add_event_handler(self.about_command, events.NewMessage(pattern='/about'))
        self.client.add_event_handler(self.cancel_command, events.NewMessage(pattern='/cancel'))
        self.client.add_event_handler(self.button_callback, events.CallbackQuery())
        self.client.add_event_handler(self.handle_media, events.NewMessage(func=lambda e: e.media))
        
        logger.info("✅ All handlers registered")
        
    async def start_command(self, event):
        """Handle /start command"""
        welcome_message = (
            "🎬 **Welcome to Video Tools Bot!**\n\n"
            "I can help you with:\n"
            "• Merge multiple videos\n"
            "• Add audio to videos\n"
            "• Add subtitles to videos\n"
            "• Extract audio from videos\n\n"
            "✅ **Max file size: 2GB per file** (using MTProto API)\n\n"
            "Use /tools to get started!\n"
            "Use /help for more information."
        )
        await event.respond(welcome_message)
        
    async def help_command(self, event):
        """Handle /help command"""
        help_text = (
            "📚 **Available Commands:**\n\n"
            "/start - Start the bot\n"
            "/tools - Show all available tools\n"
            "/help - Show this help message\n"
            "/cancel - Cancel current operation\n"
            "/about - About this bot\n\n"
            "💡 **How to use:**\n"
            "1. Click /tools\n"
            "2. Select a feature\n"
            "3. Send your files\n"
            "4. Wait for processing\n"
            "5. Download your result!\n\n"
            "✅ **File Size Limit:**\n"
            "Maximum file size: 2GB per file (using MTProto API)"
        )
        await event.respond(help_text)
        
    async def tools_command(self, event):
        """Handle /tools command"""
        buttons = [
            [Button.inline("🎬 Video + Video", b"video_video")],
            [Button.inline("🔊 Video + Audio", b"video_audio")],
            [Button.inline("📝 Video + Subtitle", b"video_subtitle")],
            [Button.inline("🎵 Audio Extractor", b"audio_extract")],
        ]
        await event.respond("🛠️ **Select a tool:**", buttons=buttons)
        
    async def about_command(self, event):
        """Handle /about command"""
        about_text = (
            "ℹ️ **About Video Tools Bot**\n\n"
            "Version: 2.0.0 (MTProto)\n"
            "Powered by FFmpeg + Telethon\n\n"
            "✅ Supports files up to 2GB!\n"
            "✅ Fast downloads with progress tracking\n"
            "✅ High quality video processing\n\n"
            "Made with ❤️ using Python + Telethon"
        )
        await event.respond(about_text)
        
    async def cancel_command(self, event):
        """Handle /cancel command"""
        user_id = event.sender_id
        
        if user_id in self.user_data:
            files = self.user_data[user_id].get('files', [])
            self.cleanup_files(files)
            del self.user_data[user_id]
            await event.respond("❌ Operation cancelled!")
        else:
            await event.respond("No active operation to cancel.")
            
    async def button_callback(self, event):
        """Handle button callbacks"""
        user_id = event.sender_id
        data = event.data.decode('utf-8')
        
        # Handle process/add more buttons
        if data == 'process_now':
            await event.edit("🔄 Processing your files...")
            await self.process_files_internal(user_id, event)
            return
        elif data == 'add_more':
            await event.edit("📹 Send more videos to merge!")
            return
        
        # Initialize user data for tool selection
        self.user_data[user_id] = {
            'mode': data,
            'files': []
        }
        
        # Send instructions based on selected mode
        instructions = {
            'video_video': "📹 **Video + Video Merger**\n\nSend me 2 or more videos to merge them into one.\n\n✅ Max file size: 2GB per file\n\nUse /cancel to stop.",
            'video_audio': "🔊 **Video + Audio Merger**\n\nSend me:\n1. A video file\n2. An audio file\n\nI'll replace the video's audio.\n\n✅ Max file size: 2GB per file\n\nUse /cancel to stop.",
            'video_subtitle': "📝 **Video + Subtitle**\n\nSend me:\n1. A video file\n2. A subtitle file (.srt)\n\nI'll add subtitles to your video.\n\n✅ Max file size: 2GB per file\n\nUse /cancel to stop.",
            'audio_extract': "🎵 **Audio Extractor**\n\nSend me a video file and I'll extract the audio for you.\n\n✅ Max file size: 2GB per file\n\nUse /cancel to stop."
        }
        
        await event.edit(instructions[data])
        
    async def handle_media(self, event):
        """Handle incoming media files"""
        user_id = event.sender_id
        
        if user_id not in self.user_data:
            await event.respond("Please select a tool first using /tools")
            return
        
        mode = self.user_data[user_id]['mode']
        
        try:
            # Get file info
            media = event.media
            file_size = 0
            file_name = None
            
            if hasattr(media, 'document'):
                file_size = media.document.size
                # Get filename from attributes
                for attr in media.document.attributes:
                    if hasattr(attr, 'file_name'):
                        file_name = attr.file_name
                        break
                if not file_name:
                    file_name = f"file_{len(self.user_data[user_id]['files'])}_{media.document.id}"
            elif hasattr(media, 'photo'):
                await event.respond("❌ Please send videos/audio as files, not photos!")
                return
            else:
                await event.respond("❌ Unsupported file type!")
                return
            
            # Check file size (2GB = 2147483648 bytes)
            MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB in bytes
            if file_size > MAX_FILE_SIZE:
                size_mb = file_size / (1024 * 1024)
                await event.respond(
                    f"❌ File too large!\n\n"
                    f"Your file: {size_mb:.1f} MB\n"
                    f"Maximum allowed: 2048 MB (2GB)\n\n"
                    f"Please send a smaller file."
                )
                return
            
            size_mb = file_size / (1024 * 1024)
            status_msg = await event.respond(
                f"📦 File: {file_name}\n"
                f"📊 Size: {size_mb:.1f} MB\n"
                f"⬇️ Starting download..."
            )
            
            # Create downloads directory
            os.makedirs('downloads', exist_ok=True)
            file_path = os.path.join('downloads', file_name)
            
            last_progress = [0]
            last_update_time = [asyncio.get_event_loop().time()]
            
            def progress_callback(current, total):
                percent = int((current / total) * 100)
                current_time = asyncio.get_event_loop().time()
                
                # Update every 5% or every 2 seconds
                if percent >= last_progress[0] + 5 or (current_time - last_update_time[0]) >= 2:
                    last_progress[0] = percent
                    last_update_time[0] = current_time
                    
                    downloaded_mb = current / (1024 * 1024)
                    speed_mbps = (current / (1024 * 1024)) / max(1, current_time - last_update_time[0])
                    
                    bar_length = 20
                    filled = int(bar_length * percent / 100)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    
                    asyncio.create_task(status_msg.edit(
                        f"📦 File: {file_name}\n"
                        f"📊 Size: {size_mb:.1f} MB\n"
                        f"⬇️ Downloading: {percent}%\n"
                        f"{bar}\n"
                        f"📥 {downloaded_mb:.1f} / {size_mb:.1f} MB"
                    ))
            
            await self.client.download_media(
                event.message,
                file=file_path,
                progress_callback=progress_callback
            )
            
            self.user_data[user_id]['files'].append(file_path)
            
            # Update status
            await status_msg.edit(
                f"✅ Downloaded successfully!\n"
                f"📁 File {len(self.user_data[user_id]['files'])}: {file_name}\n"
                f"📊 Size: {size_mb:.1f} MB"
            )
            
            # Check if we have enough files to process
            should_process = False
            
            if mode == 'audio_extract' and len(self.user_data[user_id]['files']) >= 1:
                should_process = True
            elif mode == 'video_video' and len(self.user_data[user_id]['files']) >= 2:
                should_process = True
            elif mode == 'video_audio' and len(self.user_data[user_id]['files']) >= 2:
                should_process = True
            elif mode == 'video_subtitle' and len(self.user_data[user_id]['files']) >= 2:
                should_process = True
            
            if should_process:
                # Ask user if they want to process or add more files
                if mode == 'video_video':
                    buttons = [
                        [Button.inline("✅ Merge Now", b"process_now")],
                        [Button.inline("➕ Add More Videos", b"add_more")],
                    ]
                    await event.respond(
                        f"✅ Ready to merge {len(self.user_data[user_id]['files'])} videos!\n\n"
                        "What would you like to do?",
                        buttons=buttons
                    )
                else:
                    await self.process_files(event, user_id)
        
        except Exception as e:
            logger.error(f"Error downloading file: {e}", exc_info=True)
            await event.respond(f"❌ Error downloading file: {str(e)}")
            
    async def process_files(self, event, user_id):
        """Process files based on mode"""
        status_msg = await event.respond("🔄 Starting processing...")
        await self.process_files_internal(user_id, status_msg)
        
    async def process_files_internal(self, user_id, status_msg_event):
        """Internal processing logic"""
        try:
            mode = self.user_data[user_id]['mode']
            files = self.user_data[user_id]['files']
            
            # Create output directory
            os.makedirs('output', exist_ok=True)
            
            output_file = None
            
            if mode == 'video_video':
                if hasattr(status_msg_event, 'edit'):
                    await status_msg_event.edit(
                        "🔄 Merging Videos\n"
                        f"📹 Files: {len(files)} videos\n"
                        f"⏳ Starting merge process...\n\n"
                        "This may take several minutes depending on file size."
                    )
                output_file = await self.processor.merge_videos(files, status_msg_event)
                caption = f"✅ Successfully merged {len(files)} videos into one!"
                
            elif mode == 'video_audio':
                if hasattr(status_msg_event, 'edit'):
                    await status_msg_event.edit(
                        "🔄 Adding Audio to Video\n"
                        "🔊 Combining video and audio streams...\n"
                        "⏳ Processing..."
                    )
                output_file = await self.processor.merge_video_audio(files[0], files[1], status_msg_event)
                caption = "✅ Audio added to video successfully!"
                
            elif mode == 'video_subtitle':
                if hasattr(status_msg_event, 'edit'):
                    await status_msg_event.edit(
                        "🔄 Adding Subtitles\n"
                        "📝 Burning subtitles into video...\n"
                        "⏳ Processing..."
                    )
                output_file = await self.processor.add_subtitles(files[0], files[1], status_msg_event)
                caption = "✅ Subtitles burned into video successfully!"
                
            elif mode == 'audio_extract':
                if hasattr(status_msg_event, 'edit'):
                    await status_msg_event.edit(
                        "🔄 Extracting Audio\n"
                        "🎵 Extracting audio stream from video...\n"
                        "⏳ Processing..."
                    )
                output_file = await self.processor.extract_audio(files[0], status_msg_event)
                caption = "✅ Audio extracted successfully!"
            
            if output_file and os.path.exists(output_file):
                output_size = os.path.getsize(output_file)
                output_size_mb = output_size / (1024 * 1024)
                
                if hasattr(status_msg_event, 'edit'):
                    await status_msg_event.edit(
                        f"✅ Processing Complete!\n"
                        f"📦 Output: {output_size_mb:.1f} MB\n"
                        f"⬆️ Starting upload to Telegram..."
                    )
                
                last_progress = [0]
                last_update_time = [asyncio.get_event_loop().time()]
                
                def upload_progress(current, total):
                    percent = int((current / total) * 100)
                    current_time = asyncio.get_event_loop().time()
                    
                    # Update every 5% or every 2 seconds
                    if percent >= last_progress[0] + 5 or (current_time - last_update_time[0]) >= 2:
                        last_progress[0] = percent
                        last_update_time[0] = current_time
                        
                        uploaded_mb = current / (1024 * 1024)
                        bar_length = 20
                        filled = int(bar_length * percent / 100)
                        bar = '█' * filled + '░' * (bar_length - filled)
                        
                        asyncio.create_task(status_msg_event.edit(
                            f"✅ Processing Complete!\n"
                            f"📦 Output: {output_size_mb:.1f} MB\n"
                            f"⬆️ Uploading: {percent}%\n"
                            f"{bar}\n"
                            f"📤 {uploaded_mb:.1f} / {output_size_mb:.1f} MB"
                        ))
                
                # Send the processed file
                if mode == 'audio_extract':
                    await self.client.send_file(
                        status_msg_event.chat_id,
                        output_file,
                        caption=caption,
                        progress_callback=upload_progress,
                        attributes=[DocumentAttributeAudio(
                            duration=0,
                            title=os.path.basename(output_file)
                        )]
                    )
                else:
                    await self.client.send_file(
                        status_msg_event.chat_id,
                        output_file,
                        caption=caption,
                        progress_callback=upload_progress,
                        supports_streaming=True
                    )
                
                if hasattr(status_msg_event, 'edit'):
                    await status_msg_event.edit(
                        f"✅ All Done!\n\n"
                        f"📥 Your processed file has been uploaded above.\n"
                        f"📊 Final size: {output_size_mb:.1f} MB"
                    )
                
                # Cleanup
                self.cleanup_files(files, output_file)
                del self.user_data[user_id]
            else:
                if hasattr(status_msg_event, 'edit'):
                    await status_msg_event.edit(
                        "❌ Processing Failed!\n\n"
                        "The output file was not created. Please try again or contact support."
                    )
                else:
                    await status_msg_event.respond("❌ Processing failed! Please try again.")
        
        except Exception as e:
            logger.error(f"Error processing files: {e}", exc_info=True)
            error_msg = str(e)
            # Truncate very long error messages
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            
            if hasattr(status_msg_event, 'respond'):
                await status_msg_event.respond(
                    f"❌ Error During Processing\n\n"
                    f"Error: {error_msg}\n\n"
                    f"Please try again or use /help for support."
                )
            
            # Cleanup on error
            if user_id in self.user_data:
                self.cleanup_files(self.user_data[user_id]['files'])
                del self.user_data[user_id]
    
    def cleanup_files(self, input_files, output_file=None):
        """Clean up temporary files"""
        for file_path in input_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up: {file_path}")
            except Exception as e:
                logger.error(f"Error removing file {file_path}: {e}")
        
        if output_file and os.path.exists(output_file):
            try:
                os.remove(output_file)
                logger.info(f"Cleaned up output: {output_file}")
            except Exception as e:
                logger.error(f"Error removing output file: {e}")
    
    async def run(self):
        """Run the bot"""
        await self.start()
        logger.info("🤖 Bot is running... Press Ctrl+C to stop")
        await self.client.run_until_disconnected()

if __name__ == '__main__':
    bot = VideoMergerBot()
    asyncio.run(bot.run())
