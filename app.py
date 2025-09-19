import io
import mimetypes
import os
import sys
import logging
import requests
from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, VideoMessage, AudioMessage,
    FileMessage, TextSendMessage
)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

load_dotenv()

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_TOKEN  = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
FOLDER_ID      = os.getenv("GDRIVE_FOLDER_ID", "").strip()
SA_PATH        = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not CHANNEL_SECRET or not CHANNEL_TOKEN:
    app.logger.warning("LINE env vars missing.")
if not FOLDER_ID:
    app.logger.warning("GDRIVE_FOLDER_ID missing.")
if not SA_PATH or not os.path.exists(SA_PATH):
    app.logger.warning("Service account JSON not found at GOOGLE_APPLICATION_CREDENTIALS: %s", SA_PATH)

line_bot_api = LineBotApi(CHANNEL_TOKEN) if CHANNEL_TOKEN else None
handler = WebhookHandler(CHANNEL_SECRET) if CHANNEL_SECRET else None

def get_drive_service():
    if not SA_PATH or not os.path.exists(SA_PATH):
        raise FileNotFoundError(f"Service account file not found: {SA_PATH}. Check GOOGLE_APPLICATION_CREDENTIALS and Secret File path.")
    creds = service_account.Credentials.from_service_account_file(
        SA_PATH,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)

@app.get("/")
def health():
    return jsonify({"ok": True, "service": "line-drive-bot"}), 200

@app.post("/webhook")
def webhook():
    if handler is None:
        abort(500, description="LINE handler not configured")
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.exception("Invalid signature")
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage, FileMessage, TextMessage))  # type: ignore[arg-type]
def handle_message(event):
    msg = event.message

    if isinstance(msg, TextMessage):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="ส่งรูป/วิดีโอ/เสียง/ไฟล์มาได้เลย ผมจะอัปโหลดขึ้น Google Drive ให้อัตโนมัติครับ")
        )
        return

    try:
        content_url = f"https://api-data.line.me/v2/bot/message/{msg.id}/content"
        r = requests.get(
            content_url,
            headers={"Authorization": f"Bearer {CHANNEL_TOKEN}"},
            stream=True,
            timeout=60
        )
        r.raise_for_status()

        filename = getattr(msg, "file_name", None) or f"{msg.type}-{msg.id}"
        content_type = r.headers.get("Content-Type")
        if "." not in filename and content_type:
            ext = (mimetypes.guess_extension(content_type.split(";")[0].strip()) or "").replace(".jpe", ".jpg")
            filename = f"{filename}{ext}"

        data = io.BytesIO(r.content)
        media = MediaIoBaseUpload(
            data,
            mimetype=content_type or "application/octet-stream",
            resumable=False
        )

        drive = get_drive_service()
        file_meta = {"name": filename}
        if FOLDER_ID:
            file_meta["parents"] = [FOLDER_ID]

        created = drive.files().create(
            body=file_meta,
            media_body=media,
            fields="id, name, webViewLink, webContentLink"
        ).execute()

        view_link = created.get("webViewLink") or "(private)"
        reply_text = f"อัปโหลดสำเร็จ ✅\nชื่อไฟล์: {created.get('name')}\nไฟล์ ID: {created.get('id')}\nเปิดดู: {view_link}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    except Exception as e:
        app.logger.exception("Upload failed")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"อัปโหลดไม่สำเร็จ ❌\n{e}")
            )
        except Exception:
            app.logger.exception("Failed to reply error to user")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
