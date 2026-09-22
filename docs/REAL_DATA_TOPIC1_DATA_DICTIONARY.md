# Real Data Topic 1 — Data Dictionary & Page Audit

## Scope

หัวข้อใหญ่: **1. หลักการเรียงลำดับข้อมูล (Sorting)**

ไฟล์ใน `real_data/` เท่านั้นที่เป็น Source of Truth ของ RAG

| Source | SHA-256 / source_id | Physical pages | Language | Status |
|---|---|---:|---|---|
| `1.หลักการเรียงลำดับข้อมูล-1.pdf` | `600a03b28f49640967e08144e0739e5f78049f8d6ba28ef3aeadc357002e10f3` | 60 | English | approved |
| `1.หลักการเรียงลำดับข้อมูล-2.pdf` | `0fe3eb3084a97ee2e0a91f9c7859a87c7427143fb7af5e684bdee998ffd915d6` | 21 | Thai | approved |

รวม **81 physical PDF pages** ที่ตรวจแล้ว

Machine-readable manifest: `real_data/topic_01_manifest.json`

ตอน ingest ระบบตรวจ SHA-256 ของ PDF กับ manifest ก่อน แล้วแนบ metadata รายหน้า (`section`, `subtopic`, `content_types`, `keywords`, `visual_mode`, `slide_labels`) ลงทุก text chunk และ internal image/page render โดยตรง หากไฟล์ PDF ถูกแก้จน hash ไม่ตรง ระบบจะหยุด ingest ไฟล์นั้นจนกว่าจะ audit/update manifest ใหม่

## Hard RAG rule — closed-source only

1. Retrieval ต้องค้นเฉพาะไฟล์ภายใต้ `real_data/`.
2. ห้ามใช้เว็บ, search engine, Wikipedia, external API, external image search หรือความรู้จากภายนอกเพื่อเติมเนื้อหา.
3. ห้ามใช้ความจำของ LLM เป็นหลักฐาน.
4. รูปประกอบอนุญาตเฉพาะ:
   - embedded image ที่อยู่ใน PDF จริง;
   - page render/screenshot ที่สร้างจากหน้า PDF จริง;
   - vector/diagram/table ที่อยู่บนหน้า PDF จริง.
5. ห้ามใช้ stock image, รูปจาก Google Images, รูปสร้างใหม่ด้วย AI หรือ diagram ที่ไม่ได้อยู่ในเอกสารเป็น RAG evidence.
6. ทุกภาพต้องผูกด้วย `source_id + physical_page` เดียวกับ retrieval hit.
7. ถ้าไม่มีหลักฐานใน `real_data/` ให้ abstain: บอกว่าไม่พบข้อมูลเพียงพอในฐานความรู้.
8. Citation ใช้ physical PDF page จริง ไม่เดาเลขหน้าจากข้อความบนสไลด์.

## Retrieval record fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| topic_id | TEXT | yes | หัวข้อใหญ่ เช่น `sorting-01` |
| topic_name | TEXT | yes | ชื่อหัวข้อใหญ่ |
| source_id | TEXT | yes | SHA-256 ของไฟล์ |
| source_file | TEXT | yes | ชื่อ PDF ใน `real_data/` |
| physical_page | INTEGER | yes | เลขหน้า PDF จริง ใช้ citation |
| slide_label | TEXT | no | เลขหน้าที่พิมพ์อยู่บนสไลด์; ใช้เป็น metadata เท่านั้น |
| section | TEXT | yes | กลุ่มเนื้อหา เช่น `quick_sort` |
| subtopic | TEXT | yes | หัวข้อเฉพาะของหน้า |
| language | TEXT | yes | `th`, `en`, หรือ `mixed` |
| content_types | JSONB | yes | เช่น `text`, `code`, `table`, `diagram`, `example`, `formula` |
| keywords | JSONB | yes | คำค้นหลัก/คำพ้องที่พบในเอกสาร |
| visual_available | BOOLEAN | yes | หน้านี้สามารถใช้ภาพภายในเอกสารได้หรือไม่ |
| visual_mode | TEXT | yes | `embedded_image`, `page_render`, `embedded_then_render`, `none` |
| embedded_image_count | INTEGER | yes | จำนวนรูป raster ที่ฝังในหน้า |
| source_only | BOOLEAN | yes | ต้องเป็น `true` เสมอ |
| retrieval_enabled | BOOLEAN | yes | หน้านี้ให้ RAG ค้นได้หรือไม่ |
| notes | TEXT | no | ข้อสังเกต เช่น PDF แบบ 2 slides/page |

## Visual retrieval contract

ลำดับการเลือกภาพเมื่อคำตอบมี retrieval hits:

1. สร้าง ordered references จาก hit: `(source_id, physical_page)`.
2. หา embedded image ใน reference นั้นก่อน.
3. ถ้าไม่มี embedded image แต่หน้ามี diagram/table/vector ให้ใช้ page render ของหน้าเดียวกัน.
4. จำกัดจำนวนภาพตาม `RAG_MAX_IMAGES_PER_ANSWER`.
5. ห้ามค้นภายนอกเมื่อภาพไม่พอ; ให้ตอบด้วยข้อความจากเอกสารแทน.
6. Caption ต้องระบุ `source_file · หน้า physical_page`.

> หมายเหตุ: ไฟล์ที่ 2 เป็น PDF 21 physical pages แต่หลาย physical page รวมสไลด์ต้นฉบับ 2 หน้าไว้ในหน้าเดียว ดังนั้น citation ต้องใช้ physical page 1–21 เท่านั้น

---

# Page audit — Source 1 (60 pages)

| Page | Section | Subtopic | Suggested content types | Internal visual |
|---:|---|---|---|---|
| 1 | overview | Sorting algorithms title | text | render on demand |
| 2 | overview | Learning goals | text | render on demand |
| 3 | overview | Outline | text | render on demand |
| 4 | fundamentals | Relation | definition, example, formula | render on demand |
| 5 | fundamentals | Ordering relation | definition, properties | render on demand |
| 6 | fundamentals | Sorting definition and before→after example | definition, example, diagram | page render |
| 7 | fundamentals | Common sorting requirements | table, definitions | page render |
| 8 | fundamentals | Why non-optimal algorithms are useful | explanation | render on demand |
| 9 | insertion_sort | Idea | explanation, array diagram | page render |
| 10 | insertion_sort | Pseudocode | pseudocode | page render |
| 11 | insertion_sort | Worked example | table, trace | page render |
| 12 | insertion_sort | Running time and properties | complexity, properties | page render |
| 13 | selection_sort | Idea | explanation, array diagram | page render |
| 14 | selection_sort | Pseudocode | pseudocode | page render |
| 15 | selection_sort | Worked example | table, trace | page render |
| 16 | selection_sort | Running time and properties | formula, complexity | page render |
| 17 | bubble_sort | Idea | explanation, swap diagram | page render |
| 18 | bubble_sort | Corrected pseudocode | pseudocode | page render |
| 19 | bubble_sort | Worked example | table, trace, complexity | page render |
| 20 | cocktail_sort | Motivation and idea | explanation | page render |
| 21 | cocktail_sort | Pseudocode | pseudocode | page render |
| 22 | cocktail_sort | Worked example | table, trace | page render |
| 23 | cocktail_sort | Properties | complexity, properties | render on demand |
| 24 | shell_sort | Idea | explanation, gap diagram | page render |
| 25 | shell_sort | Gap sequences | sequence, formula | page render |
| 26 | shell_sort | Pseudocode | pseudocode | page render |
| 27 | shell_sort | Example gaps 4,2,1 | table, trace, properties | page render |
| 28 | merge_sort | Divide-and-conquer idea | tree/diagram, example | page render |
| 29 | merge_sort | Merge operation | pseudocode, explanation | page render |
| 30 | merge_sort | Pseudocode | pseudocode, formula | page render |
| 31 | merge_sort | Running time | recurrence, tree, complexity | page render |
| 32 | batcher_merge | What Batcher odd-even merge is | explanation | render on demand |
| 33 | batcher_merge | Structure | sequence decomposition, steps | page render |
| 34 | batcher_merge | Worked example | diagram, sequence | page render |
| 35 | quick_sort | Idea | divide-and-conquer, partition | page render |
| 36 | quick_sort | Pseudocode | pseudocode | page render |
| 37 | quick_sort | Running time | recurrence, complexity | page render |
| 38 | quick_sort | Example partition | table, trace | page render |
| 39 | sqrt_sort | Square-root sorting | explanation, complexity | render on demand |
| 40 | lower_bound | Decision tree model | decision tree, diagram | page render |
| 41 | lower_bound | Stirling formula | formula | page render |
| 42 | lower_bound | Lower bound for comparison sorting | theorem, proof idea | page render |
| 43 | lower_bound | Consequence of Ω(n log n) | comparison, conclusion | render on demand |
| 44 | counting_sort | Assumptions | explanation, complexity | render on demand |
| 45 | counting_sort | Corrected pseudocode | pseudocode | page render |
| 46 | counting_sort | Worked example | count table, trace | page render |
| 47 | radix_sort | Idea | explanation, complexity | render on demand |
| 48 | radix_sort | Pseudocode | pseudocode | page render |
| 49 | radix_sort | Worked example | digit-pass table | page render |
| 50 | bucket_sort | Assumptions and procedure | steps, formula | page render |
| 51 | bucket_sort | Pseudocode | pseudocode | page render |
| 52 | bucket_sort | Worked example | bucket table, example | page render |
| 53 | external_sort | External sorting context | explanation | render on demand |
| 54 | external_sort | Runs | definition | render on demand |
| 55 | external_sort | Balanced two-way external merge | steps, complexity | page render |
| 56 | external_sort | Improving external sorting | explanation | render on demand |
| 57 | external_sort | Polyphase merge illustrative table | table | page render |
| 58 | comparison | Comparison of sorting methods | comparison table | page render |
| 59 | summary | Key takeaways | summary | render on demand |
| 60 | summary | Corrections and additions | summary, corrections | render on demand |

# Page audit — Source 2 (21 physical pages)

Embedded image counts that pass the actual ingestion filters (minimum size + duplicate removal):
- page 2: 2 images
- page 10: 2 images
- page 11: 1 image
- page 14: 1 image
- other pages: 0 accepted embedded raster images; page render remains available from the original PDF

QA result with `extract_images=true` and `render_vector_pages=true`:
- source 1: 60 page renders
- source 2: 21 page renders + 6 accepted embedded images
- total: 87 internal visuals covering all 81 physical pages

| Physical page | Section | Main content on this physical page | Suggested content types | Internal visual |
|---:|---|---|---|---|
| 1 | overview | Sorting title, topics, performance criteria | text, outline | page render |
| 2 | fundamentals | Sorting before/after + algorithm overview/complexities | example, comparison, table | embedded then render |
| 3 | selection_sort | lessThan/swap helpers + Selection Sort idea | code, explanation | page render |
| 4 | selection_bubble | Selection implementation/analysis + Bubble Sort idea | code, formula, explanation | page render |
| 5 | bubble_insertion | Bubble implementation/early stop + Insertion Sort idea | code, example | page render |
| 6 | insertion_sort | Insertion implementation and comparison counts | code, formula, trace | page render |
| 7 | shell_sort | Shell Sort example + implementation | example, code, trace | page render |
| 8 | shell_sort | h-sequences + why Shell Sort is fast | formula, explanation | page render |
| 9 | performance | Timing: sorted and reverse-sorted inputs for simple sorts | benchmark table | page render |
| 10 | performance_heap | Timing: random input + Heap Sort introduction | benchmark table, heap diagram | embedded then render |
| 11 | heap_merge | Heap Sort implementation + Merge Sort introduction | code, diagram | embedded then render |
| 12 | merge_sort | Merge Sort implementation + merge operation | code, array example | page render |
| 13 | merge_sort | Merge analysis + upper-bound derivation | recurrence, formula | page render |
| 14 | merge_quick | Merge runtime conclusion + Quick Sort introduction | complexity, partition diagram | embedded then render |
| 15 | quick_sort | Quick Sort implementation + partition | code, partition trace | page render |
| 16 | quick_sort | Quick Sort recurrence + best case | recurrence, formula, diagram | page render |
| 17 | quick_sort | Worst case + average-case setup | formula, derivation | page render |
| 18 | quick_sort | Average-case derivation + pivot discussion | formula, explanation | page render |
| 19 | quick_sort | Median-of-three pivot + timing context | code, pivot diagram, benchmark | page render |
| 20 | performance | Timing comparisons across Shell/Heap/Merge/Quick variants | benchmark table | page render |
| 21 | comparison_summary | Auxiliary memory comparison + summary | comparison, summary | page render |

## Curriculum scope vs source coverage

The **primary curriculum contains exactly six sorting algorithms**:

1. Selection Sort
2. Insertion Sort
3. Bubble Sort
4. Shell Sort
5. Merge Sort
6. Quick Sort

The approved PDFs may also mention Heap Sort, Cocktail Sort, Counting Sort,
Radix Sort, Bucket Sort, Batcher odd-even merge, square-root sorting, or
external sorting. These are **reference-only source content** and must not be
promoted into the tutor's primary topic list.

The sources also cover sorting definitions, ordering requirements, stability,
in-place/adaptive concepts, complexity, performance comparisons, partition,
pivot selection, and merge operations.

## Ingestion policy for the six-topic future dataset

When Topic 2–6 are added:

1. place approved PDFs under `real_data/` (subfolders are allowed);
2. hash each file to create `source_id`;
3. ingest each PDF independently;
4. keep `topic_id`, `section`, and source metadata on every chunk/image;
5. retrieval must be scoped to source IDs currently present in `real_data/`;
6. never fall back to demo/legacy PDFs;
7. images always follow the same source/page reference as the retrieved text.
