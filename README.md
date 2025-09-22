# LINE Drive Bot — Robust Build (Render Free)

> แก้ปัญหา `File not found` ทั้งกรณี **ไม่เจอไฟล์ Service Account** และ **Google Drive: File not found {folderId}**

## วิธีใช้
1. **แนะนำ**: ใช้ Secret File ใน Render
   - Environment → **Add Secret File**
     - Path: `/etc/secrets/service-account.json`
     - Content: วาง JSON ของ Service Account
   - ตั้ง env: `GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/service-account.json`

2. **ทางเลือก (fallback)**: ใช้ env var แทนไฟล์
   - ใส่ env `GOOGLE_SERVICE_ACCOUNT_JSON` เป็น **raw JSON** หรือ **base64 ของ JSON**
   - โค้ดจะเขียนไฟล์ชั่วคราวที่ `/tmp/sa.json` ให้อัตโนมัติ

> จะใช้วิธีใดวิธีหนึ่งก็พอ — ถ้า Secret File ไม่มี โค้ดจะพยายามอ่านจาก `GOOGLE_SERVICE_ACCOUNT_JSON` ให้อัตโนมัติ

## Endpoints
- `GET /` → health
- `GET /debug/env` → ดูสถานะ env และไฟล์ SA (ไม่โชว์ secret)
- `GET /debug/sa` → ดูอีเมลของ Service Account
- `GET /debug/drive/folder?folderId=<ID>` → ตรวจสิทธิ์/การเข้าถึงโฟลเดอร์
- `POST /drive/ping?folderId=<ID>` → สร้างไฟล์ทดสอบลง Drive

## ขั้นตอนตรวจแบบเร็ว (แก้ไฟล์ไม่ขึ้น Drive)
1) เปิด `/debug/env` → `sa_file_exists` ต้องเป็น **true**  
2) เปิด `/debug/sa` → ได้ `service_account_email` → ไปที่ Google Drive **แชร์โฟลเดอร์ปลายทาง** ให้เมลนี้เป็น **Editor**  
3) เปิด `/debug/drive/folder?folderId=<โฟลเดอร์ID>` → ต้อง **ok: true**  
4) `POST /drive/ping?folderId=<โฟลเดอร์ID>` → ดูว่าได้ 200 พร้อมลิงก์ไฟล์  
5) ทดสอบส่งรูป/ไฟล์ผ่าน LINE

> ถ้า error ในข้อ 3 เป็น `File not found: <id>` → **ID ผิดหรือยังไม่ได้แชร์**  
> ถ้า error ในข้อ 1 ว่า `sa_file_exists=false` → **ยังไม่มี Secret File และไม่มี GOOGLE_SERVICE_ACCOUNT_JSON**

## Shared Drive
รองรับแล้ว (`supportsAllDrives=True`). โฟลเดอร์ใน Shared Drive ก็ต้องแชร์สิทธิ์ SA เช่นกัน

## Optional: แชร์ไฟล์แบบ Anyone-with-link
ตั้ง `DRIVE_SHARE_ANYONE=true` เพื่อให้ไฟล์ดูได้ผ่านลิงก์ (ไม่ต้องล็อกอิน)
