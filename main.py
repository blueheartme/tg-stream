import os
import asyncio
from pyrogram import Client, filters
from aiohttp import web

# تنظیمات
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL")) # کانال آرشیو
PORT = int(os.environ.get("PORT", 8000))

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
routes = web.RouteTableDef()

@routes.get("/")
async def root(request):
    return web.Response(text="Bot Running")

@routes.get("/dl/{message_id}/{fn}")
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['message_id'])
        msg = await app.get_messages(BIN_CHANNEL, msg_id)
        
        if not msg or not msg.media:
            return web.Response(status=404, text="404 Not Found")

        file_size = 0
        mime = "application/octet-stream"
        
        # استخراج حجم و نوع فایل
        media = getattr(msg, msg.media.value) if msg.media else None
        if media:
            file_size = getattr(media, "file_size", 0)
            mime = getattr(media, "mime_type", mime)

        headers = {
            "Content-Type": mime,
            "Content-Length": str(file_size),
            "Content-Disposition": f'attachment; filename="{request.match_info["fn"]}"'
        }
        
        response = web.StreamResponse(headers=headers)
        await response.prepare(request)
        
        async for chunk in app.stream_media(msg):
            await response.write(chunk)
            
        return response
    except Exception as e:
        print(e)
        return web.Response(status=500)

@app.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def on_file(c, m):
    # فایل را به کانال آرشیو بفرست تا پاک نشود و آیدی ثابت بگیرد
    log = await m.forward(BIN_CHANNEL)
    
    # نام فایل را پیدا کن
    fname = "file"
    if m.document: fname = m.document.file_name
    elif m.video: fname = f"video_{m.id}.mp4"
    elif m.audio: fname = m.audio.file_name or "audio.mp3"
    
    # ساخت لینک
    base_url = os.environ.get("KOYEB_PUBLIC_URL", "")
    # اگر متغیر کویب خالی بود از آدرس دستی استفاده کن
    if not base_url:
         base_url = os.environ.get("APP_URL", "http://localhost:8000")
         
    dl_link = f"{base_url}/dl/{log.id}/{fname}"
    
    await m.reply_text(f"🔗 لینک دانلود مستقیم:\n\n{dl_link}", quote=True)

async def main():
    await app.start()
    print("Pyrogram Client Started")
    
    server = web.Application()
    server.add_routes(routes)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Web Server on Port {PORT}")
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
