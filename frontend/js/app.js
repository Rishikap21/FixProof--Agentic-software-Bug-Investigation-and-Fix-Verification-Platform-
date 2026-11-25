
const API_URL = "http://127.0.0.1:8000";

// Bug report elements
const bugForm = document.getElementById("bugForm");
const bugTitle = document.getElementById("bugTitle");
const bugDescription = document.getElementById("bugDescription");
const bugTableBody = document.getElementById("bugTableBody");
const formMessage = document.getElementById("formMessage");
const submitButton = document.getElementById("submitButton");
const refreshButton = document.getElementById("refreshButton");

// Project elements
const projectForm = document.getElementById("projectForm");
const projectName = document.getElementById("projectName");
const projectFile = document.getElementById("projectFile");
const projectTableBody = document.getElementById("projectTableBody");
const projectMessage = document.getElementById("projectMessage");
const uploadButton = document.getElementById("uploadButton");
const refreshProjectsButton = document.getElementById("refreshProjectsButton");

// Create safe table cells
function createCell(value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "";
    return cell;
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);

    if (Number.isNaN(date.getTime())) {
        return "Unknown";
    }

    return date.toLocaleString();
}

// Create status badge
function createStatusCell(status) {
    const cell = document.createElement("td");
    const badge = document.createElement("span");

    badge.className = "status-pill";
    badge.textContent = status || "Submitted";

    cell.appendChild(badge);
    return cell;
}

// Display messages
function showMessage(element, message, type) {
    element.textContent = message;
    element.className = `form-message ${type}`;
}

// Update dashboard statistics
function updateStatistics(bugs) {
    const total = bugs.length;

    const investigating = bugs.filter(
        bug => bug.status === "Investigating"
    ).length;

    const verified = bugs.filter(
        bug => bug.status === "Verified"
    ).length;

    const unresolved = bugs.filter(
        bug => !["Verified", "Resolved"].includes(bug.status)
    ).length;

    document.getElementById("totalBugs").textContent = total;
    document.getElementById("investigatingBugs").textContent = investigating;
    document.getElementById("verifiedBugs").textContent = verified;
    document.getElementById("unresolvedBugs").textContent = unresolved;
}

// Load bug reports
async function loadBugs() {
    bugTableBody.replaceChildren();

    const loadingRow = document.createElement("tr");
    const loadingCell = document.createElement("td");

    loadingCell.colSpan = 5;
    loadingCell.className = "empty-state";
    loadingCell.textContent = "Loading bug reports...";

    loadingRow.appendChild(loadingCell);
    bugTableBody.appendChild(loadingRow);

    try {
        const response = await fetch(`${API_URL}/bugs`);

        if (!response.ok) {
            throw new Error("Could not retrieve bug reports.");
        }

        const bugs = await response.json();

        bugTableBody.replaceChildren();
        updateStatistics(bugs);

        if (bugs.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 5;
            cell.className = "empty-state";
            cell.textContent = "No bug reports found. Submit your first bug!";

            row.appendChild(cell);
            bugTableBody.appendChild(row);
            return;
        }

        bugs.forEach(bug => {
            const row = document.createElement("tr");

            row.appendChild(createCell(`#BUG-${bug.id}`));
            row.appendChild(createCell(bug.title));
            row.appendChild(createCell(bug.description));
            row.appendChild(createStatusCell(bug.status));
            row.appendChild(createCell(formatDate(bug.created_at)));

            bugTableBody.appendChild(row);
        });

    } catch (error) {
        bugTableBody.replaceChildren();

        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.className = "empty-state";
        cell.textContent = "Unable to connect to FixProof API.";

        row.appendChild(cell);
        bugTableBody.appendChild(row);

        updateStatistics([]);
        console.error("Bug loading error:", error);
    }
}

// Submit bug report
bugForm.addEventListener("submit", async function(event) {
    event.preventDefault();

    const title = bugTitle.value.trim();
    const description = bugDescription.value.trim();

    if (title.length < 3 || description.length < 5) {
        showMessage(
            formMessage,
            "Please enter a valid title and description.",
            "error"
        );
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";

    try {
        const response = await fetch(`${API_URL}/bugs`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ title, description })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Failed to submit bug report.");
        }

        showMessage(
            formMessage,
            `Bug report #BUG-${result.id} submitted successfully!`,
            "success"
        );

        bugForm.reset();
        await loadBugs();

    } catch (error) {
        showMessage(formMessage, error.message, "error");
        console.error("Submission error:", error);

    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Submit Bug Report →";
    }
});

// Load uploaded projects
async function loadProjects() {
    projectTableBody.replaceChildren();

    const loadingRow = document.createElement("tr");
    const loadingCell = document.createElement("td");

    loadingCell.colSpan = 5;
    loadingCell.className = "empty-state";
    loadingCell.textContent = "Loading projects...";

    loadingRow.appendChild(loadingCell);
    projectTableBody.appendChild(loadingRow);

    try {
        const response = await fetch(`${API_URL}/projects`);

        if (!response.ok) {
            throw new Error("Could not retrieve projects.");
        }

        const projects = await response.json();

        projectTableBody.replaceChildren();

        if (projects.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 5;
            cell.className = "empty-state";
            cell.textContent = "No projects uploaded yet.";

            row.appendChild(cell);
            projectTableBody.appendChild(row);
            return;
        }

        projects.forEach(project => {
            const row = document.createElement("tr");

            row.appendChild(createCell(`#PROJECT-${project.id}`));
            row.appendChild(createCell(project.project_name));
            row.appendChild(createCell(project.original_filename));
            row.appendChild(createStatusCell(project.status));
            row.appendChild(createCell(formatDate(project.created_at)));

            projectTableBody.appendChild(row);
        });

    } catch (error) {
        projectTableBody.replaceChildren();

        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 5;
        cell.className = "empty-state";
        cell.textContent = "Unable to load projects. Check the backend server.";

        row.appendChild(cell);
        projectTableBody.appendChild(row);

        console.error("Project loading error:", error);
    }
}

// Upload ZIP project
projectForm.addEventListener("submit", async function(event) {
    event.preventDefault();

    const name = projectName.value.trim();
    const file = projectFile.files[0];

    if (!name) {
        showMessage(projectMessage, "Please enter a project name.", "error");
        return;
    }

    if (!file) {
        showMessage(projectMessage, "Please select a ZIP file.", "error");
        return;
    }

    if (!file.name.toLowerCase().endsWith(".zip")) {
        showMessage(projectMessage, "Only ZIP files are allowed.", "error");
        return;
    }

    if (file.size > 50 * 1024 * 1024) {
        showMessage(projectMessage, "File size must not exceed 50 MB.", "error");
        return;
    }

    uploadButton.disabled = true;
    uploadButton.textContent = "Uploading...";

    try {
        const formData = new FormData();

        formData.append("project_name", name);
        formData.append("file", file);

        const response = await fetch(`${API_URL}/projects/upload`, {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || "Project upload failed.");
        }

        showMessage(
            projectMessage,
            `Project "${result.project_name}" uploaded successfully! Project ID: ${result.id}`,
            "success"
        );

        projectForm.reset();
        await loadProjects();

    } catch (error) {
        showMessage(projectMessage, error.message, "error");
        console.error("Project upload error:", error);

    } finally {
        uploadButton.disabled = false;
        uploadButton.textContent = "Upload Project →";
    }
});

// Refresh buttons
refreshButton.addEventListener("click", loadBugs);
refreshProjectsButton.addEventListener("click", loadProjects);

// Initial loading
document.addEventListener("DOMContentLoaded", function() {
    loadBugs();
    loadProjects();
});
