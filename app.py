"""Serve the analyzer interface and its JSON endpoint."""

from flask import Flask, jsonify, render_template, request  # Use Flask for HTTP and templates.
from werkzeug.exceptions import BadRequest  # Catch JSON syntax errors from Flask.

from patterns import PATTERNS, extract, validate  # Keep regex logic in its own module.

app = Flask(__name__)  # Find templates and static assets relative to this file.

CATEGORIES = {  # Pair each API category with its label in the interface.
    "email": "Email",  # Label email addresses.
    "url": "URL",  # Label web addresses.
    "phone": "Phone",  # Label phone numbers.
    "time": "Time",  # Label clock times.
    "hashtag": "Hashtag",  # Label hashtags.
}


@app.get("/")  # Serve the analyzer at the site root.
def index():  # Render the page with the shared category labels.
    return render_template("index.html", categories=CATEGORIES)  # Let Jinja build the dropdown.


@app.post("/api/analyze")  # Accept analysis requests as JSON.
def analyze():  # Validate the request before calling the regex engine.
    if not request.is_json:  # Check the media type before reading the body.
        return jsonify(error="Send the request as application/json."), 415  # Explain the required format.

    try:  # Parse the body once.
        payload = request.get_json()  # Decode the submitted JSON.
    except BadRequest:  # Flask raises this when the JSON syntax is invalid.
        return jsonify(error="Malformed JSON."), 400  # Keep syntax errors in the API's JSON format.

    if not isinstance(payload, dict):  # Require named fields at the top level.
        return jsonify(error="Send a JSON object with category, action, and text."), 400  # Describe the shape.

    for field in ("category", "action", "text"):  # Require all three inputs to be strings.
        if not isinstance(payload.get(field), str):  # Catch missing fields and incorrect types together.
            return jsonify(error=f"The {field} field must be a string."), 400  # Name the affected field.

    category = payload["category"]  # Read the selected category.
    action = payload["action"]  # Read the requested operation.
    text = payload["text"]  # Keep the original text for extraction.
    if category not in PATTERNS:  # Check the supported category keys.
        return jsonify(error="Unsupported category. Choose email, url, phone, time, or hashtag."), 400  # List valid keys.
    if action not in ("validate", "extract"):  # Allow only the two analyzer actions.
        return jsonify(error="Unsupported action. Choose validate or extract."), 400  # List valid actions.
    if not text.strip():  # Reject input made entirely of whitespace.
        return jsonify(error="Input text cannot be blank."), 400  # Give the user a correction.

    if action == "validate":  # Check whether the whole trimmed value matches.
        return jsonify(category=category, action=action, valid=validate(category, text))  # Return a Boolean result.

    matches = [{"value": value} for value in extract(category, text)]  # Keep matches in source order.
    return jsonify(category=category, action=action, matches=matches)  # Return an empty list when no matches exist.
