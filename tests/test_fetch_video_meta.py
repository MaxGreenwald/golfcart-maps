"""fetch_video_meta keeps a full YouTube timestamp, or falls back to midnight UTC."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import fetch_video_meta as F
import town_videos as V


def watch_html(title, simple="Nov 8, 2026", iso=None, desc="A fixture description."):
    import json
    iso_field = f'"publishDate":"{iso}"' if iso else ""
    return (
        f'"publishDate":{{"simpleText":"{simple}"}}'
        f'"dateText":{{"simpleText":"{simple}"}}'
        f"{title}"
        'attributedDescriptionBodyText":{"content":'
        + json.dumps(desc)
        + "}"
        + iso_field
    )


class FetchVideoMeta(unittest.TestCase):
    def test_normalize_keeps_full_timestamp_and_fills_date_only(self):
        self.assertEqual(V.normalize_upload_date("2026-11-08T14:03:00Z"), "2026-11-08T14:03:00Z")
        self.assertEqual(V.normalize_upload_date("2026-11-08T14:03:00+00:00"), "2026-11-08T14:03:00+00:00")
        self.assertEqual(V.normalize_upload_date("2026-11-08T06:03:00-08:00"), "2026-11-08T06:03:00-08:00")
        self.assertEqual(V.normalize_upload_date("2026-11-08"), "2026-11-08T00:00:00Z")
        with self.assertRaises(SystemExit) as caught:
            V.normalize_upload_date("November 8, 2026", "abc")
        self.assertIn("ISO 8601", str(caught.exception))

    def test_parse_watch_keeps_youtube_timestamp(self):
        html = watch_html("Port Aransas Golf Cart Rules", iso="2026-11-08T14:03:00-08:00")
        uploaded, desc = F.parse_watch(html, "Port Aransas Golf Cart Rules")
        self.assertEqual(uploaded, "2026-11-08T14:03:00-08:00")
        self.assertEqual(desc, "A fixture description.")

    def test_parse_watch_falls_back_to_midnight_utc(self):
        html = watch_html("Port Aransas Golf Cart Rules")
        uploaded, desc = F.parse_watch(html, "Port Aransas Golf Cart Rules")
        self.assertEqual(uploaded, "2026-11-08T00:00:00Z")
        self.assertEqual(desc, "A fixture description.")


if __name__ == "__main__":
    unittest.main()
