# LINE Drive Bot (Python/Flask) — Upload to Google Drive

รับรูป/วิดีโอ/เสียง/ไฟล์จากผู้ใช้ LINE แล้วอัปโหลดเข้าโฟลเดอร์ Google Drive โดยอัตโนมัติ
รันบน **Render (Free Plan)** ได้

---

## 🚀 Deploy to Render (Blueprint)

> กดปุ่มด้านล่าง (ปรับลิงก์ให้เป็น GitHub repo ของคุณเองก่อน)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/USERNAME/line-drive-bot)

> วิธีใช้งานปุ่ม:
> 1) Fork/อัปโหลด repo นี้ไป GitHub ของคุณ (เปลี่ยน `USERNAME`)  
> 2) คลิกปุ่มด้านบน → เลือกบริการ → Render จะอ่าน `render.yaml` และสร้าง Web Service ให้อัตโนมัติ

---

## 🧱 โครงสร้าง
```
.
├─ app.py
├─ requirements.txt
├─ render.yaml
├─ .env.example
└─ .gitignore
```

## 🔑 สิ่งที่ต้องเตรียม
### LINE Developers
- สร้าง **Messaging API channel**
- เปิด **Use Webhook**
- เก็บ **Channel secret** และ **Channel access token**

### Google Cloud & Drive
- เปิดใช้ **Google Drive API**
- สร้าง **Service Account** และดาวน์โหลด **JSON key**
- ใน Google Drive: สร้างโฟลเดอร์ปลายทาง → **แชร์ให้ Service Account (Editor)**  
- จด **Folder ID** ของโฟลเดอร์ปลายทาง

---

## ⚙️ ตัวแปรแวดล้อม (Environment)
ตั้งค่าที่ Render → *Environment*

- `LINE_CHANNEL_SECRET` = จาก LINE Console
- `LINE_CHANNEL_ACCESS_TOKEN` = จาก LINE Console
- `GDRIVE_FOLDER_ID` = ไอดีโฟลเดอร์ปลายทางใน Google Drive
- `GOOGLE_APPLICATION_CREDENTIALS` = `/etc/secrets/service-account.json`

### Secret File (สำคัญ)
Render → *Environment* → **Add Secret File**  
- **Path**: `/etc/secrets/service-account.json`  
- **Content**: วางเนื้อหาไฟล์ JSON ของ Service Account

> เมื่อบันทึก Render จะรีดีพลอยอัตโนมัติ

---

## 🔌 Webhook URL (LINE)
หลังดีพลอยบน Render แล้วจะได้ URL เช่น  
`https://your-app.onrender.com`

- ตั้ง **Webhook URL** เป็น `https://your-app.onrender.com/webhook`
- กด **Verify** → ควรเป็น Success
- เปิด **Use webhook**

---

## 🧪 ทดสอบใช้งาน
- แอด LINE Bot เป็นเพื่อน
- ส่งรูป/วิดีโอ/เสียง/ไฟล์
- ตรวจใน Google Drive ว่ามีไฟล์เข้าโฟลเดอร์ปลายทาง

---

## 🛠️ ปรับแต่งเพิ่มเติม
- ตั้งสิทธิ์ไฟล์ให้ Anyone with the link: เปิดคอมเมนต์ใน `app.py` ส่วน `permissions().create(...)`
- ตั้งชื่อไฟล์ตามเวลา/ผู้ใช้: ปรับตัวแปร `filename` ใน handler ได้เลย
- รองรับเฉพาะ MIME บางชนิด: เช็ค `content_type` และตัดสินใจก่อนอัปโหลด
- ไฟล์ใหญ่มาก: เปลี่ยน `resumable=True`

---

## 🐞 Troubleshooting
- **InvalidSignatureError**: ตรวจ `LINE_CHANNEL_SECRET` ให้ตรง และ Webhook URL ต้องเป็น HTTPS
- **อัปโหลดไม่เข้าโฟลเดอร์**: ลืมแชร์โฟลเดอร์ให้ Service Account เป็น Editor
- **403 จาก Git push**: ตรวจสิทธิ์ GitHub/รีโมต/ใช้ PAT หรือ SSH
- **Render Sleep (Free Plan)**: บริการจะตื่นเมื่อมี request เข้า (ไม่เสียเงิน)

---

## 📝 License
MIT
