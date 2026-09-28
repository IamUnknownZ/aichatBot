# New Machine Setup

เป้าหมาย: ย้าย project ไปเครื่องใหม่โดยใช้ source, Git history และ Supabase เดิม

## สิ่งที่ archive ต้องมี

ต้องมี:
- source code ทั้งหมด
- `.git/`
- `.env.example` (ตัวอย่างชื่อค่าเท่านั้น; ZIP ไม่รวม secret จริง)
- `real_data/`
- `docs/`
- `db/`
- `tests/`
- `handover/`

ไม่ต้องย้าย:
- `venv/`
- `.venv/`
- `node_modules/`
- `__pycache__/`
- cache/test cache

เหตุผล:
environment binary ไม่ portable ข้ามเครื่อง/OS

## Linux — Quick start

แตก ZIP:

```bash
unzip ai-chat-bot-portable-private.zip
cd ai-chat-bot
```

รัน setup:

```bash
bash handover/setup_new_machine.sh
```

activate:

```bash
source venv/bin/activate
```

run:

```bash
python -m streamlit run app.py
```

## Manual setup

แนะนำ Python 3.11/3.12

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

จากนั้น:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## .env

Portable archive ไม่รวม `.env` เดิมและไม่รวม secret จริง

ให้สร้างไฟล์ใหม่บนเครื่องปลายทาง:

```bash
cp .env.example .env
# แก้ .env ในเครื่องนี้ แล้วกรอก GEMINI_API_KEY และ DATABASE_URL
```

ถ้ามี credential ของ legacy LINE bot ให้ตั้งผ่าน environment variables ตามชื่อที่ระบุใน
source แทนการ hardcode ค่าในไฟล์

ตรวจโดยไม่ print secret:

```bash
python - <<'PY'
from dotenv import load_dotenv
load_dotenv()
from rag.config import Settings
s = Settings.from_env()
print("Gemini:", bool(s.gemini_api_key))
print("Database:", bool(s.database_url))
PY
```

ห้าม copy ค่า secret ลง terminal history ถ้าไม่จำเป็น

## Database

DB คือ remote Supabase PostgreSQL

ถ้า archive ใช้ .env เดิม:
- ไม่ต้องสร้าง DB ใหม่
- ไม่ต้อง re-ingest ถ้า PDF hashes เดิม
- app ควรเห็น vectors เดิมทันที

ตรวจ:

```bash
python - <<'PY'
from dotenv import load_dotenv
load_dotenv()
from rag.config import Settings
import psycopg
s=Settings.from_env()
with psycopg.connect(s.database_url, connect_timeout=10) as conn:
    with conn.cursor() as cur:
        cur.execute("select count(*) from rag_document_chunks")
        print("chunks:", cur.fetchone()[0])
PY
```

expected ล่าสุด: 119

## ถ้า source PDF เปลี่ยน

```bash
python -m scripts.ingest_pdf --force
```

## ถ้าแก้เฉพาะ crop/label

```bash
python -m scripts.ingest_pdf --images-only
```

## Streamlit Cloud

Secrets:
```toml
GEMINI_API_KEY = "..."
DATABASE_URL = "postgresql://..."
```

Production runtime ต้องได้ store:
`postgres-pgvector`

## Git

Archive เก็บ `.git`

ตรวจ:

```bash
git status -sb
git log --oneline -10
git remote -v
```

baseline code ก่อน handover:
- main
- `3bd2363 fix: match curriculum topics to approved source`
- archive อาจมี handover commit เพิ่มจาก baseline นี้

## Windows

สร้าง venv ใหม่:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

ห้าม copy `venv/` จาก Linux ไปใช้ Windows

## Verification checklist

หลังย้าย:
- [ ] Python run ได้
- [ ] requirements install ครบ
- [ ] .env ถูกโหลด
- [ ] Supabase connect ได้
- [ ] pgvector extension มี
- [ ] tests ผ่าน
- [ ] Streamlit เปิด
- [ ] ถาม “การเรียงลำดับข้อมูลคือ”
- [ ] ถาม “selection sort”
- [ ] ถามต่อ “ภาพ”
- [ ] รูปไม่เป็น full A4
- [ ] curriculum list = 6 หัวข้อที่อนุมัติ
