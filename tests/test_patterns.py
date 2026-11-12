"""Exercise the regex rules independently of HTTP."""

import unittest  # Use Python's built-in test runner.

from patterns import extract, validate  # Test the same functions the route uses.


class PatternTests(unittest.TestCase):  # Keep the core regex cases together.
    def test_validation_accepts_each_supported_format(self):  # Check whole values.
        examples = {  # Organize the assignment's examples by category.
            "email": ["user@example.com", "firstname.lastname@company.co.uk"],
            "url": ["https://www.example.com", "http://subdomain.example.org/page?q=a.b#part"],
            "phone": ["(123) 456-7890", "123-456-7890", "123.456.7890"],
            "time": ["14:30", "2:30 PM", "12:00 AM", "12:00 PM", "00:00", "23:59"],
            "hashtag": ["#example", "#ThisIsAHashtag", "#Regex_101"],
        }
        for category, values in examples.items():  # Run each category's valid formats.
            for value in values:  # Verify individual examples.
                with self.subTest(category=category, value=value):  # Name any failing format.
                    self.assertTrue(validate(category, f"  {value}\n"))  # Trim before fullmatch.

    def test_validation_rejects_malformed_and_partial_values(self):  # Cover invalid formats.
        examples = {  # Include failures that contain valid-looking substrings.
            "email": ["user@@example.com", "user@example", "user..name@example.com", "See user@example.com"],
            "url": ["https://", "https://-example.com", "https://example..org", "https://example.org-"],
            "phone": ["123-456.7890", "1234-456-7890", "123-456-78900", "(123) 456.7890"],
            "time": ["24:00", "12:60", "13:30 PM", "00:30 AM"],
            "hashtag": ["#", "##example", "abc#example", "#hello-world"],
        }
        for category, values in examples.items():  # Run each category's invalid formats.
            for value in values:  # Keep each format visible in the test output.
                with self.subTest(category=category, value=value):  # Identify the rejected input.
                    self.assertFalse(validate(category, value))  # Require the entire value to match.

    def test_extraction_keeps_text_order_and_inner_punctuation(self):  # Check finditer results.
        cases = {  # Pair each input with its expected list in source order.
            "email": ("(z@example.org), then a@example.com.", ["z@example.org", "a@example.com"]),
            "url": ("(https://example.com/a(b)?x=a.b#tag). http://example.org/path!", [
                "https://example.com/a(b)?x=a.b#tag", "http://example.org/path",
            ]),
            "phone": ("123.456.7890 then (321) 654-0987.", ["123.456.7890", "(321) 654-0987"]),
            "time": ("2:30 PM, 14:30, 12:00 AM", ["2:30 PM", "14:30", "12:00 AM"]),
            "hashtag": ("#ThisIsAHashtag, #Regex_101 and #hello-world", [
                "#ThisIsAHashtag", "#Regex_101", "#hello",
            ]),
        }
        for category, (source, expected) in cases.items():  # Try every extraction pattern.
            with self.subTest(category=category):  # Identify the failing category.
                self.assertEqual(extract(category, source), expected)  # Preserve order and values.

    def test_extraction_skips_fragments_and_returns_empty_list(self):  # Guard token boundaries.
        examples = {  # Include malformed tokens and a sentence with no valid matches.
            "email": "user@@example.com user..name@example.com a@example.com..org a@example.org-",
            "url": "https://-example.com https://example..org https://example.org.-net",
            "phone": "123-456.7890 0123-456-7890 123-456-78901 0-123-456-7890",
            "time": "24:00 12:60 13:30 PM 00:30 AM 114:30 14:30:59",
            "hashtag": "# ##example abc#example",
        }
        for category, source in examples.items():  # Check each category separately.
            with self.subTest(category=category):  # Label the boundary being checked.
                self.assertEqual(extract(category, source), [])  # Skip malformed token fragments.
                self.assertEqual(extract(category, "Nothing to extract."), [])  # Handle no matches.
