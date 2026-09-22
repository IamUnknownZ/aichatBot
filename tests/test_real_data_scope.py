import json
import unittest

from rag.bootstrap import resolve_pdf_paths
from rag.models import ExtractedImage
from rag.pdf_ingest import parse_pdf
from rag.service import RAGService
from rag.store import LocalLexicalStore


class RealDataScopeTests(unittest.TestCase):
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
        ]

        visible = RAGService.select_user_visible_images(images, limit=3)

        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].metadata["kind"], "figure_crop")

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
