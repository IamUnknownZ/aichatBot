"""
สคริปต์ช่วยเตรียมชุดข้อมูล Fine-tuning จากไฟล์ PDF เป็นรูปแบบ JSONL
สำหรับนำไป Fine-tune โมเดลใน Google AI Studio (Gemini) หรือ OpenAI
"""
import os
import json
from pypdf import PdfReader

PDF_PATH = "docs/อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf"
OUTPUT_JSONL = "dataset_finetune.jsonl"

SYSTEM_INSTRUCTION = (
    "คุณคือ AI ผู้ช่วยสอนวิชาโครงสร้างข้อมูลและอัลกอริทึมการเรียงลำดับข้อมูล ระดับมหาวิทยาลัยปี 1 "
    "อธิบายเข้าใจง่าย แสดงขั้นตอนการทำงาน (Trace) โค้ดภาษา Python และวิเคราะห์ Time/Space Complexity อย่างถูกต้อง"
)

# ตัวอย่าง Template คู่คำถาม-คำตอบพื้นฐานจากเอกสาร
SAMPLE_QA_TEMPLATES = [
    {
        "user": "การเรียงลำดับข้อมูล (Sorting) คืออะไร และมีความสำคัญอย่างไรในระดับปี 1",
        "model": "การเรียงลำดับข้อมูล (Sorting) คือกระบวนการจัดเรียงสมาชิกในรายการ (เช่น รายการคะแนน ตัวเลข หรือข้อความ) ให้อยู่ในลำดับที่กำหนด เช่น จากน้อยไปมาก (Ascending Order) หรือจากมากไปน้อย (Descending Order)\n\nความสำคัญ:\n1. ช่วยให้การค้นหาข้อมูลทำได้เร็วขึ้น (เช่น ใช้ Binary Search ได้)\n2. ช่วยให้การนำเสนอข้อมูลดูเข้าใจง่ายและเป็นระเบียบ\n3. เป็นพื้นฐานสำคัญในการเรียนรู้วิเคราะห์ประสิทธิภาพของอัลกอริทึม (Time & Space Complexity)"
    },
    {
        "user": "อธิบายหลักการทำงานของ Bubble Sort พร้อมตัวอย่าง",
        "model": "Bubble Sort (การเรียงลำดับแบบฟองสบู่) ทำงานโดยการเปรียบเทียบสมาชิกที่อยู่ติดกันทีละคู่ หากสมาชิกตัวหน้ามากกว่าตัวหลัง จะทำการสลับตำแหน่ง (Swap) กัน ทำซ้ำแบบนี้ไปเรื่อยๆ จนกว่าข้อมูลจะเรียงครบทั้งหมด\n\nตัวอย่าง:\nข้อมูลเริ่มต้น: `[5, 1, 4, 2]`\n- เปรียบเทียบ 5 กับ 1 -> สลับเป็น `[1, 5, 4, 2]`\n- เปรียบเทียบ 5 กับ 4 -> สลับเป็น `[1, 4, 5, 2]`\n- เปรียบเทียบ 5 กับ 2 -> สลับเป็น `[1, 4, 2, 5]` (รอบที่ 1 จบ: ตัวที่มากที่สุดคือ 5 ไปอยู่ท้ายสุด)\n- ทำซ้ำรอบถัดไปจนครบทุกตัว"
    },
    {
        "user": "Selection Sort มีขั้นตอนการทำงานอย่างไร และต่างจาก Bubble Sort อย่างไร",
        "model": "Selection Sort (การเรียงลำดับแบบเลือก) ทำงานโดยการค้นหาค่าที่น้อยที่สุด (Min) ในช่วงข้อมูลที่ยังไม่ได้เรียง แล้วนำมาสลับกับตำแหน่งแรกสุดของช่วงนั้น\n\nความต่างหลัก:\n- **Bubble Sort:** มีการสลับที่บ่อยมาก (สลับทันทีที่เจอคู่ที่ผิดลำดับ)\n- **Selection Sort:** สลับตำแหน่งเพียง 1 ครั้งต่อ 1 รอบการวนซ้ำ (หลังจากหาค่าน้อยสุดเจอแล้ว)"
    },
    {
        "user": "Time Complexity ของ Merge Sort ในกรณี Best, Average, Worst Case คือเท่าใด เพราะเหตุใด",
        "model": "Time Complexity ของ Merge Sort:\n- **Best Case:** O(n log n)\n- **Average Case:** O(n log n)\n- **Worst Case:** O(n log n)\n\nเหตุผล: Merge Sort ใช้เทคนิค Divide and Conquer โดยแบ่งครึ่งข้อมูลออกเป็น 2 ส่วนเสมอ (ใช้เวลา log n ชั้น) และในแต่ละชั้นจะนำข้อมูลมารวมกัน (Merge) โดยเปรียบเทียบ n ตัวเสมอ ดังนั้นประสิทธิภาพจึงคงที่อยู่ที่ O(n log n) ในทุกกรณี"
    }
]

def generate_jsonl():
    if not os.path.exists(PDF_PATH):
        # Fallback to root path
        alt_path = "อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf"
        if os.path.exists(alt_path):
            pdf_file = alt_path
        else:
            print(f"ไม่พบไฟล์ PDF ที่ {PDF_PATH}")
            return
    else:
        pdf_file = PDF_PATH

    print(f"กำลังอ่านไฟล์: {pdf_file}...")
    reader = PdfReader(pdf_file)
    print(f"จำนวนหน้าทั้งหมด: {len(reader.pages)} หน้า")

    # บันทึกไฟล์ JSONL ในฟอร์แมต Gemini Fine-Tuning
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for item in SAMPLE_QA_TEMPLATES:
            entry = {
                "messages": [
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": item["user"]},
                    {"role": "model", "content": item["model"]}
                ]
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"✅ สร้างไฟล์ Dataset สำหรับ Fine-tuning เรียบร้อย: {OUTPUT_JSONL}")
    print("สามารถนำไฟล์นี้ไปอัปโหลดที่ Google AI Studio > Tuning เพื่อเริ่มเทรนโมเดลได้เลยครับ")

if __name__ == "__main__":
    generate_jsonl()
