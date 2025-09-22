import io
import os
import sys
import json
import base64
import mimetypes
import logging
import requests
from datetime import datetime
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
FOLDER_ID_ENV  = (os.getenv("GDRIVE_FOLDER_ID") or "").strip()
SA_PATH_ENV    = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SA_JSON_ENV    = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
SHARE_ANYONE   = (os.getenv("DRIVE_SHARE_ANYONE", "false").lower() == "true")

line_bot_api = LineBotApi(CHANNEL_TOKEN) if CHANNEL_TOKEN else None
handler = WebhookHandler(CHANNEL_SECRET) if CHANNEL_SECRET else None

def _write_sa_from_env_to_tmp():
    if not SA_JSON_ENV:
        return None
    # Try raw JSON first
    try:
        data = json.loads(SA_JSON_ENV)
    except Exception:
        # Try base64
        try:
            decoded = base64.b64decode(SA_JSON_ENV).decode("utf-8")
            data = json.loads(decoded)
        except Exception as e:
            app.logger.error("Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: %s", e)
            return None
    path = "/tmp/sa.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path

def resolve_sa_path():
    # 1) Secret File path
    if SA_PATH_ENV and os.path.exists(SA_PATH_ENV):
        return SA_PATH_ENV
    # 2) Env JSON fallback
    fallback = _write_sa_from_env_to_tmp()
    if fallback and os.path.exists(fallback):
        return fallback
    return None

def get_drive_service():
    sa_path = resolve_sa_path()
    if not sa_path:
        raise FileNotFoundError("Service account credentials not found. "
                                "Add Secret File at /etc/secrets/service-account.json "
                                "or set GOOGLE_SERVICE_ACCOUNT_JSON.")
    creds = service_account.Credentials.from_service_account_file(
        sa_path, scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def get_sa_email():
    sa_path = resolve_sa_path()
    if not sa_path:
        return None
    with open(sa_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("client_email")

def ensure_folder_access(drive, folder_id):
    return drive.files().get(
        fileId=folder_id,
        fields="id, name, driveId, parents",
        supportsAllDrives=True
    ).execute()

@app.get("/")
def health():
    return jsonify({"ok": True, "service": "line-drive-bot"}), 200

@app.get("/debug/env")
def debug_env():
    sa_path = resolve_sa_path()
    return jsonify({
        "has_LINE_CHANNEL_SECRET": bool(CHANNEL_SECRET),
        "has_LINE_CHANNEL_ACCESS_TOKEN": bool(CHANNEL_TOKEN),
        "has_GDRIVE_FOLDER_ID": bool(FOLDER_ID_ENV),
        "GOOGLE_APPLICATION_CREDENTIALS": SA_PATH_ENV,
        "has_GOOGLE_SERVICE_ACCOUNT_JSON": bool(SA_JSON_ENV),
        "resolved_sa_path": sa_path,
        "sa_file_exists": bool(sa_path and os.path.exists(sa_path)),
    }), 200

@app.get("/debug/sa")
def debug_sa():
    return jsonify({"service_account_email": get_sa_email()}), 200

@app.get("/debug/drive/folder")
def debug_drive_folder():
    folder_id = request.args.get("folderId") or FOLDER_ID_ENV
    if not folder_id:
        return jsonify({"ok": False, "error": "folderId is required"}), 400
    try:
        drive = get_drive_service()
        meta = drive.files().get(
            fileId=folder_id,
            supportsAllDrives=True,
            fields="id, name, mimeType, shortcutDetails, driveId, parents"
        ).execute()
        return jsonify({"ok": True, "folder": meta}), 200
    except Exception as e:
        app.logger.exception("Folder access failed")
        return jsonify({"ok": False, "error": str(e)}), 500
        
@app.get("/debug/drive/permissions")
def debug_drive_permissions():
    file_id = request.args.get("fileId") or FOLDER_ID_ENV
    if not file_id:
        return jsonify({"ok": False, "error": "fileId is required"}), 400
    try:
        drive = get_drive_service()
        perms = drive.permissions().list(
            fileId=file_id,
            supportsAllDrives=True,
            fields="permissions(id,role,type,emailAddress,domain,allowFileDiscovery,permissionDetails),nextPageToken"
        ).execute()
        return jsonify({"ok": True, **perms}), 200
    except Exception as e:
        app.logger.exception("permissions.list failed")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.get("/debug/drive/folder")
def debug_drive_folder():
    folder_id = request.args.get("folderId") or FOLDER_ID_ENV
    if not folder_id:
        return jsonify({"ok": False, "error": "folderId is required"}), 400
    try:
        drive = get_drive_service()
        meta = ensure_folder_access(drive, folder_id)
        return jsonify({"ok": True, "folder": meta}), 200
    except Exception as e:
        app.logger.exception("Folder access failed")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/drive/ping")
def drive_ping():
    folder_id = request.args.get("folderId") or FOLDER_ID_ENV or None
    try:
        drive = get_drive_service()
        if folder_id:
            ensure_folder_access(drive, folder_id)
        # create test text file
        content = io.BytesIO(f"ping {datetime.utcnow().isoformat()}Z".encode("utf-8"))
        media = MediaIoBaseUpload(content, mimetype="text/plain", resumable=False)
        meta = {"name": f"ping-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt"}
        if folder_id:
            meta["parents"] = [folder_id]
        created = drive.files().create(
            body=meta, media_body=media,
            fields="id, name, webViewLink, parents, driveId",
            supportsAllDrives=True
        ).execute()
        if SHARE_ANYONE:
            try:
                drive.permissions().create(
                    fileId=created["id"],
                    body={"role": "reader", "type": "anyone"},
                    supportsAllDrives=True
                ).execute()
            except Exception as pe:
                app.logger.warning("Set anyone permission failed: %s", pe)
        return jsonify({"ok": True, "created": created}), 200
    except Exception as e:
        app.logger.exception("Drive ping failed")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/webhook")
def webhook():
    if handler is None:
        abort(500, description="LINE handler not configured")
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    app.logger.info("Webhook received: %s", body[:256])
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
        folder_id = FOLDER_ID_ENV or None
        if folder_id:
            ensure_folder_access(drive, folder_id)

        meta = {"name": filename}
        if folder_id:
            meta["parents"] = [folder_id]

        created = drive.files().create(
            body=meta,
            media_body=media,
            fields="id, name, webViewLink, parents, driveId",
            supportsAllDrives=True
        ).execute()

        if SHARE_ANYONE:
            try:
                drive.permissions().create(
                    fileId=created["id"],
                    body={"role": "reader", "type": "anyone"},
                    supportsAllDrives=True
                ).execute()
            except Exception as pe:
                app.logger.warning("Set anyone permission failed: %s", pe)

        view_link = created.get("webViewLink") or "(private)"
        reply_text = f"อัปโหลดสำเร็จ ✅\nชื่อไฟล์: {created.get('name')}\nไฟล์ ID: {created.get('id')}\nเปิดดู: {view_link}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        app.logger.info("Uploaded file: %s (%s)", created.get("name"), created.get("id"))

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
