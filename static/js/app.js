"use strict"; // Catch accidental globals while handling the form.

const form = document.querySelector("#analyzer"); // Read controls from the analyzer form.
const category = form.elements.category; // Read the selected pattern.
const source = form.elements.text; // Read or replace the original input.
const status = document.querySelector("#status"); // Announce outcomes and errors here.
const results = document.querySelector("#result-content"); // Insert extracted values here.
const extractButton = form.querySelector("[value=extract]"); // Control when extraction can run.
const validateButton = form.querySelector("[value=validate]"); // Control when validation can run.
const categoryHint = document.querySelector("#category-hint"); // Explain the Scan All restriction.
const preview = document.querySelector("#preview"); // Reveal the preview after an extraction.
const previewText = document.querySelector("#preview-text"); // Rebuild the submitted text here.
const legend = document.querySelector("#legend"); // Label the preview's highlight colors.

const categoryLabels = new Map(); // Reuse the category labels displayed in the dropdown.
for (const option of category.options) { // Read the options in display order.
    if (option.value !== "all") categoryLabels.set(option.value, option.textContent); // Skip the Scan All label.
}

const examples = { // Provide one representative value for each validation category.
    email: "user@example.com", // Show a basic email address.
    url: "https://www.example.com/help?q=regex#examples", // Include a path, query, and fragment.
    phone: "(123) 456-7890", // Show the parenthesized format.
    time: "2:30 PM", // Show the full 12-hour format.
    hashtag: "#RegexHackathon", // Show a complete hashtag.
    all: "Contact user@example.com or visit https://www.example.com/help.\n" + // Include a URL beside punctuation.
        "Call (123) 456-7890 at 2:30 PM. Follow #RegexHackathon.", // Finish the two-line example.
};

let activeRequest; // Track the request associated with the current form values.

function setStatus(message, kind = "neutral") { // Update the visible and spoken status.
    if (status.textContent !== message) status.textContent = message; // Avoid repeating the same announcement.
    status.dataset.kind = kind; // Style different outcomes in CSS.
}

function setPending(pending) { // Prevent duplicate submissions while the server responds.
    const scanAll = category.value === "all"; // Determine which actions the selection supports.
    extractButton.disabled = pending; // Allow extraction in either category mode.
    validateButton.disabled = pending || scanAll; // Enable validation only for a single category.
    categoryHint.hidden = !scanAll; // Explain why Validate is disabled in Scan All.
}

function resetResults() { // Clear output when the user changes the input or category.
    activeRequest?.abort(); // Cancel a response that would describe old input.
    activeRequest = undefined; // Let the next submission own its own request.
    setPending(false); // Make the controls usable after cancellation.
    results.replaceChildren(); // Remove the previous extraction output.
    preview.hidden = true; // Hide the preview until another extraction succeeds.
    previewText.replaceChildren(); // Release the old preview text and highlights.
    setStatus("Ready to analyze."); // Show the current form state.
}

function matchList(matches) { // Build a list of extracted values in source order.
    const list = document.createElement("ul"); // Group values in an accessible list.
    list.className = "match-list"; // Apply the result list spacing.
    for (const match of matches) { // Render each match without interpreting user input as HTML.
        const item = document.createElement("li"); // Create a row for the value.
        item.textContent = match.value; // Copy the matched text literally.
        list.append(item); // Keep the original match order.
    }
    return list; // Let the caller place the list in the correct group.
}

function matchCount(count) { // Format counts consistently in the results.
    return count === 1 ? "1 match" : `${count} matches`; // Use the correct singular or plural.
}

function renderExtraction(data, text) { // Group matches and draw the original text.
    const scanAll = data.category === "all"; // Show all five group headings only in Scan All.
    const categories = scanAll ? [...categoryLabels.keys()] : [data.category]; // Keep dropdown order.
    const groups = new Map(categories.map((name) => [name, []])); // Include groups with zero matches.
    for (const match of data.matches) { // Keep every match, even when it overlaps another category.
        groups.get(match.category).push(match); // Preserve source order within each group.
    }
    for (const [name, matches] of groups) { // Display each requested category.
        if (scanAll) { // Give each Scan All group a heading and its own count.
            const heading = document.createElement("h3"); // Use the next heading level below Results.
            heading.className = "group-heading"; // Align the label and count.
            heading.textContent = categoryLabels.get(name); // Display the friendly category name.
            const count = document.createElement("span"); // Keep the count beside its category.
            count.textContent = matchCount(matches.length); // Include zero in empty groups.
            heading.append(" ", count); // Separate the label and count in the spoken text.
            results.append(heading); // Place the heading before its matches.
        }
        if (matches.length) results.append(matchList(matches)); // Skip empty lists.
    }

    const total = data.matches.length; // Count all matches, including overlaps.
    setStatus(total ? `${matchCount(total)} found.` : "No matches found.", total ? "success" : "neutral"); // Announce the result.
    renderPreview(text, data.matches, categories); // Preview the input from this request.
}

function renderPreview(text, matches, categories) { // Draw highlights using the server's character spans.
    const offsets = [0]; // Map Python's code-point offset zero to JavaScript offset zero.
    for (const character of text) { // JavaScript iteration advances one Unicode code point at a time.
        offsets.push(offsets[offsets.length - 1] + character.length); // Add one or two UTF-16 code units.
    }

    const ordered = [...matches].sort((first, second) => { // Sort a copy so grouped results keep all matches.
        return first.start - second.start || second.end - first.end; // Prefer the earliest start, then the longest span.
    });
    let cursor = 0; // Track the next unused UTF-16 position.
    for (const match of ordered) { // Render the first eligible match at each position.
        const start = offsets[match.start]; // Convert the match start for string slicing.
        const end = offsets[match.end]; // Convert the end-exclusive offset in the same way.
        if (start < cursor) continue; // Skip a mark that would overlap an earlier mark.
        appendPreviewText("span", text.slice(cursor, start)); // Preserve text before the match.
        const mark = appendPreviewText("mark", text.slice(start, end)); // Wrap just the matched text.
        mark.dataset.category = match.category; // Apply this category's highlight color.
        mark.title = categoryLabels.get(match.category); // Also identify the category in a tooltip.
        cursor = end; // Resume just after the chosen highlight.
    }
    appendPreviewText("span", text.slice(cursor)); // Preserve everything after the last highlight.

    legend.replaceChildren(); // Rebuild the legend for the current selection.
    for (const name of categories) { // Display the category names alongside their colors.
        const item = document.createElement("li"); // Give each category its own legend entry.
        item.dataset.category = name; // Match this entry's color to its highlights.
        item.textContent = categoryLabels.get(name); // Label the color in readable text.
        legend.append(item); // Keep the legend in display order.
    }
    preview.hidden = false; // Reveal the assembled preview.
}

function appendPreviewText(tagName, text) { // Add one highlighted or plain segment.
    const element = document.createElement(tagName); // Create the intended DOM node.
    element.textContent = text; // Preserve literal text, including anything that looks like markup.
    previewText.append(element); // Keep the segments in their original order.
    return element; // Let the caller label highlighted segments.
}

category.addEventListener("change", resetResults); // Refresh the result state when the pattern changes.
source.addEventListener("input", resetResults); // Remove outdated results when the text changes.
document.querySelector("#example").addEventListener("click", () => { // Load the selected sample on request.
    source.value = examples[category.value]; // Use the selected category's example.
    resetResults(); // Clear output that belonged to the prior text.
    source.focus(); // Return focus to the text the user can edit.
});

form.addEventListener("submit", async (event) => { // Handle both actions without a page reload.
    event.preventDefault(); // Keep the input and results on the same page.
    const action = event.submitter?.value ?? "extract"; // Default to Extract for an implicit submission.
    if (action === "validate" && category.value === "all") return; // Guard against an unavailable submission.
    const text = source.value; // Snapshot the exact text for the request.
    if (!text.trim()) { // Give immediate feedback for blank input.
        setStatus("Enter text to analyze.", "error"); // Announce how to fix the input.
        source.focus(); // Move focus to the required field.
        return; // Avoid sending an empty request.
    }

    resetResults(); // Clear any result from the previous submission.
    const controller = new AbortController(); // Allow edits to cancel this request.
    activeRequest = controller; // Track the current request for reset and cleanup.
    setPending(true); // Disable the action buttons during the request.
    setStatus("Analyzing…"); // Announce progress while waiting.
    try { // Handle API failures and network errors in the same result panel.
        const response = await fetch(form.getAttribute("action"), { // Send JSON to the Flask endpoint.
            method: "POST", // Submit the text in the request body.
            headers: { "Content-Type": "application/json" }, // Tell Flask how to decode the body.
            body: JSON.stringify({ category: category.value, action, text }), // Serialize the form values.
            signal: controller.signal, // Stop reading the response when input changes.
        });
        const data = await response.json(); // Read the server's result or error message.
        if (controller.signal.aborted) return; // Ignore a response for a superseded request.
        if (!response.ok) { // Display a readable API error when available.
            setStatus(data.error ?? "The request failed. Try again.", "error"); // Show the error as text.
        } else if (data.action === "validate") { // Report the whole-input result.
            const label = category.selectedOptions[0].textContent; // Use the same label as the dropdown.
            const message = data.valid ? `Valid ${label}.` : `Invalid ${label}.`; // Describe the outcome.
            setStatus(message, data.valid ? "success" : "error"); // Announce and style the result.
        } else { // Render the matches from an Extract request.
            renderExtraction(data, text); // Update both the grouped results and highlighted preview.
        }
    } catch { // Handle connection failures and non-JSON responses.
        if (!controller.signal.aborted) { // Keep intentional cancellations quiet.
            setStatus("Could not complete the request. Try again.", "error"); // Keep the text available for retry.
        }
    } finally { // Clean up even after a failed request.
        if (activeRequest === controller) { // Leave newer requests in control of the buttons.
            activeRequest = undefined; // Clear the completed request.
            setPending(false); // Re-enable both actions.
        }
    }
});

setPending(false); // Enable the available actions after registering the submit handler.
