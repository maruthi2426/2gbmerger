# Telegram Video Tools Bot - Deployment Guide

## 🎯 2GB File Support with MTProto API

This bot now uses **Telethon (MTProto)** instead of the standard Bot API, which allows:
- ✅ Files up to **2GB** (vs 20MB with Bot API)
- ✅ Real-time download/upload progress tracking
- ✅ Faster file transfers
- ✅ More reliable for large files

## 📋 Requirements

1. **Telegram Bot Token** - Get from @BotFather
2. **Telegram API ID & API Hash** - Get from https://my.telegram.org/apps
3. **Render Standard Plan** - Minimum 2GB RAM required for processing large video files

## 🚀 Deploy to Render

### Step 1: Fork/Clone Repository
\`\`\`bash
git clone <your-repo-url>
cd telegram-video-bot
\`\`\`

### Step 2: Update Environment Variables

Edit `render.yaml` with your credentials:
\`\`\`yaml
envVars:
  - key: BOT_TOKEN
    value: YOUR_BOT_TOKEN_HERE
  - key: API_ID
    value: YOUR_API_ID_HERE
  - key: API_HASH
    value: YOUR_API_HASH_HERE
\`\`\`

Or set them in Render Dashboard:
- Go to your service → Environment
- Add the three environment variables above

### Step 3: Deploy

**Important:** This bot requires Render's **Standard Plan** or higher (minimum 2GB RAM) to process large video files. The free tier (512MB RAM) is insufficient and will cause out-of-memory errors.

Push to GitHub and Render will auto-deploy:
\`\`\`bash
git add .
git commit -m "Deploy video bot"
git push origin main
\`\`\`

Or use Render's manual deploy:
1. Go to Render Dashboard
2. New → Background Worker (not Web Service!)
3. Connect your repository
4. Select **Standard Plan** or higher
5. Render will detect `render.yaml` automatically

### Step 4: Verify Deployment

Check the logs in Render Dashboard:
\`\`\`
✅ Bot started successfully with MTProto API!
✅ Supporting files up to 2GB!
✅ All handlers registered
🤖 Bot is running...
\`\`\`

## 🧪 Test Your Bot

1. Open Telegram and search for your bot
2. Send `/start` - You should see the welcome message
3. Send `/tools` - Select a tool
4. Send a large video file (up to 2GB)
5. Watch the progress bar as it downloads and processes

## 🔧 Features

- **Video + Video Merger** - Merge multiple videos
- **Video + Audio** - Replace video audio track
- **Video + Subtitle** - Burn subtitles into video
- **Audio Extractor** - Extract audio from video

## ⚙️ Technical Details

### Why Telethon?

Standard Bot API has a **20MB file size limit**. To handle files up to 2GB, we need:
- MTProto API (Telegram's native protocol)
- User-mode authentication (API_ID + API_HASH)
- Telethon library for Python

### Architecture

\`\`\`
User → Telegram → Telethon Bot → FFmpeg → Output → Upload back
\`\`\`

### File Processing

1. Download with progress tracking (Telethon)
2. Process with FFmpeg (no re-encoding when possible)
3. Upload with progress tracking (Telethon)
4. Auto-cleanup temporary files

## 🐛 Troubleshooting

### Bot not responding?
- Check logs in Render Dashboard
- Verify all 3 environment variables are set correctly
- Ensure API_ID is a number (no quotes)
- Ensure API_HASH is the full string

### "File too big" error?
- Max size is 2GB per file
- Check if you're sending the file as a document (not compressed)

### FFmpeg errors?
- Check that FFmpeg is installed in Docker (it is by default)
- Check file formats are supported (MP4, MKV, AVI, etc.)

### Session file issues?
- The bot creates a `bot_session.session` file
- This is normal and contains authentication data
- Don't delete it or the bot will need to re-authenticate

### Out of Memory Error?
- **Cause:** Free tier has only 512MB RAM, insufficient for video processing
- **Solution:** Upgrade to Standard Plan (2GB RAM) or higher
- Check render.yaml has `plan: standard` set
- Video processing requires significant memory for FFmpeg operations

### FFmpeg "Invalid data" error?
- **Cause:** Video file paths not properly escaped in concat list
- **Solution:** Already fixed in video_processor.py with proper path escaping
- Ensure video files are complete downloads (not corrupted)
- Try processing with smaller videos first to verify setup

### "Port scan timeout" warning?
- **Cause:** Using "web" service type instead of "worker"
- **Solution:** render.yaml should have `type: worker` (not `type: web`)
- Telegram bots don't need HTTP ports
- This warning doesn't affect bot functionality if type is "worker"

## 📊 Monitoring

Watch the logs for:
- `✅ Bot started successfully` - Bot is running
- `📦 File size: X MB` - File received
- `⬇️ Downloading: X%` - Download progress
- `🔄 Processing...` - FFmpeg working
- `⬆️ Uploading: X%` - Upload progress
- `✅ Done!` - Task completed

## 🔒 Security Notes

- Keep your BOT_TOKEN secret
- Keep your API_HASH secret
- Don't commit credentials to public repositories
- Use environment variables in production

## 💡 Tips

1. Video merging uses re-encoding for compatibility across different formats
2. Subtitle burning is slowest (requires full re-encoding)
3. Clean up old files to save disk space
4. Monitor Render's disk usage and memory consumption
5. Test with small files first before processing large 2GB files

## 📝 Key Fixes Applied

### Fixed Issues:
1. **File path escaping** - Properly escape single quotes and backslashes in FFmpeg concat
2. **Memory allocation** - Changed to Standard plan with 2GB RAM
3. **Service type** - Changed from "web" to "worker" (no HTTP port needed)
4. **Video encoding** - Using ultrafast preset to reduce processing time and memory
5. **Error handling** - Better logging and file verification

### Processing Optimizations:
- Using `ultrafast` preset for faster encoding
- CRF 23 for good quality/size balance
- AAC audio at 128k bitrate
- Fast start enabled for web playback
- Comprehensive error logging for debugging

## 🆘 Support

If you encounter issues:
1. Check Render logs for errors
2. Verify environment variables
3. Test with small files first
4. Ensure your Telegram API credentials are valid

## 📝 License

This bot is provided as-is for educational purposes.
