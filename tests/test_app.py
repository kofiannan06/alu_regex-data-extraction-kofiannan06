"""Exercise the site's Flask routes using real request and response objects."""

import unittest  # Use the built-in test runner.

from app import app  # Load the same application served locally and on Render.


class AnalyzeTests(unittest.TestCase):  # Group tests of the page and JSON API.
    def setUp(self):  # Give each test an independent Flask client.
        self.client = app.test_client()  # Issue HTTP requests without a live server.

    def analyze(self, category, action, text):  # Submit the normal JSON request shape.
        return self.client.post("/api/analyze", json={  # Send the three documented fields.
            "category": category,  # Select the regex category.
            "action": action,  # Choose validation or extraction.
            "text": text,  # Send the original text.
        })

    def test_homepage_loads(self):  # Verify the main entry point renders.
        response = self.client.get("/")  # Request the page a browser opens first.
        self.assertEqual(response.status_code, 200)  # Expect a successful response.
        self.assertIn("Regex Onboarding Hackathon", response.get_data(as_text=True))  # Check the page title.

    def test_validate_checks_the_whole_trimmed_input(self):  # Cover valid and invalid values.
        valid = self.analyze("email", "validate", " user@example.com \n")  # Include trim characters.
        invalid = self.analyze("email", "validate", "Contact user@example.com")  # Add surrounding text.
        self.assertEqual(valid.status_code, 200)  # Return a result for valid input.
        self.assertEqual(invalid.status_code, 200)  # Return a result for an invalid match, too.
        self.assertIs(valid.json["valid"], True)  # The trimmed address is valid.
        self.assertIs(invalid.json["valid"], False)  # A substring cannot validate the whole input.

    def test_extract_returns_ordered_values(self):  # Exercise extraction through the API.
        response = self.analyze("time", "extract", "At 2:30 PM or 14:30.")  # Use both time formats.
        self.assertEqual(response.status_code, 200)  # Expect extraction to succeed.
        self.assertEqual([match["value"] for match in response.json["matches"]], ["2:30 PM", "14:30"])  # Keep order.

    def test_extract_with_no_matches_returns_an_empty_list(self):  # Cover a valid search with no hits.
        response = self.analyze("phone", "extract", "No phone numbers here.")  # Send nonblank text.
        self.assertEqual(response.status_code, 200)  # A search with zero matches is successful.
        self.assertEqual(response.json["matches"], [])  # Keep the response shape consistent.

    def test_mixed_sample_finds_one_match_per_category(self):  # Pin the Scan All example.
        source = (  # Use the exact two lines from Try example.
            "Contact user@example.com or visit https://www.example.com/help.\n"  # End the URL with punctuation.
            "Call (123) 456-7890 at 2:30 PM. Follow #RegexHackathon."  # Include the full 12-hour time.
        )
        response = self.analyze("all", "extract", source)  # Scan the same input with all five patterns.
        self.assertEqual(response.status_code, 200)  # Expect Scan All to succeed.
        matches = [(match["category"], match["value"]) for match in response.json["matches"]]  # Compare pairs.
        self.assertEqual(matches, [  # Require one match for each category in source order.
            ("email", "user@example.com"),  # Keep the complete address.
            ("url", "https://www.example.com/help"),  # Leave off the sentence period.
            ("phone", "(123) 456-7890"),  # Preserve the formatting.
            ("time", "2:30 PM"),  # Include the meridiem.
            ("hashtag", "#RegexHackathon"),  # Include the leading hash.
        ])

    def test_extract_returns_python_offsets_after_emoji(self):  # Check Unicode and original whitespace.
        response = self.analyze("email", "extract", " \U0001f680 user@example.com\n")  # Include a non-BMP character.
        self.assertEqual(response.status_code, 200)  # Expect Unicode input to be accepted.
        self.assertEqual(response.json["matches"], [  # Pin zero-based, end-exclusive code-point offsets.
            {"category": "email", "value": "user@example.com", "start": 3, "end": 19},  # The emoji counts once.
        ])

    def test_scan_all_preserves_overlapping_matches(self):  # Keep overlaps in the API data.
        source = "https://example.org/#Demo"  # Put a valid hashtag inside the URL fragment.
        response = self.analyze("all", "extract", source)  # Find both categories.
        self.assertEqual(response.status_code, 200)  # An overlap still gives a successful response.
        self.assertEqual(response.json["matches"], [  # Preserve both spans and their original positions.
            {"category": "url", "value": source, "start": 0, "end": 25},  # Return the containing URL.
            {"category": "hashtag", "value": "#Demo", "start": 20, "end": 25},  # Return the nested tag too.
        ])

    def test_validate_rejects_all_categories(self):  # Require a single category for validation.
        response = self.analyze("all", "validate", "user@example.com")  # Try the unavailable combination.
        self.assertEqual(response.status_code, 400)  # Report the invalid action and category pairing.
        self.assertIn("one category", response.json["error"])  # Explain how to run validation.

    def test_payload_errors_are_json(self):  # Cover invalid objects, types and field values.
        valid = {"category": "email", "action": "extract", "text": "input"}  # Start with valid fields.
        invalid_payloads = [  # Change one part of the request at a time.
            ([], "JSON object"),  # Reject a top-level array.
            ({}, "category"),  # Reject an object with missing fields.
            ({"category": "email", "action": "extract"}, "text"),  # Require the text key.
            (dict(valid, category=[]), "category"),  # Reject a non-string category.
            (dict(valid, action=None), "action"),  # Reject a non-string action.
            (dict(valid, text=42), "text"),  # Reject non-string input.
            (dict(valid, category="postal"), "category"),  # Reject unknown categories.
            (dict(valid, action="search"), "action"),  # Reject unknown actions.
            (dict(valid, text=" \n\t"), "blank"),  # Reject whitespace-only input.
        ]
        for payload, keyword in invalid_payloads:  # Verify each bad request independently.
            with self.subTest(payload=payload):  # Show the exact case on failure.
                response = self.client.post("/api/analyze", json=payload)  # Send the malformed object.
                self.assertEqual(response.status_code, 400)  # Mark the request as invalid.
                self.assertIn(keyword, response.json["error"])  # Explain the issue in JSON.

    def test_malformed_json_returns_bad_request(self):  # Distinguish syntax from invalid fields.
        response = self.client.post("/api/analyze", data="{", content_type="application/json")  # Send broken JSON.
        self.assertEqual(response.status_code, 400)  # Reject malformed JSON syntax.
        self.assertIn("JSON", response.json["error"])  # Return a readable syntax error.

    def test_non_json_media_type_is_rejected(self):  # Distinguish JSON from other request formats.
        response = self.client.post("/api/analyze", data="plain text")  # Omit the JSON media type.
        self.assertEqual(response.status_code, 415)  # Report an unsupported media type.
        self.assertIn("application/json", response.json["error"])  # Explain the expected media type.
