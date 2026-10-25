import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import coletar_youtube as m


class TestHelpers(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(m.duration_seconds("PT12M35S"), 755)
        self.assertEqual(m.duration_seconds("PT1H2M"), 3720)
        self.assertEqual(m.duration_seconds("P1DT2S"), 86402)
        self.assertEqual(m.duration_seconds("invalid"), 0)

    def test_spreadsheet_safety(self):
        self.assertEqual(m.safe_csv_text("=HYPERLINK(\"x\")"), "'=HYPERLINK(\"x\")")
        self.assertEqual(m.safe_csv_text("opinioes normais"), "opinioes normais")

    def test_csv_header_and_utf8(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dados.csv"
            m.write_csv(path, ["id", "texto"], [{"id": 1, "texto": "programação\nIA"}])
            with path.open(encoding="utf-8-sig", newline="") as f:
                rows = __import__("csv").DictReader(f)
                self.assertEqual(list(rows)[0]["texto"], "programação\nIA")

    def test_report_uses_observed_totals(self):
        with tempfile.TemporaryDirectory() as folder:
            summary = {
                "coleta_utc": "2026-10-25T00:00:00+00:00", "avisos": [],
                "criterios": {"published_after": "2024-01-01T00:00:00Z",
                              "videos_per_topic": 4, "comments_per_video": 100,
                              "min_duration_seconds": 240, "min_comment_count": 50,
                              "max_per_channel": 2},
            }
            videos = [{"grupo_busca": "aprendizado", "video_id": "exemplo",
                       "url_video": "https://www.youtube.com/watch?v=exemplo",
                       "comentarios_coletados": 1}]
            comments = [{"grupo_busca": "aprendizado"}]
            m.write_report(Path(folder), videos, comments, summary)
            report = (Path(folder) / "relatorio_parte1.md").read_text(encoding="utf-8")
            self.assertIn("efetivamente coletados: **1**", report)
            self.assertIn("Meta planejada: ate 12 videos", report)

    @patch("coletar_youtube.api_get")
    def test_comments_pagination_and_deduplication(self, get):
        def thread(comment_id, message):
            return {"snippet": {"topLevelComment": {
                "id": comment_id, "snippet": {"textDisplay": message, "likeCount": 3,
                                              "publishedAt": "2026-10-01T00:00:00Z"}}}}
        get.side_effect = [
            {"items": [thread("c1", "um"), thread("c2", "dois")], "nextPageToken": "P2"},
            {"items": [thread("c2", "dois"), thread("c3", "tres")]},
        ]
        rows = m.fetch_comments("fake-test-key", {"video_id": "abc", "grupo_busca": "aprendizado",
                                                 "url_video": "https://www.youtube.com/watch?v=abc"},
                                5, "2026-10-25T00:00:00Z")
        self.assertEqual([x["comentario_id"] for x in rows], ["c1", "c2", "c3"])
        self.assertEqual(get.call_count, 2)

    @patch("coletar_youtube.video_details")
    @patch("coletar_youtube.api_get")
    def test_video_selection_respects_channel_limit(self, api, details):
        api.return_value = {"items": [{"id": {"videoId": "video_a"}},
                                      {"id": {"videoId": "video_b"}}]}
        def item(vid):
            return {"id": vid, "snippet": {"channelId": "same_channel", "channelTitle": "Canal",
                                               "title": vid, "publishedAt": "2026-03-01T00:00:00Z"},
                    "statistics": {"commentCount": "150", "viewCount": "2000"},
                    "contentDetails": {"duration": "PT10M"}}
        details.return_value = {"video_a": item("video_a"), "video_b": item("video_b")}
        chosen = m.select_videos("fake-key", 2, "2024-01-01T00:00:00Z", 240, 50, 1)
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0]["video_id"], "video_a")


if __name__ == "__main__":
    unittest.main()
