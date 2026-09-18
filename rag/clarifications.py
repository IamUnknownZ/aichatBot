from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from .query_lexicon import compact_text, normalize_text


CLARIFICATION_GROUPS: dict[str, dict[str, object]] = {
    "general_sort": {
        "use_topic_context": False,
        "prompt": (
            "สนใจเรื่องไหนของ Sort (ซอร์ท) ครับ? เช่น Bubble Sort, "
            "Selection Sort, Insertion Sort, Merge Sort, Quick Sort "
            "หรืออยากดูภาพรวมของการเรียงลำดับข้อมูล?"
        ),
        "aliases": (
            "sort", "sorting", "sorts", "sorting algorithm", "sorting algorithms",
            "sort algorithm", "sort algo", "sorting algo", "about sort",
            "เรื่อง sort", "ซอร์ท", "ซอร์ต", "ซอท", "การซอร์ท", "เรื่องซอร์ท",
            "sorting คือ", "sort คือ", "การเรียง", "การเรียงข้อมูล",
            "เรียงข้อมูล", "เรียงลำดับ", "การเรียงลำดับ", "เรื่องการเรียง",
            "sorting data", "data sorting", "sort data", "วิชา sort",
        ),
    },
    "general_algorithm": {
        "use_topic_context": False,
        "prompt": (
            "หมายถึงอัลกอริทึมส่วนไหนครับ? ระบุชื่อได้เลย เช่น Bubble Sort, "
            "Merge Sort, Quick Sort หรือถ้าต้องการภาพรวมให้พิมพ์ว่า "
            "ภาพรวมอัลกอริทึมการเรียงลำดับ"
        ),
        "aliases": (
            "algorithm", "algorithms", "algo", "algos", "the algorithm",
            "algorithm sort", "algorithm sorting", "sorting method",
            "method", "methods", "อัลกอริทึม", "อัลกอริทึมครับ", "อัลกอ",
            "อัลกอริทึมเรียง", "วิธีเรียง", "วิธีการเรียง", "วิธี sorting",
            "ตัว algorithm", "เรื่อง algorithm", "algorithm คืออะไร",
            "อัลกอริทึมคือ", "วิธี", "วิธีทำ", "หลักการ", "แนวทาง",
        ),
    },
    "compare": {
        "use_topic_context": False,
        "prompt": (
            "อยากเปรียบเทียบอัลกอริทึมไหนกับอัลกอริทึมไหนครับ? "
            "เช่น Bubble Sort vs Selection Sort หรือ Merge Sort vs Quick Sort"
        ),
        "aliases": (
            "compare", "comparison", "vs", "versus", "compare them",
            "compare sort", "compare sorting", "difference", "differences",
            "different", "what difference", "which better", "which is better",
            "เทียบ", "เปรียบเทียบ", "เทียบกัน", "ต่างกัน", "ต่างกันยังไง",
            "ต่างกันอย่างไร", "ข้อแตกต่าง", "อันไหนดีกว่า", "ตัวไหนดีกว่า",
            "เทียบให้หน่อย", "เปรียบเทียบให้หน่อย", "เหมือนกันไหม", "ต่างไหม",
            "vs กัน", "อันไหนเร็วกว่า",
        ),
    },
    "code": {
        "use_topic_context": True,
        "prompt": (
            "อยากดูโค้ดของอัลกอริทึมไหนครับ? เช่น Bubble Sort Python, "
            "Quick Sort Python หรือ Merge Sort pseudocode"
        ),
        "aliases": (
            "code", "coding", "source code", "show code", "give code",
            "code please", "python", "python code", "implementation",
            "implement", "implementation code", "function", "write function",
            "pseudocode", "pseudo code", "syntax", "example code",
            "โค้ด", "ขอโค้ด", "เขียนโค้ด", "โค้ดหน่อย", "ขอ code",
            "เขียนโปรแกรม", "โปรแกรม", "ฟังก์ชัน", "เขียนฟังก์ชัน",
            "รหัสเทียม", "ซูโดโค้ด", "ไพธอน", "โค้ด python", "ทำเป็นโค้ด",
        ),
    },
    "trace": {
        "use_topic_context": True,
        "prompt": (
            "อยากให้ Trace อัลกอริทึมไหนและใช้ข้อมูลชุดไหนครับ? "
            "เช่น Trace Bubble Sort: 5, 1, 4, 2"
        ),
        "aliases": (
            "trace", "dry run", "walkthrough", "walk through", "step by step",
            "show steps", "show every step", "each pass", "each round",
            "simulate", "simulation", "manual run", "trace table",
            "ไล่ค่า", "ไล่ทีละรอบ", "ทีละรอบ", "ทีละขั้น", "ไล่ทีละขั้น",
            "trace ให้หน่อย", "จำลอง", "จำลองการทำงาน", "แสดงทุกขั้น",
            "แสดงรอบ", "ดูแต่ละรอบ", "ทำมือ", "ตาราง trace", "ไล่การสลับ",
        ),
    },
    "complexity": {
        "use_topic_context": True,
        "prompt": (
            "ต้องการดู Time Complexity / Big-O ของอัลกอริทึมไหนครับ? "
            "หรือถ้าอยากเรียนแนวคิด Big-O โดยรวม พิมพ์ว่า อธิบาย Big-O ได้เลย"
        ),
        "aliases": (
            "complexity", "time complexity", "runtime", "runtime complexity",
            "performance", "speed", "how fast", "fast or slow", "big o of it",
            "complexity please", "time", "efficiency", "efficient",
            "ความซับซ้อน", "ความซับซ้อนเวลา", "ความซับซ้อนเชิงเวลา",
            "เวลา", "เวลาในการทำงาน", "เร็วไหม", "ช้าไหม", "เร็วหรือช้า",
            "ประสิทธิภาพ", "กินเวลา", "ใช้เวลา", "big o ของมัน", "บิ๊กโอของมัน",
            "ความเร็ว", "เร็วแค่ไหน",
        ),
    },
    "stability": {
        "use_topic_context": True,
        "prompt": (
            "กำลังถามเรื่องความเสถียร (stable) ของอัลกอริทึมไหนครับ? "
            "เช่น Bubble Sort stable ไหม หรือ Quick Sort stable ไหม"
        ),
        "aliases": (
            "stable", "stability", "is it stable", "stable or not",
            "stable sort", "unstable", "is this stable", "stability please",
            "เสถียร", "ความเสถียร", "stable ไหม", "เสถียรไหม",
            "เสถียรหรือไม่", "ไม่เสถียร", "เป็น stable ไหม", "รักษาลำดับไหม",
            "ค่าซ้ำ", "ค่าซ้ำลำดับเดิม", "ลำดับเดิม", "relative order",
        ),
    },
    "memory": {
        "use_topic_context": True,
        "prompt": "อยากดูการใช้หน่วยความจำ / Space Complexity ของอัลกอริทึมไหนครับ?",
        "aliases": (
            "memory", "space", "space complexity", "memory usage",
            "memory complexity", "extra memory", "auxiliary space",
            "memory cost", "ram", "space usage", "storage",
            "หน่วยความจำ", "ใช้หน่วยความจำ", "กินแรม", "ใช้แรม",
            "พื้นที่", "พื้นที่เพิ่ม", "พื้นที่เพิ่มเติม", "ความจำ",
            "space ของมัน", "memory ของมัน", "แรม", "ใช้พื้นที่เท่าไร",
            "ใช้ memory เท่าไร", "พื้นที่หน่วยความจำ",
        ),
    },
    "example": {
        "use_topic_context": True,
        "prompt": (
            "อยากดูตัวอย่างของหัวข้อหรืออัลกอริทึมไหนครับ? "
            "เช่น ตัวอย่าง Bubble Sort หรือ ตัวอย่าง Big-O"
        ),
        "aliases": (
            "example", "examples", "give example", "show example", "sample",
            "demo", "demonstration", "example please", "for example",
            "case", "sample data", "example data", "illustrate",
            "ตัวอย่าง", "ขอตัวอย่าง", "ยกตัวอย่าง", "มีตัวอย่างไหม",
            "ลองให้ดู", "สาธิต", "ตัวอย่างหน่อย", "เคสตัวอย่าง",
            "ตัวอย่างง่ายๆ", "ทำตัวอย่าง", "ยกเคส", "เช่นอะไร",
        ),
    },
    "summary": {
        "use_topic_context": True,
        "prompt": "อยากให้สรุปหัวข้อไหนครับ? ระบุชื่ออัลกอริทึมหรือแนวคิดได้เลย",
        "aliases": (
            "summary", "summarize", "brief", "short summary", "tldr", "tl dr",
            "key points", "main points", "sum it up", "short version",
            "recap", "summary please", "สรุป", "สรุปหน่อย", "สรุปให้หน่อย",
            "สรุปสั้นๆ", "สรุปย่อ", "เอาสั้นๆ", "สั้นๆ", "ใจความ",
            "ประเด็นสำคัญ", "จำง่ายๆ", "เอาไว้ท่อง", "รวบรัด", "สรุปรวม",
        ),
    },
    "explain": {
        "use_topic_context": True,
        "prompt": (
            "อยากให้อธิบายเรื่องไหนครับ? เช่น อธิบาย Merge Sort "
            "หรือ อธิบาย stability"
        ),
        "aliases": (
            "explain", "explanation", "explain it", "tell me", "tell me more",
            "describe", "what is it", "meaning", "definition", "how it works",
            "how does it work", "อธิบาย", "อธิบายหน่อย", "ช่วยอธิบาย",
            "คืออะไร", "หมายถึงอะไร", "มันคืออะไร", "ทำงานยังไง",
            "ทำงานอย่างไร", "ขอความหมาย", "เล่าให้ฟัง", "ขอภาพรวม",
        ),
    },
    "why": {
        "use_topic_context": True,
        "prompt": (
            "หมายถึงทำไมในเรื่องไหนครับ? บอกชื่ออัลกอริทึมหรือประเด็นก่อนหน้าเพิ่มนิดหนึ่งได้เลย"
        ),
        "aliases": (
            "why", "why is that", "why though", "why does it", "reason",
            "because why", "explain why", "what causes it", "why so",
            "ทำไม", "เพราะอะไร", "เพราะเหตุใด", "เหตุผล", "ทำไมล่ะ",
            "ทำไมครับ", "ทำไมอะ", "ทำไมถึง", "ทำไมต้อง", "สาเหตุ",
            "เกิดจากอะไร", "เพราะเหตุไหน", "เหตุใด",
        ),
    },
    "visualize": {
        "use_topic_context": True,
        "prompt": (
            "อยากดูภาพ/แผนภาพของหัวข้อไหนครับ? เช่น ภาพ Bubble Sort ทีละรอบ "
            "หรือ แผนภาพ Merge Sort"
        ),
        "aliases": (
            "visual", "visualize", "visualise", "diagram", "picture", "image",
            "illustration", "animation", "show visually", "visual example",
            "graphical", "draw it", "show image", "รูป", "ภาพ", "แผนภาพ",
            "ไดอะแกรม", "ภาพประกอบ", "รูปประกอบ", "ขอรูป", "ขอภาพ",
            "ทำภาพ", "วาด", "แอนิเมชัน", "animation หน่อย", "เห็นภาพ",
        ),
    },
    "steps": {
        "use_topic_context": True,
        "prompt": "อยากดูขั้นตอนของอัลกอริทึมไหนครับ? เช่น ขั้นตอน Insertion Sort",
        "aliases": (
            "steps", "step", "procedure", "process", "how to", "method",
            "instructions", "how", "workflow", "sequence of steps",
            "ขั้นตอน", "ขอขั้นตอน", "ขั้นตอนการทำงาน", "วิธีทำ", "ทำยังไง",
            "ทำอย่างไร", "ลำดับขั้น", "วิธีการ", "ขั้นตอนหน่อย", "เริ่มยังไง",
            "ทำทีละขั้น", "กระบวนการ",
        ),
    },
    "pros_cons": {
        "use_topic_context": True,
        "prompt": "อยากดูข้อดี–ข้อเสียของอัลกอริทึมไหนครับ?",
        "aliases": (
            "pros cons", "pros and cons", "advantages", "disadvantages",
            "advantage", "disadvantage", "benefits", "drawbacks",
            "strengths weaknesses", "good bad", "tradeoffs", "trade offs",
            "ข้อดี", "ข้อเสีย", "ข้อดีข้อเสีย", "ข้อดีและข้อเสีย",
            "จุดเด่น", "จุดด้อย", "ข้อจำกัด", "มีข้อเสียอะไร",
            "มีข้อดีอะไร", "ดีตรงไหน", "เสียตรงไหน", "tradeoff",
        ),
    },
    "use_case": {
        "use_topic_context": True,
        "prompt": (
            "อยากรู้ว่าอัลกอริทึมไหนเหมาะกับกรณีใดครับ? ระบุชื่ออัลกอริทึมได้เลย"
        ),
        "aliases": (
            "use case", "use cases", "when to use", "when should use",
            "where to use", "best use", "suitable for", "appropriate for",
            "practical use", "real use", "application", "applications",
            "ใช้ตอนไหน", "ใช้เมื่อไร", "เหมาะกับอะไร", "เหมาะเมื่อไร",
            "ใช้กับอะไร", "ใช้งานจริง", "กรณีใช้งาน", "ควรใช้ตอนไหน",
            "เอาไปใช้ไหน", "ใช้กรณีไหน", "เหมาะตอนไหน", "สถานการณ์ไหน",
        ),
    },
    "order_direction": {
        "use_topic_context": True,
        "prompt": (
            "ต้องการเรียงน้อยไปมาก (ascending) หรือมากไปน้อย (descending) "
            "และใช้กับอัลกอริทึมไหนครับ?"
        ),
        "aliases": (
            "ascending", "descending", "asc", "desc", "ascending order",
            "descending order", "small to large", "large to small",
            "increasing", "decreasing", "order", "direction",
            "น้อยไปมาก", "มากไปน้อย", "จากน้อยไปมาก", "จากมากไปน้อย",
            "เรียงขึ้น", "เรียงลง", "ลำดับขึ้น", "ลำดับลง",
            "ascending ครับ", "descending ครับ", "เรียงเลข", "ทิศทางการเรียง",
        ),
    },
    "performance_choice": {
        "use_topic_context": False,
        "prompt": (
            "คำว่าเร็ว/ดีที่สุดขึ้นกับข้อมูลครับ — อยากเปรียบเทียบอัลกอริทึมไหน "
            "และสนใจเกณฑ์อะไร เช่น เวลา, หน่วยความจำ, stability หรือขนาดข้อมูล?"
        ),
        "aliases": (
            "best", "fastest", "best sort", "fastest sort", "most efficient",
            "which fastest", "which best", "best algorithm", "fast algorithm",
            "เร็วสุด", "ดีที่สุด", "ตัวไหนดี", "อันไหนดี", "อันไหนเร็วสุด",
            "ตัวไหนเร็วสุด", "ตัวไหนดีที่สุด", "เลือกอะไรดี", "ควรใช้อันไหน",
            "อันไหนคุ้ม", "ประสิทธิภาพดีที่สุด", "เร็วที่สุด", "ดีสุด",
        ),
    },
    "pivot": {
        "use_topic_context": True,
        "prompt": (
            "หมายถึง pivot ใน Quick Sort ใช่ไหมครับ? "
            "อยากรู้ความหมาย, วิธีเลือก pivot หรือดูตัวอย่างการ partition?"
        ),
        "aliases": (
            "pivot", "pivot element", "pivot value", "choose pivot",
            "pivot selection", "partition pivot", "the pivot",
            "พิวอต", "พิวอท", "ไพวอต", "ตัว pivot", "ค่า pivot",
            "เลือก pivot", "พิวอตคือ", "pivot คือ", "จุด pivot",
            "พิวอตหน่อย", "เรื่อง pivot",
        ),
    },
    "recursion": {
        "use_topic_context": True,
        "prompt": (
            "สนใจ recursion โดยรวม หรือ recursion ที่ใช้ใน Merge Sort / Quick Sort ครับ?"
        ),
        "aliases": (
            "recursion", "recursive", "recursive call", "recursive function",
            "base case", "recursion depth", "recursive algorithm",
            "รีเคอร์ชัน", "รีเคอร์ชั่น", "รีเคอร์ซีฟ", "เรียกตัวเอง",
            "ฟังก์ชันเรียกตัวเอง", "การเรียกซ้ำ", "กรณีฐาน",
            "base case คือ", "recursive คือ", "recursion คือ",
        ),
    },
    "data_input": {
        "use_topic_context": False,
        "prompt": (
            "ต้องการทำอะไรกับชุดข้อมูลนี้ครับ? เช่นให้ Sort, Trace ทีละรอบ, "
            "เปรียบเทียบอัลกอริทึม หรือวิเคราะห์ Big-O"
        ),
        "aliases": (
            "data", "dataset", "array", "list", "numbers", "input",
            "input data", "sample data", "values", "items", "elements",
            "ข้อมูล", "ชุดข้อมูล", "ตัวเลข", "อาร์เรย์", "array ครับ",
            "list ครับ", "ลิสต์", "อินพุต", "ข้อมูลนี้", "เลขชุดนี้",
            "ชุดตัวเลข", "ค่าพวกนี้", "สมาชิก", "elements ครับ",
        ),
    },
    "swap": {
        "use_topic_context": True,
        "prompt": (
            "หมายถึงการ swap (สลับค่า) ในอัลกอริทึมไหนครับ? "
            "เช่น Bubble Sort หรือ Selection Sort"
        ),
        "aliases": (
            "swap", "swapping", "swap values", "swap elements", "exchange",
            "exchange values", "สลับ", "สลับค่า", "การสลับ", "สลับตำแหน่ง",
            "สลับข้อมูล", "swap คือ", "swap หน่อย", "ทำไมสลับ",
            "การ exchange", "แลกตำแหน่ง",
        ),
    },
    "partition": {
        "use_topic_context": True,
        "prompt": (
            "หมายถึง partition ของ Quick Sort หรือการแบ่งข้อมูลแบบอื่นครับ? "
            "ถ้าเป็น Quick Sort ผมอธิบายทีละขั้นได้"
        ),
        "aliases": (
            "partition", "partitioning", "partition step", "partition process",
            "partition algorithm", "แบ่ง partition", "พาร์ทิชัน", "พาร์ติชัน",
            "การแบ่ง", "แบ่งข้อมูล", "แบ่งกลุ่ม", "partition คือ",
            "partition หน่อย", "ขั้นตอน partition", "แบ่งด้วย pivot",
        ),
    },
}


@dataclass(frozen=True)
class ClarificationMatch:
    canonical: str
    prompt: str
    alias: str
    match_type: str
    score: float
    use_topic_context: bool


_EXACT: dict[str, ClarificationMatch] = {}
_COMPACT: dict[str, ClarificationMatch] = {}
_BY_LENGTH: dict[int, list[ClarificationMatch]] = {}

for canonical, spec in CLARIFICATION_GROUPS.items():
    prompt = str(spec["prompt"])
    use_topic_context = bool(spec["use_topic_context"])
    for alias in spec["aliases"]:
        normalized = normalize_text(str(alias))
        compact = compact_text(str(alias))
        if not compact:
            continue
        match = ClarificationMatch(
            canonical=canonical,
            prompt=prompt,
            alias=str(alias),
            match_type="exact",
            score=1.0,
            use_topic_context=use_topic_context,
        )
        _EXACT.setdefault(normalized, match)
        _COMPACT.setdefault(compact, match)
        _BY_LENGTH.setdefault(len(compact), []).append(match)


TOTAL_CLARIFICATION_ALIASES = len(
    {
        (match.canonical, compact_text(match.alias))
        for values in _BY_LENGTH.values()
        for match in values
    }
)


@lru_cache(maxsize=1024)
def match_clarification(query: str) -> ClarificationMatch | None:
    """Match only an ambiguous whole utterance; never substring-match."""
    normalized = normalize_text(query)
    compact = compact_text(query)
    if not compact or len(compact) > 42:
        return None

    exact = _EXACT.get(normalized) or _COMPACT.get(compact)
    if exact is not None:
        return exact

    candidates: list[ClarificationMatch] = []
    radius = 2 if len(compact) < 8 else 3
    for size in range(max(1, len(compact) - radius), len(compact) + radius + 1):
        candidates.extend(_BY_LENGTH.get(size, ()))

    best: ClarificationMatch | None = None
    best_score = 0.0
    for candidate in candidates:
        score = SequenceMatcher(
            None,
            compact,
            compact_text(candidate.alias),
        ).ratio()
        if score > best_score:
            best_score = score
            best = candidate

    if best is not None and best_score >= 0.84:
        return ClarificationMatch(
            canonical=best.canonical,
            prompt=best.prompt,
            alias=best.alias,
            match_type="fuzzy",
            score=best_score,
            use_topic_context=best.use_topic_context,
        )
    return None
