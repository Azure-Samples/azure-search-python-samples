// Sync Inspector: drives the merge-first ingestion demo panel.
//
// Flow:
//   1. Fetch device list from /api/demo/devices and populate the dropdown.
//   2. On submit, POST to /api/demo/update and capture expectedVersion (the
//      new Cosmos _etag).
//   3. Poll /api/demo/ingestion-status?deviceId=&expectedVersion= every
//      ~1.2s, updating the four-step timeline:
//         write -> pending -> upserting (P0-1 visible) -> consistent.
//   4. Stop polling once we reach `consistent` or hit the timeout.

const deviceSelect = document.getElementById("inspector-device");
const fieldSelect = document.getElementById("inspector-field");
const valueInput = document.getElementById("inspector-value");
const form = document.getElementById("inspector-form");
const submitButton = document.getElementById("inspector-submit");
const hint = document.getElementById("inspector-hint");
const timeline = document.getElementById("inspector-timeline");

const STEPS = ["write", "pending", "upserting", "consistent"];
const POLL_INTERVAL_MS = 1200;
const POLL_TIMEOUT_MS = 90_000;

let currentPollTimer = null;
let currentPollDeadline = 0;
let devicesCache = [];

function setStepState(stepName, state, detail) {
  const node = timeline.querySelector(`.step[data-step="${stepName}"]`);
  if (!node) return;
  node.classList.remove("is-active", "is-done", "is-error");
  if (state) {
    node.classList.add(state);
  }
  if (detail !== undefined) {
    const detailNode = node.querySelector('[data-role="detail"]');
    if (detailNode) detailNode.textContent = detail;
  }
}

function resetTimeline() {
  for (const step of STEPS) {
    setStepState(step, null);
  }
  setStepState("write", null, "Waiting for an update...");
  setStepState("pending", null, "No new chunks at the new deviceVersion yet.");
  setStepState(
    "upserting",
    null,
    "New chunks present alongside the previous version. The index is never blanked."
  );
  setStepState(
    "consistent",
    null,
    "Stale chunks deleted. Only the new deviceVersion remains for this source."
  );
}

async function loadDevices() {
  try {
    const response = await fetch("/api/demo/devices");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    devicesCache = payload.devices || [];
    deviceSelect.innerHTML = "";
    if (!devicesCache.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No devices found - run scripts/seed_cosmos.py";
      deviceSelect.appendChild(opt);
      submitButton.disabled = true;
      return;
    }
    for (const device of devicesCache) {
      const opt = document.createElement("option");
      opt.value = device.id;
      const label = device.name ? `${device.id} - ${device.name}` : device.id;
      opt.textContent = label;
      opt.dataset.tenantId = device.tenantId || "";
      deviceSelect.appendChild(opt);
    }
    submitButton.disabled = false;
  } catch (error) {
    deviceSelect.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = `Failed to load devices: ${error.message}`;
    deviceSelect.appendChild(opt);
    submitButton.disabled = true;
  }
}

function applyStatusPhase(phase, payload) {
  // Always mark the write step done once we begin polling.
  setStepState("write", "is-done");

  const counts = `new=${payload.newChunkCount} stale=${payload.staleChunkCount}`;
  switch (phase) {
    case "pending":
      setStepState("pending", "is-active", `Change feed has not landed new chunks yet (${counts}).`);
      setStepState("upserting", null);
      setStepState("consistent", null);
      break;
    case "upserting":
      setStepState("pending", "is-done", "Change feed fired; new chunks are upserted.");
      setStepState(
        "upserting",
        "is-active",
        `Merge-first window: ${payload.newChunkCount} new chunk(s) live alongside ${payload.staleChunkCount} stale chunk(s).`
      );
      setStepState("consistent", null);
      break;
    case "consistent":
      setStepState("pending", "is-done", "Change feed fired; new chunks are upserted.");
      setStepState("upserting", "is-done", `Stale chunks cleared; ${payload.newChunkCount} chunk(s) at the new version.`);
      setStepState(
        "consistent",
        "is-done",
        `Index is consistent at deviceVersion ${shortVersion(payload.expectedVersion)} (${payload.latestNewIngestionTimestamp || "now"}).`
      );
      break;
    case "missing":
      setStepState(
        "pending",
        "is-error",
        "No chunks at all for this sourceId. Is the Function App running and indexing?"
      );
      break;
    default:
      break;
  }
}

function shortVersion(value) {
  if (!value) return "?";
  return value.length > 16 ? `${value.slice(0, 14)}...` : value;
}

function stopPolling() {
  if (currentPollTimer) {
    clearTimeout(currentPollTimer);
    currentPollTimer = null;
  }
}

async function pollStatus(deviceId, expectedVersion) {
  try {
    const url = new URL("/api/demo/ingestion-status", window.location.origin);
    url.searchParams.set("deviceId", deviceId);
    url.searchParams.set("expectedVersion", expectedVersion);
    const response = await fetch(url);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }

    applyStatusPhase(payload.status, payload);

    if (payload.status === "consistent") {
      stopPolling();
      hint.textContent = "Done. The change has fully landed in Azure AI Search.";
      submitButton.disabled = false;
      return;
    }

    if (Date.now() > currentPollDeadline) {
      stopPolling();
      hint.textContent = "Polling timed out. Check the Function App logs.";
      submitButton.disabled = false;
      return;
    }
    currentPollTimer = setTimeout(
      () => pollStatus(deviceId, expectedVersion),
      POLL_INTERVAL_MS
    );
  } catch (error) {
    stopPolling();
    hint.textContent = `Status error: ${error.message}`;
    submitButton.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  stopPolling();
  resetTimeline();

  const deviceId = deviceSelect.value;
  if (!deviceId) return;
  const selectedOption = deviceSelect.options[deviceSelect.selectedIndex];
  const tenantId = selectedOption?.dataset?.tenantId || "";
  const field = fieldSelect.value;
  const value = valueInput.value.trim();
  if (!value) {
    hint.textContent = "Enter a value for the selected field.";
    return;
  }

  submitButton.disabled = true;
  hint.textContent = "Writing to Cosmos...";
  setStepState("write", "is-active", "Replacing the device document in Cosmos...");

  try {
    const response = await fetch("/api/demo/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deviceId, tenantId, field, value }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }

    setStepState(
      "write",
      "is-done",
      `Cosmos wrote ${field}="${value}" at ${payload.writtenAt}. New deviceVersion ${shortVersion(payload.expectedVersion)}.`
    );
    hint.textContent = "Polling Azure AI Search...";
    currentPollDeadline = Date.now() + POLL_TIMEOUT_MS;
    pollStatus(deviceId, payload.expectedVersion);
  } catch (error) {
    setStepState("write", "is-error", `Cosmos write failed: ${error.message}`);
    hint.textContent = "";
    submitButton.disabled = false;
  }
});

resetTimeline();
loadDevices();
