"""tools/cag_mirror.py: which URL to try, what to skip, and that a stopped run resumes."""
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import cag_mirror as m  # noqa: E402

PDF = b"%PDF-1.4 a report"


class Candidates(unittest.TestCase):
    def test_archived_cdn_path_is_moved_to_the_current_host(self):
        got = m.candidates("https://d7i5wg8xwe4hf.cloudfront.net/uploads/download_audit_report/2023/a.pdf",
                           "https://new.cloudfront.net")
        self.assertEqual(got, ["https://new.cloudfront.net/uploads/download_audit_report/2023/a.pdf"])

    def test_an_old_cag_gov_in_path_is_moved_too(self):
        got = m.candidates("https://cag.gov.in/webroot/uploads/download_audit_report/2015/b.pdf",
                           "https://new.cloudfront.net")
        self.assertEqual(got, ["https://new.cloudfront.net/uploads/download_audit_report/2015/b.pdf"])

    def test_no_archived_url_means_no_candidate(self):
        self.assertEqual(m.candidates(None, "https://new.cloudfront.net"), [])


class Run(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        if "detail" in url:
            return 200, b'<a href="https://new.cloudfront.net/uploads/download_audit_report/x/fresh.pdf">', url
        if url.endswith("gone.pdf"):
            return 403, b"", url
        return 200, PDF, url

    def reports(self):
        return [{"id": 2, "pdf_url": "https://d7i5wg8xwe4hf.cloudfront.net/uploads/download_audit_report/x/two.pdf",
                 "detail_url": "https://cag.gov.in/en/audit-report/details/2", "title": "Two"},
                {"id": 1, "pdf_url": "https://d7i5wg8xwe4hf.cloudfront.net/uploads/download_audit_report/x/gone.pdf",
                 "detail_url": "https://cag.gov.in/en/audit-report/details/1", "title": "One"}]

    def manifest(self):
        with open(os.path.join(self.dir, "manifest.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def run_once(self, **kw):
        return m.mirror(self.reports(), self.dir, "https://new.cloudfront.net", fetch=self.fetch,
                        sleep=lambda s: None, free_gb=lambda p: 500, **kw)

    def test_newest_first_saved_with_checksum(self):
        self.run_once()
        man = self.manifest()
        self.assertEqual(self.calls[0], "https://new.cloudfront.net/uploads/download_audit_report/x/two.pdf")
        self.assertEqual(man["2"]["sha256"], hashlib.sha256(PDF).hexdigest())
        self.assertTrue(os.path.exists(os.path.join(self.dir, "2.pdf")))

    def test_a_dead_cdn_path_falls_back_to_the_report_page(self):
        self.run_once()
        man = self.manifest()
        self.assertEqual(man["1"]["url"], "https://new.cloudfront.net/uploads/download_audit_report/x/fresh.pdf")

    def test_a_report_the_index_links_no_pdf_for_is_read_off_its_own_page(self):
        r = {"id": 3, "pdf_url": None, "detail_url": "https://cag.gov.in/en/audit-report/details/3",
             "title": "Three"}
        m.mirror([r], self.dir, "https://new.cloudfront.net", fetch=self.fetch,
                 sleep=lambda s: None, free_gb=lambda p: 500)
        self.assertEqual(self.calls[0], r["detail_url"])
        self.assertEqual(self.manifest()["3"]["url"],
                         "https://new.cloudfront.net/uploads/download_audit_report/x/fresh.pdf")

    def test_a_second_run_fetches_nothing(self):
        self.run_once()
        self.calls.clear()
        self.run_once()
        self.assertEqual(self.calls, [])

    def test_a_file_that_no_longer_matches_its_checksum_is_fetched_again(self):
        self.run_once()
        with open(os.path.join(self.dir, "2.pdf"), "wb") as fh:
            fh.write(b"truncated")
        self.calls.clear()
        self.run_once()
        self.assertEqual(len(self.calls), 1)

    def test_held_files_are_matched_by_size_without_reading_them(self):
        self.run_once()
        self.calls.clear()
        with mock.patch.object(m, "sha", side_effect=AssertionError("hashed a held file")):
            self.run_once()
        self.assertEqual(self.calls, [])

    def test_verify_catches_a_same_size_change_that_the_size_check_cannot(self):
        self.run_once()
        with open(os.path.join(self.dir, "2.pdf"), "wb") as fh:
            fh.write(b"X" * len(PDF))
        self.calls.clear()
        self.run_once()
        self.assertEqual(self.calls, [])
        self.run_once(verify=True)
        self.assertEqual(len(self.calls), 1)

    def test_stops_cleanly_when_the_disk_is_nearly_full(self):
        done = m.mirror(self.reports(), self.dir, "https://new.cloudfront.net", fetch=self.fetch,
                        sleep=lambda s: None, free_gb=lambda p: 5, min_free_gb=20)
        self.assertEqual(done["stopped"], "disk")
        self.assertEqual(self.calls, [])

    def test_the_held_count_ignores_the_limit(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.run_once(limit=1)
        self.assertIn("2 reports, 0 held, 1 to fetch", buf.getvalue())

    def test_a_report_with_no_pdf_anywhere_is_not_asked_again_soon(self):
        def fetch(url):
            self.calls.append(url)
            return 404, b"", url
        run = lambda **kw: m.mirror(self.reports()[:1], self.dir, "https://new.cloudfront.net",  # noqa: E731
                                    fetch=fetch, sleep=lambda s: None, free_gb=lambda p: 500, **kw)
        run()
        self.calls.clear()
        run()
        self.assertEqual(self.calls, [])
        run(retry_missing=True)
        self.assertNotEqual(self.calls, [])

    def test_a_non_pdf_answer_is_not_saved(self):
        def fetch(url):
            return 200, b"<html>not found</html>", url
        m.mirror(self.reports()[:1], self.dir, "https://new.cloudfront.net", fetch=fetch,
                 sleep=lambda s: None, free_gb=lambda p: 500)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "2.pdf")))



def pdf_with(*pages):
    """A real PDF with one page per string, so the merge and the placeholder test are run on
    what PyMuPDF writes and not on stand-in bytes."""
    import fitz
    doc = fitz.open()
    for text in pages:
        doc.new_page().insert_text((72, 72), text)
    return doc.tobytes()


class Parts(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.files = {"toc.pdf": pdf_with("Table of contents"),
                      "ch1.pdf": pdf_with("Chapter 1", "Chapter 1 continued"),
                      "app.pdf": pdf_with("Appendices")}

    def fetch(self, url):
        if "detail" in url:
            links = "".join(f'<a href="https://new.cloudfront.net/uploads/download_audit_report/x/{n}">'
                            for n in ("toc.pdf", "ch1.pdf", "app.pdf", "toc.pdf"))
            return 200, links.encode(), url
        return 200, self.files[url.rsplit("/", 1)[1]], url

    def test_a_report_split_into_chapters_is_saved_whole_in_page_order(self):
        import fitz
        r = {"id": 7, "pdf_url": None, "detail_url": "https://cag.gov.in/en/audit-report/details/7"}
        m.mirror([r], self.dir, "https://new.cloudfront.net", fetch=self.fetch,
                 sleep=lambda s: None, free_gb=lambda p: 500)
        with open(os.path.join(self.dir, "manifest.json"), encoding="utf-8") as fh:
            rec = json.load(fh)["7"]
        self.assertEqual([p["url"].rsplit("/", 1)[1] for p in rec["parts"]],
                         ["toc.pdf", "ch1.pdf", "app.pdf"])
        self.assertEqual(rec["parts"][1]["sha256"], hashlib.sha256(self.files["ch1.pdf"]).hexdigest())
        doc = fitz.open(os.path.join(self.dir, "7.pdf"))
        self.assertEqual([pg.get_text().strip() for pg in doc],
                         ["Table of contents", "Chapter 1", "Chapter 1 continued", "Appendices"])

    def test_numbered_parts_are_joined_in_their_own_order_not_the_page_s(self):
        urls = ["https://h/x/3-Preface-06.pdf", "https://h/x/10-Chapter-6-06.pdf",
                "https://h/x/1-Inner-Cover-06.pdf", "https://h/x/2.-Contents-06.pdf"]
        self.assertEqual([u.rsplit("/", 1)[1] for u in m.reading_order(urls)],
                         ["1-Inner-Cover-06.pdf", "2.-Contents-06.pdf", "3-Preface-06.pdf",
                          "10-Chapter-6-06.pdf"])

    def test_parts_without_a_number_on_every_one_keep_the_page_s_order(self):
        urls = ["https://h/x/Preface.pdf", "https://h/x/2-Chapter.pdf", "https://h/x/Cover.pdf"]
        self.assertEqual(m.reading_order(urls), urls)

    def test_a_missing_chapter_saves_nothing(self):
        def fetch(url):
            return (403, b"", url) if url.endswith("ch1.pdf") else self.fetch(url)
        r = {"id": 7, "pdf_url": None, "detail_url": "https://cag.gov.in/en/audit-report/details/7"}
        m.mirror([r], self.dir, "https://new.cloudfront.net", fetch=fetch,
                 sleep=lambda s: None, free_gb=lambda p: 500)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "7.pdf")))


class Placeholder(unittest.TestCase):
    def test_the_cag_s_stand_in_pages_are_placeholders(self):
        for text in ("Report Not Tabled Yet",
                     '" For the contents of this paragraph/report, printed version of the '
                     'relevant report may be referred to"', ""):
            self.assertTrue(m.is_placeholder(pdf_with(text)), text)

    def test_a_report_is_not(self):
        self.assertFalse(m.is_placeholder(pdf_with("Chapter 1", "Chapter 2")))
        self.assertFalse(m.is_placeholder(pdf_with("Preface. This Report of the CAG for the year "
                                                   "ended 31 March 2021 has been prepared")))

    def test_a_placeholder_is_counted_missing_and_asked_again_later(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        calls = []

        def fetch(url):
            calls.append(url)
            return 200, pdf_with("Report Not Tabled Yet"), url
        r = {"id": 5, "pdf_url": "https://x.net/uploads/download_audit_report/a.pdf", "detail_url": None}
        run = lambda **kw: m.mirror([r], tmp.name, "https://new.cloudfront.net", fetch=fetch,  # noqa: E731
                                    sleep=lambda s: None, free_gb=lambda p: 500, **kw)
        done = run()
        self.assertEqual(done["missing"], 1)
        calls.clear()
        run()
        self.assertEqual(calls, [])
        run(retry_missing=True)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
