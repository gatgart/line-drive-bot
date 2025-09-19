# LINE Drive Bot — Python/Flask → Google Drive (Render Free)

รับรูป/วิดีโอ/เสียง/ไฟล์จากผู้ใช้ LINE แล้วอัปโหลดเข้า Google Drive อัตโนมัติ

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/USERNAME/line-drive-bot)

## Quick Start
1. ใส่โค้ดนี้ใน GitHub ของคุณเอง แล้วแก้ลิงก์ `USERNAME` ในปุ่มข้างบนให้ตรง
2. Render จะอ่าน `render.yaml` และสร้าง Web Service ให้อัตโนมัติ
3. ตั้งค่า Environment:
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `GDRIVE_FOLDER_ID`
   - `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/service-account.json`
4. เพิ่ม **Secret File** ที่ Render:
   - Path: `/etc/secrets/service-account.json`
   - Content: วางเนื้อหา JSON ของ Service Account
5. ตั้ง **Webhook URL** ใน LINE Console เป็น `https://<your-app>.onrender.com/webhook` แล้ว Verify

## Troubleshooting: "file not found"
- **Service Account JSON ไม่พบ**  
  - ตรวจว่า *Secret File* ถูกสร้างแล้ว และ *Path* ตรงกับ `GOOGLE_APPLICATION_CREDENTIALS`
  - ชื่อคีย์ต้องสะกดถูกต้อง: `GOOGLE_APPLICATION_CREDENTIALS` (ไม่มี S เติม)
  - ถ้า log มี `FileNotFoundError: '/etc/secrets/service-account.json'`: แปลว่า Secret File ยังไม่ถูกเพิ่ม หรือ path ผิด
- **requirements.txt not found**  
  - ให้แน่ใจว่าไฟล์อยู่ที่ root ของ repo และชื่อถูกต้องตาม `render.yaml`
- **ModuleNotFoundError: No module named 'app'**  
  - ให้ไฟล์ entrypoint ชื่อ `app.py` อยู่ที่ root และ `startCommand` เป็น `gunicorn app:app`
- **LINE Verify 404**  
  - Route ถูกคือ `POST /webhook` (LINE ใช้ POST อยู่แล้ว) — ตรวจว่า service up และ URL ถูก

## Lic: MIT
