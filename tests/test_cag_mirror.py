"""tools/cag_mirror.py: which URL to try, what to skip, and that a stopped run resumes."""
import hashlib
import json
import os
import sys
import tempfile
import unittest

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
        self.dir = tempfile.mkdtemp()
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

    def test_stops_cleanly_when_the_disk_is_nearly_full(self):
        done = m.mirror(self.reports(), self.dir, "https://new.cloudfront.net", fetch=self.fetch,
                        sleep=lambda s: None, free_gb=lambda p: 5, min_free_gb=20)
        self.assertEqual(done["stopped"], "disk")
        self.assertEqual(self.calls, [])

    def test_the_held_count_ignores_the_limit(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.run_once(limit=1)
        self.assertIn("2 reports, 0 held, 1 to fetch", buf.getvalue())

    def test_a_non_pdf_answer_is_not_saved(self):
        def fetch(url):
            return 200, b"<html>not found</html>", url
        m.mirror(self.reports()[:1], self.dir, "https://new.cloudfront.net", fetch=fetch,
                 sleep=lambda s: None, free_gb=lambda p: 500)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "2.pdf")))


if __name__ == "__main__":
    unittest.main()
