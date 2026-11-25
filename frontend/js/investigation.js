
const API_URL = "http://127.0.0.1:8000";

// HTML elements
const bugSelect = document.getElementById("bugSelect");
const refreshButton = document.getElementById("refreshButton");
const pageMessage = document.getElementById("pageMessage");

const bugDetails = document.getElementById("bugDetails");
const progressSection = document.getElementById("progressSection");

const bugHeading = document.getElementById("bugHeading");
const bugId = document.getElementById("bugId");
const bugStatus = document.getElementById("bugStatus");
const bugDate = document.getElementById("bugDate");
const bugDescription = document.getElementById("bugDescription");

// Format dates
function formatDate(dateString) {
    const date = new Date(dateString);

    if (Number.isNaN(date.getTime())) {
        return "Unknown";
    }

    return date.toLocaleString();
}

// Display messages
function showMessage(message, type = "") {
    pageMessage.textContent = message;
    pageMessage.className = `message ${type}`;
}

// Display selected bug details
function displayBug(bug) {
    bugHeading.textContent = bug.title;
    bugId.textContent = `BUG-${bug.id}`;
    bugStatus.textContent = bug.status || "Submitted";
    bugDate.textContent = formatDate(bug.created_at);
    bugDescription.textContent = bug.description;

    bugDetails.classList.remove("hidden");
    progressSection.classList.remove("hidden");

    // Only submission is confirmed by the current backend.
    // Remaining stages require actual AI workflow integration.
    document.getElementById("progressCount").textContent =
        "1 of 6 stages completed";

    document.getElementById("progressPercent").textContent = "17%";

    document.getElementById("progressBar").style.width = "17%";

    document.getElementById("progressNote").textContent =
        "Bug submission is confirmed. Classification, investigation, " +
        "fix generation and verification are awaiting module integration.";
}

// Retrieve an individual bug report
async function loadBugDetails(id) {
    if (!id) {
        bugDetails.classList.add("hidden");
        progressSection.classList.add("hidden");
        return;
    }

    try {
        showMessage("Loading bug report...");

        const response = await fetch(`${API_URL}/bugs/${encodeURIComponent(id)}`);

        if (!response.ok) {
            throw new Error(
                response.status === 404
                    ? "Bug report not found."
                    : "Unable to retrieve bug details."
            );
        }

        const bug = await response.json();

        displayBug(bug);
        showMessage("Bug report loaded successfully.", "success");

    } catch (error) {
        bugDetails.classList.add("hidden");
        progressSection.classList.add("hidden");

        showMessage(error.message, "error");
        console.error("Bug detail error:", error);
    }
}

// Load all bug reports into the dropdown
async function loadBugReports() {
    bugSelect.disabled = true;
    bugSelect.replaceChildren();

    const loadingOption = document.createElement("option");
    loadingOption.value = "";
    loadingOption.textContent = "Loading bug reports...";
    bugSelect.appendChild(loadingOption);

    try {
        const response = await fetch(`${API_URL}/bugs`);

        if (!response.ok) {
            throw new Error("Could not retrieve bug reports.");
        }

        const bugs = await response.json();

        bugSelect.replaceChildren();

        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "-- Select a bug report --";
        bugSelect.appendChild(defaultOption);

        if (bugs.length === 0) {
            showMessage("No bug reports available. Submit a bug first.", "error");
            bugDetails.classList.add("hidden");
            progressSection.classList.add("hidden");
            return;
        }

        bugs.forEach(bug => {
            const option = document.createElement("option");

            option.value = bug.id;
            option.textContent = `BUG-${bug.id} - ${bug.title}`;

            bugSelect.appendChild(option);
        });

        // Support a bug ID passed through the URL.
        const params = new URLSearchParams(window.location.search);
        const requestedId = params.get("bug_id");

        if (
            requestedId &&
            bugs.some(bug => String(bug.id) === requestedId)
        ) {
            bugSelect.value = requestedId;
            await loadBugDetails(requestedId);
        } else {
            bugSelect.value = "";
            bugDetails.classList.add("hidden");
            progressSection.classList.add("hidden");
            showMessage("Select a bug report to view its investigation.");
        }

    } catch (error) {
        bugSelect.replaceChildren();

        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Unable to load bug reports";
        bugSelect.appendChild(option);

        bugDetails.classList.add("hidden");
        progressSection.classList.add("hidden");

        showMessage(
            "Unable to connect to FixProof API. Please start the backend.",
            "error"
        );

        console.error("Bug loading error:", error);

    } finally {
        bugSelect.disabled = false;
    }
}

// When a bug is selected
bugSelect.addEventListener("change", function() {
    const selectedId = bugSelect.value;

    if (selectedId) {
        loadBugDetails(selectedId);

        // Update URL without reloading the page.
        const url = new URL(window.location.href);
        url.searchParams.set("bug_id", selectedId);
        window.history.replaceState({}, "", url);

    } else {
        bugDetails.classList.add("hidden");
        progressSection.classList.add("hidden");
        showMessage("Select a bug report to view its investigation.");

        const url = new URL(window.location.href);
        url.searchParams.delete("bug_id");
        window.history.replaceState({}, "", url);
    }
});

// Refresh
refreshButton.addEventListener("click", loadBugReports);

// Initial loading
document.addEventListener("DOMContentLoaded", loadBugReports);
