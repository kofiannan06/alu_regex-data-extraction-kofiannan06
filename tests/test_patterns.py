"""Exercise the regex rules independently of HTTP."""

import unittest  # Use Python's built-in test runner.

from patterns import extract, validate  # Test the same functions the route uses.


class PatternTests(unittest.TestCase):  # Keep the core regex cases together.
    def test_validation_accepts_each_supported_format(self):  # Check whole values.
        examples = {  # Organize the assignment's examples by category.
            "email": ["user@example.com", "firstname.lastname@company.co.uk"],  # Cover dots in both parts.
            "url": ["https://www.example.com", "http://subdomain.example.org/page?q=a.b#part"],  # Cover both schemes.
            "phone": ["(123) 456-7890", "123-456-7890", "123.456.7890"],  # Cover the three phone styles.
            "time": ["14:30", "2:30 PM", "12:00 AM", "12:00 PM", "00:00", "23:59"],  # Cover clock boundaries.
            "hashtag": ["#example", "#ThisIsAHashtag", "#Regex_101"],  # Cover capitalization and underscores.
        }
        for category, values in examples.items():  # Run each category's valid formats.
            for value in values:  # Verify individual examples.
                with self.subTest(category=category, value=value):  # Name any failing format.
                    self.assertTrue(validate(category, f"  {value}\n"))  # Trim before fullmatch.

    def test_validation_rejects_malformed_and_partial_values(self):  # Cover invalid formats.
        examples = {  # Include failures that contain valid-looking substrings.
            "email": ["user@@example.com", "user@example", "user..name@example.com", "See user@example.com"],  # Reject invalid addresses and prose.
            "url": ["https://", "https://-example.com", "https://example..org", "https://example.org-"],  # Reject invalid hosts.
            "phone": ["123-456.7890", "1234-456-7890", "123-456-78900", "(123) 456.7890"],  # Reject incorrect lengths and separators.
            "time": ["24:00", "12:60", "13:30 PM", "00:30 AM"],  # Reject out-of-range clock values.
            "hashtag": ["#", "##example", "abc#example", "#hello-world"],  # Reject broken hashtag tokens.
        }
        for category, values in examples.items():  # Run each category's invalid formats.
            for value in values:  # Keep each format visible in the test output.
                with self.subTest(category=category, value=value):  # Identify the rejected input.
                    self.assertFalse(validate(category, value))  # Require the entire value to match.

    def test_extraction_keeps_text_order_and_inner_punctuation(self):  # Check finditer results.
        cases = {  # Pair each input with its expected list in source order.
            "email": ("(z@example.org), then a@example.com.", ["z@example.org", "a@example.com"]),  # Trim enclosing punctuation.
            "url": ("(https://example.com/a(b)?x=a.b#tag). http://example.org/path!", [  # Mix internal and enclosing punctuation.
                "https://example.com/a(b)?x=a.b#tag", "http://example.org/path",  # Retain the internal punctuation.
            ]),
            "phone": ("123.456.7890 then (321) 654-0987.", ["123.456.7890", "(321) 654-0987"]),  # Keep each number's separators.
            "time": ("2:30 PM, 14:30, 12:00 AM", ["2:30 PM", "14:30", "12:00 AM"]),  # Keep both meridiem suffixes.
            "hashtag": ("#ThisIsAHashtag, #Regex_101 and #hello-world", [  # Include a hyphenated token.
                "#ThisIsAHashtag", "#Regex_101", "#hello",  # Stop the final match at the hyphen.
            ]),
        }
        for category, (source, expected) in cases.items():  # Try every extraction pattern.
            with self.subTest(category=category):  # Identify the failing category.
                values = [match["value"] for match in extract(category, source)]  # Read the extracted text.
                self.assertEqual(values, expected)  # Preserve order and values.

    def test_extraction_skips_fragments_and_returns_empty_list(self):  # Guard token boundaries.
        examples = {  # Include malformed tokens and a sentence with no valid matches.
            "email": "user@@example.com user..name@example.com a@example.com..org a@example.org-",  # Skip invalid local and domain fragments.
            "url": "https://-example.com https://example..org https://example.org.-net",  # Skip valid-looking hostname prefixes.
            "phone": "123-456.7890 0123-456-7890 123-456-78901 0-123-456-7890",  # Skip fragments of longer numbers.
            "time": "24:00 12:60 13:30 PM 00:30 AM 114:30 14:30:59",  # Skip invalid times and unsupported seconds.
            "hashtag": "# ##example abc#example",  # Skip empty, doubled, and attached hashes.
        }
        for category, source in examples.items():  # Check each category separately.
            with self.subTest(category=category):  # Label the boundary being checked.
                self.assertEqual(extract(category, source), [])  # Skip malformed token fragments.
                self.assertEqual(extract(category, "Nothing to extract."), [])  # Handle no matches.

    def test_url_extraction_distinguishes_quotation_from_inner_punctuation(self):  # Test quoted prose.
        source = "Read “https://example.org/o'neill?q=a,b.”"  # Use smart quotes around a punctuated URL.
        values = [match["value"] for match in extract("url", source)]  # Read the extracted URL text.
        self.assertEqual(values, ["https://example.org/o'neill?q=a,b"])  # Keep the apostrophe and comma inside.

    def test_time_extraction_allows_a_sentence_colon(self):  # Distinguish punctuation from seconds.
        source = "At 2:30 PM: first talk. At 14:30: second talk."  # Place a colon after each time format.
        values = [match["value"] for match in extract("time", source)]  # Read both extracted times.
        self.assertEqual(values, ["2:30 PM", "14:30"])  # Exclude the sentence punctuation.

    def test_email_extraction_skips_unsupported_local_part_suffixes(self):  # Check malformed tokens in prose.
        source = r"bad\name@example.com user!name@example.com O'Name@example.org 'ok@example.com'"  # Mix bad tokens with a quote.
        values = [match["value"] for match in extract("email", source)]  # Read all extracted addresses.
        self.assertEqual(values, ["ok@example.com"])  # Keep only the complete, supported address.
