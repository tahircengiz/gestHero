#!/usr/bin/env python3
import base64
import json
import os
import textwrap


ICON_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
    "ASsJTYQAAAAASUVORK5CYII="
)


MANIFEST = {
    "name": "Simple Gestures",
    "description": "Lightweight mouse gesture controls.",
    "version": "1.0.0",
    "manifest_version": 3,
    "permissions": ["storage", "tabs", "sessions"],
    "host_permissions": ["<all_urls>"],
    "background": {"service_worker": "background.js"},
    "action": {
        "default_title": "Simple Gestures",
        "default_icon": {
            "16": "icon16.png",
            "48": "icon48.png",
            "128": "icon128.png",
        },
    },
    "icons": {
        "16": "icon16.png",
        "48": "icon48.png",
        "128": "icon128.png",
    },
    "options_page": "options.html",
    "content_scripts": [
        {
            "matches": ["<all_urls>"],
            "js": ["content.js"],
            "run_at": "document_idle",
        }
    ],
}


BACKGROUND_JS = textwrap.dedent(
    """
    const ACTIONS = {
      new_tab: (tab) => {
        chrome.tabs.create({ url: "chrome://newtab" });
      },
      close_tab: (tab) => {
        if (tab && tab.id) {
          chrome.tabs.remove(tab.id);
        }
      },
      reload_tab: (tab) => {
        if (tab && tab.id) {
          chrome.tabs.reload(tab.id);
        }
      },
      reopen_closed_tab: () => {
        chrome.sessions.restore();
      },
    };

    chrome.runtime.onMessage.addListener((message, sender) => {
      if (!message || message.type !== "executeAction") {
        return;
      }
      const action = ACTIONS[message.action];
      if (action) {
        action(sender.tab);
      }
    });
    """
).strip() + "\n"


CONTENT_JS = textwrap.dedent(
    """
    const MIN_DISTANCE = 20;
    const DEFAULT_GESTURES = [
      { sequence: "DR", action: "close_tab" },
      { sequence: "UR", action: "new_tab" },
      { sequence: "UD", action: "reload_tab" },
      { sequence: "DL", action: "reopen_closed_tab" },
      { sequence: "U", action: "scroll_top" },
      { sequence: "D", action: "scroll_bottom" },
    ];

    const ACTIONS_LOCAL = new Set(["scroll_top", "scroll_bottom"]);
    let gestureMap = new Map();

    function normalizeSequence(sequence) {
      return String(sequence || "")
        .toUpperCase()
        .replace(/[^UDLR]/g, "");
    }

    function buildGestureMap(gestures) {
      gestureMap = new Map();
      (gestures || []).forEach((item) => {
        const normalized = normalizeSequence(item.sequence);
        if (normalized && item.action) {
          gestureMap.set(normalized, item.action);
        }
      });
    }

    function loadGestures() {
      chrome.storage.sync.get({ gestures: DEFAULT_GESTURES }, (data) => {
        buildGestureMap(data.gestures || DEFAULT_GESTURES);
      });
    }

    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === "sync" && changes.gestures) {
        buildGestureMap(changes.gestures.newValue || DEFAULT_GESTURES);
      }
    });

    loadGestures();

    let gestureActive = false;
    let gestureUsed = false;
    let directions = [];
    let lastX = 0;
    let lastY = 0;
    let lastDrawX = 0;
    let lastDrawY = 0;
    let canvas = null;
    let ctx = null;

    function createCanvas() {
      canvas = document.createElement("canvas");
      canvas.style.position = "fixed";
      canvas.style.left = "0";
      canvas.style.top = "0";
      canvas.style.width = "100vw";
      canvas.style.height = "100vh";
      canvas.style.pointerEvents = "none";
      canvas.style.zIndex = "2147483647";
      document.documentElement.appendChild(canvas);
      ctx = canvas.getContext("2d");
      resizeCanvas();
    }

    function resizeCanvas() {
      if (!canvas || !ctx) {
        return;
      }
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(window.innerWidth * dpr);
      canvas.height = Math.floor(window.innerHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      ctx.lineWidth = 3;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(0, 120, 255, 0.8)";
    }

    function destroyCanvas() {
      if (canvas && canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }
      canvas = null;
      ctx = null;
    }

    function getDirection(dx, dy) {
      if (Math.abs(dx) > Math.abs(dy)) {
        return dx > 0 ? "R" : "L";
      }
      return dy > 0 ? "D" : "U";
    }

    function performLocalAction(action) {
      if (action === "scroll_top") {
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else if (action === "scroll_bottom") {
        window.scrollTo({
          top: document.documentElement.scrollHeight,
          behavior: "smooth",
        });
      }
    }

    function handleGesture(sequence) {
      const action = gestureMap.get(sequence);
      if (!action) {
        return;
      }
      if (ACTIONS_LOCAL.has(action)) {
        performLocalAction(action);
        return;
      }
      chrome.runtime.sendMessage({ type: "executeAction", action });
    }

    function onMouseDown(event) {
      if (event.button !== 2) {
        return;
      }
      gestureActive = true;
      gestureUsed = false;
      directions = [];
      lastX = event.clientX;
      lastY = event.clientY;
      lastDrawX = lastX;
      lastDrawY = lastY;
      createCanvas();
    }

    function onMouseMove(event) {
      if (!gestureActive) {
        return;
      }
      const dx = event.clientX - lastX;
      const dy = event.clientY - lastY;
      if (Math.hypot(dx, dy) < MIN_DISTANCE) {
        return;
      }
      gestureUsed = true;
      const direction = getDirection(dx, dy);
      if (direction && direction !== directions[directions.length - 1]) {
        directions.push(direction);
      }
      if (ctx) {
        ctx.beginPath();
        ctx.moveTo(lastDrawX, lastDrawY);
        ctx.lineTo(event.clientX, event.clientY);
        ctx.stroke();
      }
      lastX = event.clientX;
      lastY = event.clientY;
      lastDrawX = event.clientX;
      lastDrawY = event.clientY;
      event.preventDefault();
    }

    function onMouseUp(event) {
      if (!gestureActive || event.button !== 2) {
        return;
      }
      gestureActive = false;
      destroyCanvas();
      const sequence = directions.join("");
      if (sequence) {
        handleGesture(sequence);
      }
    }

    function onContextMenu(event) {
      if (gestureUsed) {
        event.preventDefault();
        gestureUsed = false;
      }
    }

    window.addEventListener("resize", resizeCanvas);
    document.addEventListener("mousedown", onMouseDown, true);
    document.addEventListener("mousemove", onMouseMove, true);
    document.addEventListener("mouseup", onMouseUp, true);
    document.addEventListener("contextmenu", onContextMenu, true);
    """
).strip() + "\n"


OPTIONS_HTML = textwrap.dedent(
    """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Simple Gestures Options</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f6f6f6;
            color: #222;
          }
          h1 {
            font-size: 20px;
            margin-bottom: 10px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            background: #fff;
          }
          th,
          td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
          }
          input[type="text"] {
            width: 100%;
            padding: 6px;
            box-sizing: border-box;
          }
          select {
            width: 100%;
            padding: 6px;
          }
          button {
            margin-top: 10px;
            padding: 8px 12px;
          }
          .row-actions button {
            margin: 0;
          }
          #status {
            margin-left: 10px;
          }
          .hint {
            font-size: 12px;
            color: #666;
            margin-top: 6px;
          }
        </style>
      </head>
      <body>
        <h1>Simple Gestures</h1>
        <p>Use sequences with U, D, L, R. Example: DR = Down then Right.</p>
        <table>
          <thead>
            <tr>
              <th>Sequence</th>
              <th>Action</th>
              <th>Remove</th>
            </tr>
          </thead>
          <tbody id="gesture-rows"></tbody>
        </table>
        <button id="add-row">Add Gesture</button>
        <button id="save">Save</button>
        <span id="status"></span>
        <p class="hint">Right mouse button: hold and drag to draw a gesture.</p>
        <script src="options.js"></script>
      </body>
    </html>
    """
).strip() + "\n"


OPTIONS_JS = textwrap.dedent(
    """
    const DEFAULT_GESTURES = [
      { sequence: "DR", action: "close_tab" },
      { sequence: "UR", action: "new_tab" },
      { sequence: "UD", action: "reload_tab" },
      { sequence: "DL", action: "reopen_closed_tab" },
      { sequence: "U", action: "scroll_top" },
      { sequence: "D", action: "scroll_bottom" },
    ];

    const ACTIONS = [
      { value: "new_tab", label: "New Tab" },
      { value: "close_tab", label: "Close Tab" },
      { value: "reload_tab", label: "Reload Tab" },
      { value: "reopen_closed_tab", label: "Reopen Closed Tab" },
      { value: "scroll_top", label: "Scroll Top" },
      { value: "scroll_bottom", label: "Scroll Bottom" },
    ];

    const tableBody = document.getElementById("gesture-rows");
    const addRowButton = document.getElementById("add-row");
    const saveButton = document.getElementById("save");
    const status = document.getElementById("status");

    function normalizeSequence(sequence) {
      return String(sequence || "")
        .toUpperCase()
        .replace(/[^UDLR]/g, "");
    }

    function createActionSelect(selected) {
      const select = document.createElement("select");
      ACTIONS.forEach((action) => {
        const option = document.createElement("option");
        option.value = action.value;
        option.textContent = action.label;
        if (action.value === selected) {
          option.selected = true;
        }
        select.appendChild(option);
      });
      return select;
    }

    function addRow(sequence, action) {
      const row = document.createElement("tr");

      const seqCell = document.createElement("td");
      const input = document.createElement("input");
      input.type = "text";
      input.value = sequence || "";
      seqCell.appendChild(input);

      const actionCell = document.createElement("td");
      const select = createActionSelect(action || ACTIONS[0].value);
      actionCell.appendChild(select);

      const removeCell = document.createElement("td");
      removeCell.className = "row-actions";
      const removeButton = document.createElement("button");
      removeButton.textContent = "Remove";
      removeButton.addEventListener("click", () => row.remove());
      removeCell.appendChild(removeButton);

      row.appendChild(seqCell);
      row.appendChild(actionCell);
      row.appendChild(removeCell);
      tableBody.appendChild(row);
    }

    function loadGestures() {
      chrome.storage.sync.get({ gestures: DEFAULT_GESTURES }, (data) => {
        tableBody.innerHTML = "";
        (data.gestures || DEFAULT_GESTURES).forEach((item) => {
          addRow(item.sequence, item.action);
        });
      });
    }

    function saveGestures() {
      const rows = Array.from(tableBody.querySelectorAll("tr"));
      const gestures = rows
        .map((row) => {
          const input = row.querySelector("input");
          const select = row.querySelector("select");
          return {
            sequence: normalizeSequence(input.value),
            action: select.value,
          };
        })
        .filter((item) => item.sequence);
      chrome.storage.sync.set({ gestures }, () => {
        status.textContent = "Saved.";
        setTimeout(() => {
          status.textContent = "";
        }, 1500);
      });
    }

    addRowButton.addEventListener("click", () => addRow("", ACTIONS[0].value));
    saveButton.addEventListener("click", saveGestures);
    loadGestures();
    """
).strip() + "\n"


def write_text(path, content):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_binary(path, data):
    with open(path, "wb") as handle:
        handle.write(data)


def main():
    root = os.path.join(os.getcwd(), "SimpleGestures")
    os.makedirs(root, exist_ok=True)

    write_json(os.path.join(root, "manifest.json"), MANIFEST)
    write_text(os.path.join(root, "background.js"), BACKGROUND_JS)
    write_text(os.path.join(root, "content.js"), CONTENT_JS)
    write_text(os.path.join(root, "options.html"), OPTIONS_HTML)
    write_text(os.path.join(root, "options.js"), OPTIONS_JS)

    icon_bytes = base64.b64decode(ICON_PNG_BASE64)
    write_binary(os.path.join(root, "icon16.png"), icon_bytes)
    write_binary(os.path.join(root, "icon48.png"), icon_bytes)
    write_binary(os.path.join(root, "icon128.png"), icon_bytes)

    print("Created extension in:", root)


if __name__ == "__main__":
    main()
