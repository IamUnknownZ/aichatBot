import json
import unittest

from rag.bootstrap import resolve_pdf_paths, resolve_source_paths
from rag.models import DocumentChunk, ExtractedImage
from rag.pdf_ingest import parse_pdf, parse_source
from rag.service import RAGService
from rag.store import LocalLexicalStore
from rag.visuals import display_image_label, image_message_payload
from scripts.ingest_pdf import approved_ingest_sources


class RealDataScopeTests(unittest.TestCase):
    def test_merge_book_is_approved_with_readable_thai_code_and_scoped_pages(self):
        source = next(
            path for path in resolve_source_paths()
            if path.name == "Merge_Sort_Complete_Book_TH.pdf"
        )
        document = parse_pdf(source)
        self.assertEqual(document.page_count, 31)
        by_page = {}
        for chunk in document.chunks:
            by_page.setdefault(chunk.page_number, []).append(chunk)
        self.assertEqual(set(by_page), set(range(1, 32)))
        self.assertIn("การเรียงลำดับ", " ".join(c.content for c in by_page[4]))
        self.assertNotIn("คืือ", " ".join(c.content for c in by_page[4]))
        self.assertIn("def merge_sort(arr):", " ".join(c.content for c in by_page[14]))
        self.assertIn("    if len(arr) <= 1:", "\n".join(c.content for c in by_page[14]))
        self.assertEqual(by_page[23][0].metadata["curriculum_status"], "reference_only")
        self.assertEqual(by_page[14][0].metadata["curriculum_status"], "primary")

    def test_merge_book_visuals_are_precise_labeled_and_exclude_external_sort(self):
        source = next(
            path for path in resolve_source_paths()
            if path.name == "Merge_Sort_Complete_Book_TH.pdf"
        )
        document = parse_pdf(source, extract_images=True, render_vector_pages=True)
        visible = RAGService.select_user_visible_images(
            document.images, limit=100
        )
        self.assertTrue(any(i.page_number == 10 for i in visible))
        self.assertTrue(any(i.page_number == 14 for i in visible))
        self.assertTrue(any(i.page_number == 16 for i in visible))
        self.assertEqual(len(visible), 16)
        self.assertTrue(all(i.metadata.get("kind") == "figure_crop" for i in visible))
        self.assertTrue(all(i.metadata.get("visual_topic") == "Merge Sort" for i in visible))
        self.assertTrue(all(i.metadata.get("label") and i.metadata.get("visual_detail") for i in visible))
        self.assertFalse(any(i.page_number in {2, 15, 17, 20, 23, 27, 30, 31} for i in visible))
        page_ten = next(i for i in visible if i.page_number == 10)
        self.assertIn("ภาพที่ 6.1", page_ten.metadata["source_caption"])

    def test_streamlit_production_requires_database(self):
        from rag.bootstrap import build_rag_service
        from rag.config import Settings

        with self.assertRaisesRegex(RuntimeError, "DATABASE_URL"):
            build_rag_service(
                Settings(gemini_api_key="test-key", database_url=""),
                require_database=True,
            )

    def test_only_real_data_pdfs_are_selected(self):
        paths = resolve_pdf_paths()
        names = {path.name for path in paths}

        self.assertGreaterEqual(len(paths), 2)
        self.assertTrue(all("real_data" in path.parts for path in paths))
        self.assertTrue(
            {
                "1.หลักการเรียงลำดับข้อมูล-1.pdf",
                "1.หลักการเรียงลำดับข้อมูล-2.pdf",
            }.issubset(names)
        )

    def test_reviewed_scan_sources_are_bound_to_topic_one(self):
        paths = resolve_source_paths()
        names = {path.name for path in paths}
        expected = {
            "Counting_sort.pages",
            "Selection Sort - GeeksforGeeks.pdf",
            "cormen-insertion-sort.pdf",
            "counting sort.pdf",
            "insertion_sort_algorithm.pdf",
            "lecs105.pdf",
            "rohini_37999080689.pdf",
            "selection_sort_algorithm.pdf",
            "การเรียงลำดับแบบเลือก selection.pdf",
        }

        self.assertTrue(expected.issubset(names))

        selection_path = next(
            path
            for path in paths
            if path.name == "การเรียงลำดับแบบเลือก selection.pdf"
        )
        document = parse_pdf(selection_path)
        self.assertEqual(
            document.chunks[0].metadata["topic_id"],
            "topic-01",
        )
        self.assertEqual(
            document.chunks[0].metadata["language"],
            "en-th",
        )

    def test_ingest_cli_includes_reviewed_pages_sources(self):
        names = {path.name for path in approved_ingest_sources()}

        self.assertIn("Counting_sort.pages", names)
        self.assertIn("การเรียงลำดับแบบเลือก selection.pdf", names)

    def test_new_selection_source_exposes_labeled_step_visuals(self):
        selection_path = next(
            path
            for path in resolve_source_paths()
            if path.name == "การเรียงลำดับแบบเลือก selection.pdf"
        )
        document = parse_pdf(
            selection_path,
            extract_images=True,
            render_vector_pages=True,
        )
        visuals = [
            image
            for image in document.images
            if image.metadata.get("user_visible") is True
            and image.metadata.get("visual_topic") == "Selection Sort"
        ]

        self.assertGreaterEqual(len(visuals), 6)
        self.assertTrue(all(image.metadata.get("label") for image in visuals))

    def test_pages_source_keeps_original_identity_and_primary_visual(self):
        pages_path = next(
            path
            for path in resolve_source_paths()
            if path.name == "Counting_sort.pages"
        )
        document = parse_source(
            pages_path,
            extract_images=True,
            render_vector_pages=True,
        )

        self.assertEqual(document.source_file, "Counting_sort.pages")
        self.assertEqual(document.page_count, 3)
        self.assertTrue(
            any(
                image.metadata.get("visual_topic") == "Counting Sort"
                and image.metadata.get("curriculum_status") == "primary"
                and image.metadata.get("user_visible") is True
                for image in document.images
            )
        )

    def test_user_visible_images_never_include_full_pages_or_raw_embeds(self):
        images = [
            ExtractedImage(
                source_id="s",
                source_file="x.pdf",
                page_number=1,
                image_index=0,
                mime_type="image/png",
                image_bytes=b"page",
                metadata={"kind": "vector_page_render"},
            ),
            ExtractedImage(
                source_id="s",
                source_file="x.pdf",
                page_number=1,
                image_index=1,
                mime_type="image/png",
                image_bytes=b"embed",
                metadata={"kind": "embedded_image"},
            ),
            ExtractedImage(
                source_id="s",
                source_file="x.pdf",
                page_number=1,
                image_index=1001,
                mime_type="image/png",
                image_bytes=b"crop",
                metadata={"kind": "figure_crop"},
            ),
            ExtractedImage(
                source_id="s",
                source_file="x.pdf",
                page_number=1,
                image_index=2001,
                mime_type="image/png",
                image_bytes=b"trace",
                metadata={"kind": "trace_crop"},
            ),
        ]

        visible = RAGService.select_user_visible_images(images, limit=3)

        self.assertEqual(len(visible), 2)
        self.assertEqual(
            [image.metadata["kind"] for image in visible],
            ["figure_crop", "trace_crop"],
        )

    def test_user_visible_images_filter_out_other_algorithm(self):
        images = [
            ExtractedImage(
                source_id="s",
                source_file="x.pdf",
                page_number=8,
                image_index=2001,
                mime_type="image/png",
                image_bytes=b"insertion",
                metadata={
                    "kind": "trace_crop",
                    "caption": "การเรียงลำดับข้อมูลแบบ Insertion Sort",
                },
            ),
            ExtractedImage(
                source_id="s",
                source_file="x.pdf",
                page_number=9,
                image_index=2001,
                mime_type="image/png",
                image_bytes=b"bubble",
                metadata={
                    "kind": "trace_crop",
                    "caption": "ภาพขั้นตอน Bubble Sort",
                },
            ),
        ]

        visible = RAGService.select_user_visible_images(
            images,
            limit=3,
            topic="Bubble Sort",
        )

        self.assertEqual([image.image_bytes for image in visible], [b"bubble"])

    def test_image_lookup_is_bound_to_source_and_page(self):
        images = [
            ExtractedImage(
                source_id="source-a",
                source_file="a.pdf",
                page_number=10,
                image_index=1,
                mime_type="image/png",
                image_bytes=b"a",
            ),
            ExtractedImage(
                source_id="source-b",
                source_file="b.pdf",
                page_number=10,
                image_index=1,
                mime_type="image/png",
                image_bytes=b"b",
            ),
        ]
        store = LocalLexicalStore([], images)

        result = store.images_for_references([("source-a", 10)], limit=3)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].source_id, "source-a")
        self.assertEqual(result[0].image_bytes, b"a")

    def test_user_visible_images_survive_chat_rerun_payload(self):
        images = [
            ExtractedImage(
                source_id="source-a",
                source_file="a.pdf",
                page_number=10,
                image_index=2001,
                mime_type="image/png",
                image_bytes=b"crop-bytes",
                metadata={
                    "kind": "trace_crop",
                    "caption": "Bubble Sort รอบที่ 1",
                },
            )
        ]

        payload = image_message_payload(images)

        self.assertEqual(payload[0]["source_id"], "source-a")
        self.assertEqual(payload[0]["page_number"], 10)
        self.assertEqual(payload[0]["image_bytes"], b"crop-bytes")
        self.assertEqual(
            payload[0]["metadata"]["caption"],
            "Bubble Sort รอบที่ 1",
        )

    def test_display_label_prefers_detailed_visual_label(self):
        self.assertEqual(
            display_image_label(
                {"caption": "Bubble Sort", "label": "Bubble Sort รอบที่ 1"},
                1,
            ),
            "Bubble Sort รอบที่ 1",
        )

    def test_machine_manifest_covers_all_81_physical_pages(self):
        paths = resolve_pdf_paths()
        manifest_path = paths[0].parent / "topic_01_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        source_1 = manifest["sources"]["1.หลักการเรียงลำดับข้อมูล-1.pdf"]
        source_2 = manifest["sources"]["1.หลักการเรียงลำดับข้อมูล-2.pdf"]

        self.assertEqual(set(source_1["pages"]), {str(i) for i in range(1, 61)})
        self.assertEqual(set(source_2["pages"]), {str(i) for i in range(1, 22)})
        self.assertTrue(manifest["closed_source"])
        self.assertFalse(manifest["external_content_allowed"])
        self.assertFalse(manifest["external_images_allowed"])

    def test_manifest_covers_the_legacy_textbook_pages(self):
        paths = resolve_pdf_paths()
        manifest_path = paths[0].parent / "topic_01_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        legacy_name = "เอกสารหน่วยที่ 8 การเรียงลำดับข้อมูล.pdf"
        legacy = manifest["sources"][legacy_name]

        self.assertEqual(legacy["physical_pages"], 29)
        self.assertEqual(
            set(legacy["pages"]),
            {str(page) for page in range(1, 30)},
        )

    def test_legacy_textbook_pages_have_curriculum_status(self):
        textbook = next(
            path
            for path in resolve_pdf_paths()
            if path.name.startswith("เอกสารหน่วยที่ 8")
        )
        document = parse_pdf(textbook)

        selection = next(
            chunk for chunk in document.chunks if chunk.page_number == 4
        )
        shell = next(
            chunk for chunk in document.chunks if chunk.page_number == 14
        )

        self.assertEqual(selection.metadata["topic_id"], "topic-01")
        self.assertEqual(selection.metadata["section"], "selection_sort")
        self.assertEqual(selection.metadata["curriculum_status"], "primary")
        self.assertEqual(shell.metadata["section"], "shell_sort")
        self.assertEqual(
            shell.metadata["curriculum_status"],
            "reference_only",
        )

    def test_slide_chunks_mark_reference_only_sections(self):
        slide_pdf = next(
            path
            for path in resolve_pdf_paths()
            if path.name == "1.หลักการเรียงลำดับข้อมูล-1.pdf"
        )
        document = parse_pdf(slide_pdf)

        bubble = next(
            chunk for chunk in document.chunks if chunk.page_number == 17
        )
        cocktail = next(
            chunk for chunk in document.chunks if chunk.page_number == 20
        )

        self.assertEqual(bubble.metadata["curriculum_status"], "primary")
        self.assertEqual(
            cocktail.metadata["curriculum_status"],
            "reference_only",
        )

    def test_mixed_and_comparison_slide_chunks_keep_scope_labels(self):
        slide_pdf = next(
            path
            for path in resolve_pdf_paths()
            if path.name == "1.หลักการเรียงลำดับข้อมูล-2.pdf"
        )
        document = parse_pdf(slide_pdf)

        merge_quick = next(
            chunk for chunk in document.chunks if chunk.page_number == 14
        )
        comparison = next(
            chunk for chunk in document.chunks if chunk.page_number == 21
        )

        self.assertEqual(merge_quick.metadata["curriculum_status"], "mixed")
        self.assertEqual(
            comparison.metadata["curriculum_status"],
            "reference_only",
        )

    def test_legacy_selection_visuals_have_detailed_step_labels(self):
        textbook = next(
            path
            for path in resolve_pdf_paths()
            if path.name.startswith("เอกสารหน่วยที่ 8")
        )
        document = parse_pdf(
            textbook,
            extract_images=True,
            render_vector_pages=True,
        )
        page_5 = [
            image
            for image in document.images
            if image.page_number == 5
            and image.metadata.get("kind") == "trace_crop"
        ]

        self.assertEqual(len(page_5), 3)
        self.assertEqual(
            [image.metadata["visual_step"] for image in page_5],
            [2, 3, 4],
        )
        self.assertTrue(
            all(image.metadata["visual_topic"] == "Selection Sort" for image in page_5)
        )
        self.assertIn("รอบที่ 2", page_5[0].metadata["label"])
        self.assertIn("20 แล้วสลับ", page_5[0].metadata["label"])

    def test_reference_only_visuals_are_not_user_visible(self):
        images = [
            ExtractedImage(
                source_id="s",
                source_file="x.pdf",
                page_number=14,
                image_index=2001,
                mime_type="image/png",
                image_bytes=b"shell",
                metadata={
                    "kind": "trace_crop",
                    "curriculum_status": "reference_only",
                    "visual_topic": "Shell Sort",
                },
            ),
            ExtractedImage(
                source_id="s",
                source_file="x.pdf",
                page_number=5,
                image_index=2001,
                mime_type="image/png",
                image_bytes=b"selection",
                metadata={
                    "kind": "trace_crop",
                    "curriculum_status": "primary",
                    "visual_topic": "Selection Sort",
                },
            ),
        ]

        visible = RAGService.select_user_visible_images(images, limit=3)

        self.assertEqual([image.image_bytes for image in visible], [b"selection"])

    def test_current_real_data_shell_section_is_not_user_visible(self):
        shell_images = []
        for pdf_path in resolve_pdf_paths():
            document = parse_pdf(
                pdf_path,
                extract_images=True,
                render_vector_pages=True,
            )
            shell_images.extend(
                image
                for image in document.images
                if image.metadata.get("section") == "shell_sort"
            )

        self.assertTrue(shell_images)
        self.assertTrue(
            all(
                image.metadata.get("curriculum_status") == "reference_only"
                for image in shell_images
            )
        )
        self.assertEqual(
            RAGService.select_user_visible_images(shell_images, limit=20),
            [],
        )

    def test_local_retrieval_excludes_reference_only_chunks(self):
        store = LocalLexicalStore(
            [
                DocumentChunk(
                    source_id="reference",
                    source_file="reference.pdf",
                    page_number=1,
                    chunk_index=0,
                    content="Shell Sort uses a gap sequence.",
                    metadata={"curriculum_status": "reference_only"},
                ),
                DocumentChunk(
                    source_id="primary",
                    source_file="primary.pdf",
                    page_number=1,
                    chunk_index=0,
                    content="Bubble Sort compares adjacent elements.",
                    metadata={"curriculum_status": "primary"},
                ),
            ]
        )

        hits = store.search(
            "Shell Sort",
            None,
            top_k=3,
            candidate_k=3,
        )

        self.assertTrue(hits)
        self.assertTrue(
            all(
                hit.metadata.get("curriculum_status") != "reference_only"
                for hit in hits
            )
        )
        self.assertNotIn("reference", {hit.source_id for hit in hits})

    def test_legacy_bubble_final_round_has_an_isolated_crop(self):
        textbook = next(
            path
            for path in resolve_pdf_paths()
            if path.name.startswith("เอกสารหน่วยที่ 8")
        )
        document = parse_pdf(
            textbook,
            extract_images=True,
            render_vector_pages=True,
        )
        page_11 = [
            image
            for image in document.images
            if image.page_number == 11
            and image.metadata.get("kind") == "trace_crop"
        ]

        self.assertEqual(len(page_11), 1)
        self.assertEqual(page_11[0].metadata["visual_topic"], "Bubble Sort")
        self.assertEqual(page_11[0].metadata["visual_step"], 5)
        self.assertIn("รอบที่ 5", page_11[0].metadata["label"])

    def test_primary_slide_visuals_carry_topic_labels(self):
        slide_pdf = next(
            path
            for path in resolve_pdf_paths()
            if path.name == "1.หลักการเรียงลำดับข้อมูล-1.pdf"
        )
        slide_document = parse_pdf(
            slide_pdf,
            extract_images=True,
            render_vector_pages=True,
        )
        insertion_visual = next(
            image
            for image in slide_document.images
            if image.page_number == 9
            and image.metadata.get("kind") == "trace_crop"
        )

        self.assertEqual(
            insertion_visual.metadata["visual_topic"],
            "Insertion Sort",
        )
        self.assertIn("sorted prefix", insertion_visual.metadata["label"])

        code_pdf = next(
            path
            for path in resolve_pdf_paths()
            if path.name == "1.หลักการเรียงลำดับข้อมูล-2.pdf"
        )
        code_document = parse_pdf(
            code_pdf,
            extract_images=True,
            render_vector_pages=True,
        )
        page_5 = [
            image
            for image in code_document.images
            if image.page_number == 5
            and image.metadata.get("kind") == "trace_crop"
        ]

        page_4 = [
            image
            for image in code_document.images
            if image.page_number == 4
            and image.metadata.get("kind") == "trace_crop"
        ]

        self.assertEqual(page_4[0].metadata["visual_topic"], "Selection Sort")

        self.assertEqual(
            [image.metadata["visual_topic"] for image in page_5],
            ["Bubble Sort", "Insertion Sort"],
        )

    def test_source_one_worked_example_table_has_an_isolated_crop(self):
        slide_pdf = next(
            path
            for path in resolve_pdf_paths()
            if path.name == "1.หลักการเรียงลำดับข้อมูล-1.pdf"
        )
        document = parse_pdf(
            slide_pdf,
            extract_images=True,
            render_vector_pages=True,
        )
        page_11 = [
            image
            for image in document.images
            if image.page_number == 11
            and image.metadata.get("kind") == "trace_crop"
        ]

        self.assertEqual(len(page_11), 1)
        self.assertEqual(page_11[0].metadata["visual_topic"], "Insertion Sort")

    def test_mixed_slide_keeps_merge_visual_but_hides_heap_visual(self):
        slide_pdf = next(
            path
            for path in resolve_pdf_paths()
            if path.name == "1.หลักการเรียงลำดับข้อมูล-2.pdf"
        )
        document = parse_pdf(
            slide_pdf,
            extract_images=True,
            render_vector_pages=True,
        )
        page_11 = [
            image
            for image in document.images
            if image.page_number == 11
        ]

        visible = RAGService.select_user_visible_images(page_11, limit=3)

        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].metadata["visual_topic"], "Merge Sort")

    def test_counting_sort_example_table_has_a_source_crop(self):
        slide_pdf = next(
            path
            for path in resolve_pdf_paths()
            if path.name == "1.หลักการเรียงลำดับข้อมูล-1.pdf"
        )
        document = parse_pdf(
            slide_pdf,
            extract_images=True,
            render_vector_pages=True,
        )
        page_46 = [
            image
            for image in document.images
            if image.page_number == 46
            and image.metadata.get("kind") == "trace_crop"
        ]

        self.assertEqual(len(page_46), 1)
        self.assertEqual(page_46[0].metadata["visual_topic"], "Counting Sort")
        self.assertIn("count table", page_46[0].metadata["label"])

    def test_source_one_bubble_and_merge_lessons_have_isolated_visuals(self):
        slide_pdf = next(
            path
            for path in resolve_pdf_paths()
            if path.name == "1.หลักการเรียงลำดับข้อมูล-1.pdf"
        )
        document = parse_pdf(
            slide_pdf,
            extract_images=True,
            render_vector_pages=True,
        )

        expected = {
            13: "Selection Sort",
            17: "Bubble Sort",
            19: "Bubble Sort",
            28: "Merge Sort",
            29: "Merge Sort",
            31: "Merge Sort",
        }
        for page_number, visual_topic in expected.items():
            with self.subTest(page_number=page_number):
                crops = [
                    image
                    for image in document.images
                    if image.page_number == page_number
                    and image.metadata.get("kind") == "trace_crop"
                    and image.metadata.get("visual_topic") == visual_topic
                ]
                self.assertEqual(len(crops), 1)
                self.assertTrue(crops[0].metadata.get("label"))
                self.assertNotEqual(
                    crops[0].metadata.get("kind"), "vector_page_render"
                )

    def test_manifest_metadata_is_attached_to_chunks(self):
        source_1 = next(
            path
            for path in resolve_pdf_paths()
            if path.name.endswith("-1.pdf")
        )
        document = parse_pdf(source_1)
        merge_page = next(
            chunk for chunk in document.chunks if chunk.page_number == 28
        )

        self.assertEqual(merge_page.metadata["topic_id"], "topic-01")
        self.assertEqual(
            merge_page.metadata["topic_name"],
            "หลักการเรียงลำดับข้อมูล",
        )
        self.assertEqual(merge_page.metadata["section"], "merge_sort")
        self.assertEqual(
            merge_page.metadata["subtopic"],
            "Merge Sort divide-and-conquer idea",
        )
        self.assertEqual(merge_page.metadata["knowledge_scope"], "real_data")
        self.assertTrue(merge_page.metadata["source_only"])

    def test_manifest_metadata_is_attached_to_internal_images(self):
        source_2 = next(
            path
            for path in resolve_pdf_paths()
            if path.name.endswith("-2.pdf")
        )
        document = parse_pdf(source_2, extract_images=True)
        page_2_image = next(
            image for image in document.images if image.page_number == 2
        )

        self.assertEqual(page_2_image.metadata["section"], "fundamentals")
        self.assertEqual(
            page_2_image.metadata["visual_mode"],
            "embedded_then_render",
        )
        self.assertTrue(page_2_image.metadata["source_only"])

    def test_selection_sort_trace_is_cropped_instead_of_full_page(self):
        textbook = next(
            path
            for path in resolve_pdf_paths()
            if path.name.startswith("เอกสารหน่วยที่ 8")
        )
        document = parse_pdf(
            textbook,
            extract_images=True,
            render_vector_pages=True,
        )
        page_4 = [
            image for image in document.images if image.page_number == 4
        ]
        trace = next(
            image
            for image in page_4
            if image.metadata.get("kind") == "trace_crop"
        )

        self.assertIn("Selection sort", trace.metadata.get("caption", ""))
        self.assertGreater(trace.width, trace.height)
        self.assertFalse(
            any(
                image.metadata.get("kind") == "vector_page_render"
                for image in page_4
            )
        )

    def test_textbook_figure_is_cropped_instead_of_full_page(self):
        textbook = next(
            path
            for path in resolve_pdf_paths()
            if path.name.startswith("เอกสารหน่วยที่ 8")
        )
        document = parse_pdf(
            textbook,
            extract_images=True,
            render_vector_pages=True,
        )
        page_6 = [
            image for image in document.images if image.page_number == 6
        ]
        figure = next(
            image
            for image in page_6
            if image.metadata.get("kind") == "figure_crop"
        )

        self.assertIn("รูปที่ 8.2", figure.metadata.get("caption", ""))
        self.assertLess(figure.height, figure.width)
        self.assertFalse(
            any(
                image.metadata.get("kind") == "vector_page_render"
                for image in page_6
            )
        )


if __name__ == "__main__":
    unittest.main()
