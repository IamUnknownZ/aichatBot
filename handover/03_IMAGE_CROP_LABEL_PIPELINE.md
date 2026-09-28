# Image Crop + Label Pipeline — Current Implementation and Limitations

เอกสารนี้สำคัญที่สุดสำหรับงานต่อ เพราะ visual pipeline ยังไม่ถึงระดับ production-quality

## 1. เป้าหมาย

ต้องการให้ chatbot แสดง “รูป/แผนภาพ/trace ที่เกี่ยวข้อง” จาก PDF จริง

ไม่ต้องการ:
- screenshot ทั้งหน้า A4
- ภาพดำ
- image จากเว็บ
- AI generated visual
- ภาพจากคนละ PDF/คนละหน้า

## 2. Source binding

ทุก image มี:
- source_id = SHA-256 ของ PDF
- source_file
- page_number
- image_index
- sha256 ของภาพ
- metadata
- source_only=true

UI map text hit → image ด้วยคู่:

```
(source_id, page_number)
```

จึงไม่ควรเกิด collision แบบ “หน้า 4 ของ PDF A” ไปหยิบ “หน้า 4 ของ PDF B”

## 3. Image kinds

### embedded_image
ภาพ raster ที่ฝังใน PDF

ดึงจาก:
```python
page.get_images(full=True)
doc.extract_image(xref)
```

filter ปัจจุบัน:
- min_width 180
- min_height 120
- dedupe SHA-256

ปัญหา:
- PDF บางเล่มฝังภาพที่ดำ/เป็น mask/ไม่ใช่ visual ที่ user ควรเห็น
- จึงไม่แสดง raw embedded_image ต่อ user

### figure_crop
ใช้เมื่อมี caption ชัด เช่น:
- รูปที่ 8.2
- Figure 1
- Fig. 2

caption regex:
```
^\s*(รูปที่|figure|fig\.)\s*\d
```

algorithm:
1. อ่าน text blocks
2. หา caption
3. เอา caption y
4. มอง vector drawings ย้อนขึ้นไปไม่เกิน ~280 PDF points
5. candidate ต้องกว้าง >= 120 และสูง >= 45
6. เลือก candidate ที่ area ใหญ่ที่สุด
7. padding 8 points
8. render crop ที่ 2×
9. บันทึก kind=figure_crop
10. label/caption = caption text จริง

ตัวอย่างที่เคยทดสอบ:
Insertion Sort “รูปที่ 8.2”
- crop จากหน้า 6
- ~729×325 px
- ไม่แสดง A4 เต็มหน้า

### trace_crop
เพิ่มเพราะ Selection Sort มี visual แต่ไม่มี caption “รูปที่ …”

algorithm ปัจจุบัน:
1. อ่าน `page.get_drawings()`
2. ทิ้ง rect ที่อยู่ใกล้ header/footer
3. ทิ้ง rect เล็กเกิน
4. ทิ้งเส้น horizontal เกือบเต็มหน้า
5. ต้องมี rect อย่างน้อย 5
6. sort rect ด้วย y/x
7. group ถ้า rect ถัดไปอยู่ห่าง bottom ของ group <= 35 points
8. group ต้องมีอย่างน้อย 5 rect
9. crop bounding union ของ group
10. width >= 180, height >= 25
11. padding x=14, y=18
12. ถ้า crop area > 35% ของหน้า → reject
13. render 2×
14. kind=trace_crop

ผลที่เคย audit:
- Selection Sort textbook หน้า 4 ~553×176
- หน้า 5 ได้หลาย trace
- English PDF Selection Sort หน้า 15 ~545×240

## 4. Label / Caption logic

สำหรับ `figure_crop`:
- ใช้ caption จริงจาก PDF

สำหรับ `trace_crop` ฟังก์ชัน `_trace_caption()` ใช้ priority:

1. `visual_metadata["subtopic"]`
2. `visual_metadata["section"]`
3. scan text line หา regex algorithm:
   Selection / Insertion / Bubble / Shell / Quick / Merge / Heap / Cocktail / Counting / Radix / Bucket + "sort"
4. fallback:
   `ภาพขั้นตอนจากหน้า N`

metadata source มาจาก manifest ถ้า SHA-256 ตรงกับ PDF

## 5. image_index convention

ตอนนี้ใช้:
- embedded image: 1,2,3,...
- vector_page_render: 0
- figure_crop: 1001+
- trace_crop: 2001+

ใช้แยก type ในหน้าเดียวกันได้ง่าย แต่จริง ๆ UI ตัดสินจาก metadata.kind

## 6. User-facing selector

`RAGService.select_user_visible_images()`

อนุญาตเฉพาะ:
- figure_crop
- trace_crop

ห้าม:
- embedded_image
- vector_page_render

เหตุผล:
embedded มีโอกาสดำ/ผิด layer
full page อ่านยากและไม่ใช่ “ภาพประกอบ”

## 7. Follow-up “ภาพ”

flow:
1. user ถาม `selection sort`
2. answer source refs ถูกเก็บใน message metadata
3. user ถาม `ภาพ`
4. visual clarification reuse previous user topic
5. retrieval query กลับเป็น selection sort
6. image refs ใช้ previous answer source refs ก่อน
7. current retrieval refs เป็น fallback
8. query `images_for_references`
9. filter figure_crop/trace_crop
10. แสดง caption + source + page

## 8. Current DB visual state

ตรวจล่าสุด:
- total 130
- embedded_image 8
- figure_crop 2
- trace_crop 49
- vector_page_render 71

**71 vector_page_render คือ signal ว่า crop pipeline ยังไม่ครอบคลุม**

## 9. ปัญหาปัจจุบันของ crop

### P0 — heuristic จับ layout ไม่ครบ
`_trace_clips` ใช้ rectangle grouping ตาม y gap

จึงมีโอกาส:
- crop กว้างเกิน
- crop แยก step ที่ควรรวม
- รวม visual กับ text decoration
- missed visual ที่ใช้เส้น/รูปทรงไม่เข้า threshold
- diagram ที่เป็น raster ไม่เข้า trace crop

### P0 — caption association ยังง่ายเกิน
figure crop:
- เลือก drawing ที่ area ใหญ่ที่สุดเหนือ caption
- ถ้าหน้ามีหลาย figure อาจจับผิด

### P0 — label อาจกว้าง/ผิด
trace caption:
- ถ้า manifest section/subtopic กว้างเกิน จะ label กว้าง
- regex scan เจอชื่อ algorithm อื่นก่อน อาจ label ผิด
- fallback “ภาพขั้นตอนจากหน้า N” ไม่ช่วย semantic retrieval มาก

### P0 — ไม่มี visual quality score
ยังไม่มี:
- blank/black ratio
- text-only crop detection
- edge density
- crop aspect sanity score
- overlap/duplicate region suppression
- caption-distance confidence

### P1 — ยังไม่ได้ index image vector
`RAG_INDEX_IMAGES=false` โดย default

ปัจจุบัน image retrieval = text hit → source/page → visual

ยังไม่มี:
- query-to-image semantic similarity
- visual embedding rerank

### P1 — ไม่มี manual override
หน้า PDF สำคัญควรมี manifest override เช่น:

```json
{
  "page": 4,
  "visuals": [
    {
      "label": "Selection Sort รอบที่ 1",
      "clip": [0, 0, 0, 0],
      "step": 1
    }
  ]
}
```

ปัจจุบันยัง auto heuristic อย่างเดียว

## 10. แผนปรับ crop ที่แนะนำ

### Step A — สร้าง visual audit tool
ทำหน้า/CLI ที่:
- render page
- วาด bounding box ของ candidate
- แสดง crop preview
- label ที่ระบบคิด
- accept / reject / edit clip

output → manifest override

### Step B — Visual quality filter
คำนวณ:
- crop/page area ratio
- grayscale variance
- black/white percentage
- number of drawing objects
- text block overlap
- duplicate IoU

reject crop ที่ quality ต่ำ

### Step C — Better region grouping
แทน y-gap อย่างเดียวด้วย:
- connected/overlap graph ของ rect
- x/y proximity
- union-find clustering
- text/caption anchor
- IoU/NMS

### Step D — Label extraction
label ควรใช้:
1. manual manifest override
2. nearest caption/title block
3. section/subtopic metadata
4. nearest algorithm text
5. fallback

เพิ่ม:
- confidence
- algorithm canonical name
- step number

### Step E — Manual curriculum visual map
สำหรับ 6 หัวข้อหลัก ทำ map อย่างน้อย:
- overview
- key concept visual
- worked example / trace
- step 1..N ถ้ามี

### Step F — Step-by-step visualization
เมื่อ source มีหลาย trace crop:
- sort ด้วย page + y
- metadata `sequence_id`, `step`
- UI next/previous
- ห้ามสร้าง algorithm states จากความรู้ภายนอกถ้า source ไม่มี

## 11. วิธี refresh เฉพาะภาพ

ถ้าแก้ crop code แต่ text/PDF เดิม:

```bash
python -m scripts.ingest_pdf --images-only
```

ไม่ต้อง re-embed 119 chunks

ถ้า PDF เปลี่ยน:
```bash
python -m scripts.ingest_pdf --force
```

## 12. ไฟล์ที่ต้องแก้เมื่อทำต่อ

หลัก:
- `rag/pdf_ingest.py`
- `rag/service.py`
- `app.py`
- `real_data/topic_01_manifest.json`
- `tests/test_real_data_scope.py`

research/reference:
- `docs/RESEARCH_REFERENCES.md`
- `docs/DATA_DICTIONARY.md`
