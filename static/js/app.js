"use strict"; // Catch accidental globals while handling the form.

const form = document.querySelector("#analyzer"); // Read controls from the analyzer form.
const category = form.elements.category; // Read the selected pattern.
const source = form.elements.text; // Read or replace the original input.
const status = document.querySelector("#status"); // Announce outcomes and errors here.
const results = document.querySelector("#result-content"); // Insert extracted values here.
const submitButtons = form.querySelectorAll("button[type=submit]"); // Disable submissions while a request runs.

const examples = { // Provide one representative value for each validation category.
    email: "user@example.com", // Show a basic email address.
    url: "https://www.example.com/help?q=regex#examples", // Include a path, query, and fragment.
    phone: "(123) 456-7890", // Show the parenthesized format.
    time: "2:30 PM", // Show the full 12-hour format.
    hashtag: "#RegexHackathon", // Show a complete hashtag.
};

let activeRequest; // Track the request associated with the current form values.

function setStatus(message, kind = "neutral") { // Update the visible and spoken status.
    status.textContent = message; // Treat every message as plain text.
    status.dataset.kind = kind; // Style different outcomes in CSS.
}

function setPending(pending) { // Prevent duplicate submissions while the server responds.
    submitButtons.forEach((button) => { // Update both analysis actions.
        button.disabled = pending; // Re-enable this action when the request ends.
    });
}

function resetResults() { // Clear output when the user changes the input or category.
    activeRequest?.abort(); // Cancel a response that would describe old input.
    activeRequest = undefined; // Let the next submission own its own request.
    setPending(false); // Make the controls usable after cancellation.
    results.replaceChildren(); // Remove the previous extraction output.
    setStatus("Ready to analyze."); // Show the current form state.
}

function renderExtraction(matches) { // Show the extracted values in source order.
    if (matches.length === 0) { // Give an empty search a visible outcome.
        setStatus("No matches found."); // Announce the empty result.
        return; // Leave the results list empty.
    }

    const list = document.createElement("ul"); // Group values in an accessible list.
    list.className = "match-list"; // Apply the result list spacing.
    for (const match of matches) { // Render each match without interpreting user input as HTML.
        const item = document.createElement("li"); // Create a row for the value.
        item.textContent = match.value; // Copy the matched text literally.
        list.append(item); // Keep the original match order.
    }
    results.append(list); // Display the list beneath the status message.
    setStatus(matches.length === 1 ? "1 match found." : `${matches.length} matches found.`, "success"); // Announce the count.
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
        const response = await fetch(form.dataset.endpoint, { // Send JSON to the Flask endpoint.
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
            renderExtraction(data.matches); // Update the result panel with the search output.
        }
    } catch (error) { // Handle connection failures and non-JSON responses.
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
