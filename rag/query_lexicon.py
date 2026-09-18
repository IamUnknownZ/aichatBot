from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
import re
import unicodedata


RAW_ALIASES = {
  "topics": {
    "Bubble Sort": [
      "bubble sort",
      "bubblesort",
      "bubble",
      "bubble sorting",
      "bubble-sort",
      "bubble algorithm",
      "bubble sorting algorithm",
      "bubble method",
      "bubble technique",
      "sort by bubble",
      "บับเบิลซอร์ท",
      "บับเบิลซอร์ต",
      "บับเบิ้ลซอร์ท",
      "บับเบิ้ลซอร์ต",
      "บับเบิลซอท",
      "บับเบิ้ลซอท",
      "บับเบิ้ลซอด",
      "บับเบิล ซอร์ท",
      "บับเบิ้ล ซอร์ท",
      "เรียงแบบฟองสบู่",
      "ฟองสบู่",
      "การเรียงแบบฟองสบู่",
      "วิธีฟองสบู่",
      "อัลกอริทึมฟองสบู่"
    ],
    "Selection Sort": [
      "selection sort",
      "selectionsort",
      "selection",
      "selection sorting",
      "selection-sort",
      "selection algorithm",
      "selection sorting algorithm",
      "selection method",
      "select sort",
      "sort by selection",
      "ซีเล็กชันซอร์ท",
      "ซีเล็กชั่นซอร์ท",
      "ซีเลคชันซอร์ท",
      "ซีเลคชั่นซอร์ท",
      "เซเล็กชันซอร์ท",
      "เซเล็กชั่นซอร์ท",
      "ซีเล็กชันซอท",
      "ซีเล็กชั่นซอท",
      "ซีเลคชั่น ซอร์ท",
      "ซีเล็กชั่น ซอร์ท",
      "การเรียงแบบเลือก",
      "เรียงแบบเลือก",
      "วิธีเลือกค่าน้อยสุด",
      "เลือกค่าน้อยสุด",
      "เลือกค่าต่ำสุด"
    ],
    "Insertion Sort": [
      "insertion sort",
      "insertionsort",
      "insertion",
      "insertion sorting",
      "insertion-sort",
      "insertion algorithm",
      "insertion sorting algorithm",
      "insertion method",
      "insert sort",
      "sort by insertion",
      "อินเซอร์ชันซอร์ท",
      "อินเซิร์ชันซอร์ท",
      "อินเซอชันซอร์ท",
      "อินเซอชั่นซอร์ท",
      "อินเซอร์ชั่นซอร์ท",
      "อินเซิร์ชั่นซอร์ท",
      "อินเซอร์ชันซอท",
      "อินเซิร์ชันซอท",
      "อินเซอร์ชัน ซอร์ท",
      "อินเซิร์ชัน ซอร์ท",
      "การเรียงแบบแทรก",
      "เรียงแบบแทรก",
      "วิธีแทรก",
      "แทรกข้อมูลเรียงลำดับ",
      "insert แบบเรียง"
    ],
    "Merge Sort": [
      "merge sort",
      "mergesort",
      "merge",
      "merge sorting",
      "merge-sort",
      "merge algorithm",
      "merge sorting algorithm",
      "merge method",
      "sort by merge",
      "divide merge sort",
      "เมิร์จซอร์ท",
      "เมอร์จซอร์ท",
      "เมิร์กซอร์ท",
      "เมิจก์ซอร์ท",
      "เมิร์จซอท",
      "เมอร์จซอท",
      "เมิร์จ ซอร์ท",
      "เมอร์จ ซอร์ท",
      "การเรียงแบบผสาน",
      "เรียงแบบผสาน",
      "การเรียงแบบรวม",
      "แบ่งแล้วรวม",
      "แบ่งครึ่งแล้วรวม",
      "divide and merge",
      "merge แบบแบ่งครึ่ง"
    ],
    "Quick Sort": [
      "quick sort",
      "quicksort",
      "quick",
      "quick sorting",
      "quick-sort",
      "quick algorithm",
      "quick sorting algorithm",
      "quick method",
      "sort by quick",
      "pivot sort",
      "ควิกซอร์ท",
      "ควิกซอร์ต",
      "ควิกซอท",
      "ควิก ซอร์ท",
      "ควิกซอร์ทอัลกอริทึม",
      "ควิกซอร์ตอัลกอริทึม",
      "ควิ๊กซอร์ท",
      "ควิคซอร์ท",
      "การเรียงแบบเร็ว",
      "เรียงแบบเร็ว",
      "การเรียงแบบควิก",
      "แบ่งด้วย pivot",
      "pivot partition sort",
      "พิวอตซอร์ท",
      "พิวอทซอร์ท"
    ],
    "Heap Sort": [
      "heap sort",
      "heapsort",
      "heap",
      "heap sorting",
      "heap-sort",
      "heap algorithm",
      "heap sorting algorithm",
      "heap method",
      "sort by heap",
      "binary heap sort",
      "ฮีปซอร์ท",
      "ฮีปซอร์ต",
      "ฮีปซอท",
      "ฮีป ซอร์ท",
      "ฮี๊ปซอร์ท",
      "ฮิพซอร์ท",
      "ฮีป sort",
      "การเรียงแบบฮีป",
      "เรียงแบบฮีป",
      "เรียงด้วยฮีป",
      "binary heap sorting",
      "max heap sort",
      "min heap sort",
      "heapify sort",
      "ฮีปไฟซอร์ท"
    ],
    "Shell Sort": [
      "shell sort",
      "shellsort",
      "shell",
      "shell sorting",
      "shell-sort",
      "shell algorithm",
      "shell sorting algorithm",
      "shell method",
      "sort by shell",
      "gap sort",
      "เชลล์ซอร์ท",
      "เชลซอร์ท",
      "เชลล์ซอท",
      "เชลซอท",
      "เชลล์ ซอร์ท",
      "เชล ซอร์ท",
      "เชลล์ sort",
      "การเรียงแบบเชลล์",
      "เรียงแบบเชลล์",
      "เรียงแบบช่วงห่าง",
      "gap sorting",
      "gap insertion sort",
      "increment sort",
      "shell method sort",
      "วิธีเชลล์"
    ],
    "Counting Sort": [
      "counting sort",
      "countingsort",
      "counting",
      "counting sorting",
      "counting-sort",
      "counting algorithm",
      "counting sorting algorithm",
      "counting method",
      "sort by counting",
      "frequency sort",
      "เคาน์ติ้งซอร์ท",
      "เคาน์ทิงซอร์ท",
      "เคาน์ติ้งซอท",
      "เคาท์ติ้งซอร์ท",
      "เคาน์ติ้ง ซอร์ท",
      "เคาน์ทิง ซอร์ท",
      "count sort",
      "การเรียงแบบนับ",
      "เรียงแบบนับ",
      "เรียงด้วยการนับ",
      "นับความถี่แล้วเรียง",
      "frequency counting sort",
      "count frequency sort",
      "วิธีนับจำนวน",
      "อัลกอริทึมนับ"
    ],
    "Radix Sort": [
      "radix sort",
      "radixsort",
      "radix",
      "radix sorting",
      "radix-sort",
      "radix algorithm",
      "radix sorting algorithm",
      "radix method",
      "sort by radix",
      "digit sort",
      "เรดิกซ์ซอร์ท",
      "เรดิกซอร์ท",
      "เรดิกซ์ซอท",
      "เรดิกซอท",
      "เรดิกซ์ ซอร์ท",
      "เรดิก ซอร์ท",
      "radix แบบหลัก",
      "การเรียงตามหลัก",
      "เรียงตามหลัก",
      "เรียงตามเลขหลัก",
      "digit sorting",
      "lsd radix sort",
      "msd radix sort",
      "เรียงทีละหลัก",
      "วิธีเรดิกซ์"
    ],
    "Bucket Sort": [
      "bucket sort",
      "bucketsort",
      "bucket",
      "bucket sorting",
      "bucket-sort",
      "bucket algorithm",
      "bucket sorting algorithm",
      "bucket method",
      "sort by bucket",
      "bin sort",
      "บักเก็ตซอร์ท",
      "บัคเก็ตซอร์ท",
      "บักเกตซอร์ท",
      "บัคเกตซอร์ท",
      "บักเก็ตซอท",
      "บักเก็ต ซอร์ท",
      "bucket แบบถัง",
      "การเรียงแบบถัง",
      "เรียงแบบถัง",
      "เรียงลงถัง",
      "bin sorting",
      "distribution bucket sort",
      "กระจายลงถัง",
      "วิธีถัง",
      "อัลกอริทึมบักเก็ต"
    ]
  },
  "concepts": {
    "time complexity Big-O": [
      "big o",
      "big-o",
      "bigo",
      "big o notation",
      "asymptotic complexity",
      "time complexity",
      "ไทม์คอมเพล็กซิตี้",
      "ไทมคอมเพลกซิตี",
      "ไทม์คอมเพลกซิตี้",
      "ไทมคอมเพล็กซิตี",
      "runtime complexity",
      "computational complexity",
      "complexity",
      "worst case",
      "best case",
      "average case",
      "บิ๊กโอ",
      "บิกโอ",
      "บิ๊ก o",
      "ความซับซ้อน",
      "ความซับซ้อนเชิงเวลา",
      "เวลาในการทำงาน",
      "ประสิทธิภาพเชิงเวลา",
      "กรณีแย่ที่สุด",
      "กรณีดีที่สุด",
      "กรณีเฉลี่ย",
      "โอใหญ่",
      "สัญกรณ์บิ๊กโอ"
    ],
    "space complexity memory": [
      "space complexity",
      "memory complexity",
      "memory usage",
      "extra memory",
      "auxiliary space",
      "storage usage",
      "memory cost",
      "space usage",
      "additional memory",
      "constant space",
      "linear space",
      "memory requirement",
      "ความซับซ้อนเชิงพื้นที่",
      "การใช้หน่วยความจำ",
      "หน่วยความจำ",
      "พื้นที่หน่วยความจำ",
      "หน่วยความจำเพิ่มเติม",
      "ใช้แรม",
      "กินแรม",
      "พื้นที่เพิ่มเติม",
      "ความจำเสริม",
      "พื้นที่จัดเก็บ"
    ],
    "stable sorting stability": [
      "stable sort",
      "stable sorting",
      "stability",
      "stable algorithm",
      "sorting stability",
      "preserve equal order",
      "relative order",
      "equal elements order",
      "unstable sort",
      "unstable sorting",
      "stable property",
      "is stable",
      "stable",
      "สเตเบิล",
      "สเตเบิ้ล",
      "สเตเบิลล",
      "สเตเบิ้ลล",
      "เสถียร",
      "ความเสถียร",
      "การเรียงแบบเสถียร",
      "รักษาลำดับเดิม",
      "ค่าซ้ำลำดับเดิม",
      "สมาชิกเท่ากัน",
      "ลำดับสัมพัทธ์",
      "ไม่เสถียร",
      "เรียงเสถียร"
    ],
    "in-place sorting": [
      "in place",
      "in-place",
      "inplace",
      "in place sort",
      "in-place sort",
      "inplace sort",
      "in place algorithm",
      "constant extra space",
      "without extra array",
      "no extra array",
      "in memory sort",
      "in situ sort",
      "อินเพลส",
      "อินเพลซ",
      "เรียงในที่เดิม",
      "ไม่ใช้อาร์เรย์เพิ่ม",
      "ไม่ใช้พื้นที่เพิ่ม",
      "ใช้พื้นที่คงที่",
      "ทำในอาร์เรย์เดิม",
      "แก้ในข้อมูลเดิม",
      "ไม่สร้างลิสต์ใหม่",
      "พื้นที่เสริมคงที่"
    ],
    "comparison sorting": [
      "comparison sort",
      "comparison sorting",
      "comparison based sort",
      "comparison-based sorting",
      "compare elements",
      "element comparison",
      "key comparison",
      "comparison algorithm",
      "comparison model",
      "compare and swap",
      "comparison method",
      "comparison based",
      "การเรียงแบบเปรียบเทียบ",
      "เปรียบเทียบค่า",
      "การเปรียบเทียบสมาชิก",
      "เปรียบเทียบแล้วสลับ",
      "อาศัยการเปรียบเทียบ",
      "เรียงด้วยการเปรียบเทียบ",
      "เทียบค่าแล้วเรียง",
      "เปรียบเทียบคีย์",
      "วิธีเปรียบเทียบ"
    ],
    "divide and conquer": [
      "divide and conquer",
      "divide-and-conquer",
      "divide conquer",
      "divide then combine",
      "recursive divide",
      "split and merge",
      "split problem",
      "divide problem",
      "combine subproblems",
      "recursive decomposition",
      "divide strategy",
      "divide approach",
      "แบ่งแยกและเอาชนะ",
      "แบ่งแล้วแก้",
      "แบ่งปัญหา",
      "แยกปัญหาย่อย",
      "รวมผลปัญหาย่อย",
      "แบ่งครึ่ง",
      "divide conquer",
      "ดิไวด์แอนด์คองเคอร์",
      "ดิไวด์แอนคองเคอร์",
      "ดิวายแอนคองเคอ",
      "ดิวายด์แอนด์คองเคอร์",
      "แนวคิดแบ่งปัญหา",
      "วิธีแบ่งแยก",
      "แบ่งแล้วรวม"
    ],
    "recursion recursive": [
      "recursion",
      "recursive",
      "recursive algorithm",
      "recursive call",
      "recursive function",
      "base case",
      "recursive step",
      "call itself",
      "self recursion",
      "recursion depth",
      "recursive sorting",
      "recursive method",
      "รีเคอร์ชัน",
      "รีเคอร์ซีฟ",
      "เรียกตัวเอง",
      "ฟังก์ชันเรียกตัวเอง",
      "กรณีฐาน",
      "การวนซ้ำแบบเรียกตัวเอง",
      "การเรียกซ้ำ",
      "recursive แบบไทย",
      "ลำดับการเรียกซ้ำ",
      "ความลึกรีเคอร์ชัน"
    ],
    "iteration pass trace": [
      "iteration",
      "pass",
      "round",
      "trace",
      "dry run",
      "step by step",
      "walkthrough",
      "simulation",
      "each pass",
      "each round",
      "sorting pass",
      "algorithm trace",
      "trace table",
      "manual trace",
      "ทีละรอบ",
      "แต่ละรอบ",
      "แต่ละ pass",
      "ไล่ทีละขั้น",
      "ตามรอย",
      "จำลองการทำงาน",
      "ทำมือ",
      "แสดงรอบ",
      "ตาราง trace",
      "ขั้นตอนต่อขั้นตอน",
      "เดินค่าทีละรอบ",
      "ไล่ค่า"
    ]
  },
  "actions": {
    "explain": [
      "อธิบาย",
      "ช่วยอธิบาย",
      "คืออะไร",
      "หมายถึงอะไร",
      "ทำความเข้าใจ",
      "ขอความหมาย",
      "สรุปความหมาย",
      "explain",
      "what is",
      "meaning",
      "define",
      "definition",
      "tell me about",
      "how does it work",
      "ทำงานยังไง",
      "ทำงานอย่างไร",
      "หลักการ",
      "หลักการทำงาน",
      "ขอภาพรวม",
      "เล่าให้ฟัง"
    ],
    "compare": [
      "เปรียบเทียบ",
      "เทียบ",
      "ต่างกันยังไง",
      "ต่างกันอย่างไร",
      "เหมือนกันไหม",
      "อันไหนต่าง",
      "ข้อแตกต่าง",
      "compare",
      "comparison",
      "versus",
      "vs",
      "difference",
      "different",
      "how different",
      "compare with",
      "ข้อเหมือน",
      "ข้อดีข้อเสีย",
      "ต่างตรงไหน",
      "เลือกอันไหนดี",
      "เทียบกัน"
    ],
    "example": [
      "ตัวอย่าง",
      "ขอตัวอย่าง",
      "ยกตัวอย่าง",
      "ยกเคส",
      "ลองให้ดู",
      "สาธิต",
      "ตัวอย่างง่ายๆ",
      "example",
      "give example",
      "sample",
      "demo",
      "demonstrate",
      "show me",
      "illustrate",
      "case example",
      "เช่นอะไร",
      "มีตัวอย่างไหม",
      "ทำตัวอย่าง",
      "ตัวอย่างข้อมูล",
      "ตัวอย่างการเรียง"
    ],
    "trace": [
      "trace",
      "dry run",
      "ไล่ค่า",
      "ไล่ทีละรอบ",
      "ทีละรอบ",
      "ทีละขั้น",
      "แสดงทุกขั้น",
      "จำลอง",
      "walk through",
      "walkthrough",
      "step by step",
      "show steps",
      "each pass",
      "each round",
      "manual run",
      "ตามรอย",
      "ทำตาราง",
      "แสดงรอบ",
      "ดูการสลับ",
      "ไล่การสลับ",
      "ทำให้ดู"
    ],
    "code": [
      "โค้ด",
      "ขอโค้ด",
      "เขียนโค้ด",
      "โปรแกรม",
      "implementation",
      "implement",
      "code",
      "source code",
      "python",
      "ภาษาไพธอน",
      "pseudocode",
      "pseudo code",
      "รหัสเทียม",
      "เขียนฟังก์ชัน",
      "เขียนโปรแกรม",
      "ตัวอย่างโค้ด",
      "code example",
      "ทำเป็นโค้ด",
      "syntax",
      "เขียนยังไง"
    ],
    "summarize": [
      "สรุป",
      "สรุปให้หน่อย",
      "สรุปสั้นๆ",
      "สรุปย่อ",
      "ใจความ",
      "ประเด็นสำคัญ",
      "เอาสั้นๆ",
      "summary",
      "summarize",
      "short summary",
      "brief",
      "key points",
      "main points",
      "tl dr",
      "tldr",
      "สั้นๆ",
      "รวบรัด",
      "สรุปรวม",
      "ขอประเด็น",
      "จำง่ายๆ",
      "เอาไว้ท่อง"
    ],
    "why": [
      "ทำไม",
      "เพราะอะไร",
      "เหตุผล",
      "เพราะเหตุใด",
      "ทำไมต้อง",
      "ทำไมถึง",
      "ข้อสังเกต",
      "why",
      "reason",
      "why does",
      "why is",
      "because",
      "explain why",
      "what causes",
      "เกิดจากอะไร",
      "สาเหตุ",
      "มีเหตุผลอะไร",
      "เพราะเหตุไหน",
      "ช่วยบอกเหตุผล",
      "เหตุใด"
    ]
  },
  "social": {
    "greeting": [
      "ไง",
      "ไงครับ",
      "ไงคับ",
      "ไงง",
      "ว่าไง",
      "ว่าไงง",
      "หวัดดี",
      "หวัดดีครับ",
      "หวัดดีคับ",
      "สวัสดี",
      "สวัสดีครับ",
      "สวัสดีคับ",
      "ดีครับ",
      "ดีคับ",
      "ฮัลโหล",
      "ฮัลโหลครับ",
      "hello",
      "hello there",
      "hi",
      "hi there",
      "hey",
      "hey there",
      "yo",
      "good morning",
      "good afternoon",
      "good evening"
    ],
    "thanks": [
      "ขอบคุณ",
      "ขอบคุณครับ",
      "ขอบคุณคับ",
      "ขอบใจ",
      "ขอบใจมาก",
      "ขอบคุณมาก",
      "ขอบคุณนะ",
      "โอเคขอบคุณ",
      "thank you",
      "thanks",
      "thanks a lot",
      "thank you so much",
      "thx",
      "ty",
      "appreciate it",
      "แต๊ง",
      "แต๊งกิ้ว",
      "ขอบพระคุณ",
      "ดีมากขอบคุณ",
      "โอเคเลย"
    ],
    "farewell": [
      "บาย",
      "บายครับ",
      "ไปละ",
      "ไปแล้ว",
      "เจอกัน",
      "ไว้เจอกัน",
      "ไว้คุยกัน",
      "จบละ",
      "พอละ",
      "bye",
      "goodbye",
      "see you",
      "see ya",
      "later",
      "catch you later",
      "talk later",
      "good night",
      "ขอตัวก่อน",
      "ไว้ถามใหม่",
      "ไปก่อนนะ",
      "เจอกันใหม่"
    ],
    "help": [
      "ช่วยอะไรได้บ้าง",
      "ทำอะไรได้บ้าง",
      "ถามอะไรได้บ้าง",
      "ช่วยหน่อย",
      "ใช้ยังไง",
      "ใช้งานยังไง",
      "ถามแบบไหนได้",
      "มีอะไรให้ถาม",
      "เริ่มยังไง",
      "ช่วยสอนได้ไหม",
      "help",
      "help me",
      "what can you do",
      "how to use",
      "how do i use this",
      "what can i ask",
      "show help",
      "commands",
      "guide me",
      "usage",
      "start"
    ],
    "identity": [
      "ชื่ออะไร",
      "นายชื่ออะไร",
      "เธอชื่ออะไร",
      "คุณชื่ออะไร",
      "ชื่อไร",
      "เป็นใคร",
      "นายเป็นใคร",
      "คุณเป็นใคร",
      "who are you",
      "what are you",
      "what is your name",
      "your name",
      "name",
      "introduce yourself",
      "แนะนำตัว",
      "ช่วยแนะนำตัว",
      "เป็นบอทอะไร",
      "บอทชื่ออะไร",
      "ชื่อบอท",
      "ai อะไร"
    ]
  }
}


@lru_cache(maxsize=4096)
def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = re.sub(r"[!?！？.,，。;:()\[\]{}'\"“”‘’]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=4096)
def compact_text(value: str) -> str:
    return re.sub(r"[^a-z0-9ก-๙]+", "", normalize_text(value))


@dataclass(frozen=True)
class AliasMatch:
    kind: str
    canonical: str
    alias: str
    match_type: str
    score: float
    normalized_alias: str = ""
    compact_alias: str = ""


_EXACT: dict[str, AliasMatch] = {}
_COMPACT: dict[str, AliasMatch] = {}
_EXACT_BY_KIND: dict[str, dict[str, AliasMatch]] = {}
_COMPACT_BY_KIND: dict[str, dict[str, AliasMatch]] = {}
_BY_LENGTH: dict[int, list[AliasMatch]] = {}
_BY_KIND_LENGTH: dict[str, dict[int, list[AliasMatch]]] = {}
_SEARCHABLE: list[AliasMatch] = []
_SEARCHABLE_BY_KIND: dict[str, list[AliasMatch]] = {}

for kind, groups in RAW_ALIASES.items():
    for canonical, aliases in groups.items():
        for alias in aliases:
            normalized = normalize_text(alias)
            compact = compact_text(alias)
            if not normalized or not compact:
                continue
            match = AliasMatch(
                kind,
                canonical,
                alias,
                "exact",
                1.0,
                normalized,
                compact,
            )
            _EXACT.setdefault(normalized, match)
            _COMPACT.setdefault(compact, match)
            _EXACT_BY_KIND.setdefault(kind, {}).setdefault(normalized, match)
            _COMPACT_BY_KIND.setdefault(kind, {}).setdefault(compact, match)
            _BY_LENGTH.setdefault(len(compact), []).append(match)
            _BY_KIND_LENGTH.setdefault(kind, {}).setdefault(
                len(compact), []
            ).append(match)
            _SEARCHABLE.append(match)
            _SEARCHABLE_BY_KIND.setdefault(kind, []).append(match)

TOTAL_ALIASES = len({(m.kind, m.canonical, compact_text(m.alias)) for m in _SEARCHABLE})


@lru_cache(maxsize=2048)
def match_alias(
    query: str,
    kind: str | None = None,
    *,
    allow_substring: bool = True,
    allow_fuzzy: bool = True,
) -> AliasMatch | None:
    normalized = normalize_text(query)
    compact = compact_text(query)
    if not compact:
        return None

    if kind is None:
        exact = _EXACT.get(normalized) or _COMPACT.get(compact)
    else:
        exact = (
            _EXACT_BY_KIND.get(kind, {}).get(normalized)
            or _COMPACT_BY_KIND.get(kind, {}).get(compact)
        )
    if exact is not None:
        return exact

    # Social intents should be whole-message matches so words such as "ไง"
    # inside an unrelated question do not turn it into a greeting.
    if allow_substring:
        best_substring: AliasMatch | None = None
        best_len = 0
        search_space = (
            _SEARCHABLE
            if kind is None
            else _SEARCHABLE_BY_KIND.get(kind, ())
        )
        for candidate in search_space:
            alias_norm = candidate.normalized_alias
            alias_compact = candidate.compact_alias
            if len(alias_compact) < 4:
                continue
            if alias_norm in normalized or alias_compact in compact:
                if len(alias_compact) > best_len:
                    best_len = len(alias_compact)
                    best_substring = AliasMatch(
                        candidate.kind,
                        candidate.canonical,
                        candidate.alias,
                        "substring",
                        0.96,
                        candidate.normalized_alias,
                        candidate.compact_alias,
                    )
        if best_substring is not None:
            return best_substring

    if not allow_fuzzy or len(compact) > 40:
        return None

    # Length bucketing prevents fuzzy matching from scanning the full lexicon.
    candidates: list[AliasMatch] = []
    radius = 4 if len(compact) >= 8 else 2
    length_buckets = (
        _BY_LENGTH
        if kind is None
        else _BY_KIND_LENGTH.get(kind, {})
    )
    for size in range(max(1, len(compact) - radius), len(compact) + radius + 1):
        candidates.extend(length_buckets.get(size, ()))

    best: AliasMatch | None = None
    best_score = 0.0
    for candidate in candidates:
        score = SequenceMatcher(
            None,
            compact,
            candidate.compact_alias,
        ).ratio()
        if score > best_score:
            best_score = score
            best = candidate

    threshold = 0.80 if kind == "social" else 0.73
    if best is not None and best_score >= threshold:
        return AliasMatch(
            best.kind,
            best.canonical,
            best.alias,
            "fuzzy",
            best_score,
            best.normalized_alias,
            best.compact_alias,
        )
    return None


def aliases_for(kind: str, canonical: str) -> tuple[str, ...]:
    values = RAW_ALIASES.get(kind, {}).get(canonical, ())
    return tuple(values)


def primary_thai_alias(kind: str, canonical: str) -> str:
    for alias in aliases_for(kind, canonical):
        if re.search(r"[ก-๙]", alias):
            return alias
    return ""
