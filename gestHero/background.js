const DEFAULT_SEARCH_URL = "https://www.google.com/search?q=%s";
const DEFAULT_ZOOM_STEP = 0.1;
const DEBUG_LIMIT = 500;
let debugEvents = [];

const getInsertIndex = (tab) =>
  tab && typeof tab.index === "number" ? tab.index + 1 : undefined;

function createTabNextTo(tab, options) {
  const index = getInsertIndex(tab);
  if (typeof index === "number") {
    options.index = index;
  }
  chrome.tabs.create(options);
}

function buildSearchUrl(query, template) {
  if (!query) {
    return null;
  }
  const safeQuery = encodeURIComponent(query);
  const base = template || DEFAULT_SEARCH_URL;
  if (base.includes("%s")) {
    return base.replace("%s", safeQuery);
  }
  return `${base}${safeQuery}`;
}

function openSearchTab(query, template) {
  const url = buildSearchUrl(query, template);
  if (!url) {
    return;
  }
  chrome.tabs.create({ url });
}

function switchTab(offset, tab) {
  if (!tab || typeof tab.index !== "number") {
    return;
  }
  chrome.tabs.query({ currentWindow: true }, (tabs) => {
    if (!tabs || !tabs.length) {
      return;
    }
    let targetIndex = tab.index + offset;
    if (targetIndex < 0) {
      targetIndex = tabs.length - 1;
    } else if (targetIndex >= tabs.length) {
      targetIndex = 0;
    }
    const target = tabs.find((item) => item.index === targetIndex);
    if (target && target.id) {
      chrome.tabs.update(target.id, { active: true });
    }
  });
}

function switchTabEdge(edge, tab) {
  if (!tab) {
    return;
  }
  chrome.tabs.query({ currentWindow: true }, (tabs) => {
    if (!tabs || !tabs.length) {
      return;
    }
    const target = edge === "first" ? tabs[0] : tabs[tabs.length - 1];
    if (target && target.id) {
      chrome.tabs.update(target.id, { active: true });
    }
  });
}

function moveTab(offset, tab) {
  if (!tab || typeof tab.index !== "number" || !tab.id) {
    return;
  }
  chrome.tabs.query({ currentWindow: true }, (tabs) => {
    if (!tabs || !tabs.length) {
      return;
    }
    const maxIndex = tabs.length - 1;
    const targetIndex = Math.min(maxIndex, Math.max(0, tab.index + offset));
    chrome.tabs.move(tab.id, { index: targetIndex });
  });
}

function togglePin(tab) {
  if (!tab || !tab.id) {
    return;
  }
  chrome.tabs.update(tab.id, { pinned: !tab.pinned });
}

function toggleMute(tab) {
  if (!tab || !tab.id || !tab.mutedInfo) {
    return;
  }
  chrome.tabs.update(tab.id, { muted: !tab.mutedInfo.muted });
}

function changeZoom(tab, deltaSteps, zoomStep) {
  if (!tab || !tab.id) {
    return;
  }
  const step = Number(zoomStep) || DEFAULT_ZOOM_STEP;
  chrome.tabs.getZoom(tab.id, (zoom) => {
    if (chrome.runtime.lastError) {
      return;
    }
    const nextZoom = Math.min(5, Math.max(0.25, zoom + deltaSteps * step));
    chrome.tabs.setZoom(tab.id, nextZoom);
  });
}

function resetZoom(tab) {
  if (!tab || !tab.id) {
    return;
  }
  chrome.tabs.setZoom(tab.id, 1);
}

function navigateHistory(tab, direction) {
  if (!tab || !tab.id) {
    return;
  }
  if (direction === "back" && chrome.tabs.goBack) {
    chrome.tabs.goBack(tab.id);
    return;
  }
  if (direction === "forward" && chrome.tabs.goForward) {
    chrome.tabs.goForward(tab.id);
    return;
  }
  chrome.tabs.sendMessage(tab.id, { type: "historyNavigate", direction });
}

function toggleFullscreen(tab) {
  if (!tab || typeof tab.windowId !== "number") {
    return;
  }
  chrome.windows.get(tab.windowId, {}, (win) => {
    if (!win) {
      return;
    }
    const nextState = win.state === "fullscreen" ? "normal" : "fullscreen";
    chrome.windows.update(win.id, { state: nextState });
  });
}

const ACTIONS = {
  new_tab: (tab) => {
    createTabNextTo(tab, { url: "chrome://newtab", active: true });
  },
  new_window: () => {
    chrome.windows.create({ url: "chrome://newtab", focused: true });
  },
  new_incognito_window: () => {
    chrome.windows.create({
      url: "chrome://newtab",
      focused: true,
      incognito: true,
    });
  },
  open_link_new_tab: (tab, message) => {
    if (!message.linkUrl) {
      return;
    }
    createTabNextTo(tab, { url: message.linkUrl, active: true });
  },
  open_link_background_tab: (tab, message) => {
    if (!message.linkUrl) {
      return;
    }
    createTabNextTo(tab, { url: message.linkUrl, active: false });
  },
  open_link_new_window: (tab, message) => {
    if (!message.linkUrl) {
      return;
    }
    chrome.windows.create({ url: message.linkUrl, focused: true });
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
  duplicate_tab: (tab) => {
    if (tab && tab.id) {
      chrome.tabs.duplicate(tab.id);
    }
  },
  toggle_pin_tab: (tab) => {
    togglePin(tab);
  },
  toggle_mute_tab: (tab) => {
    toggleMute(tab);
  },
  switch_tab_right: (tab) => {
    switchTab(1, tab);
  },
  switch_tab_left: (tab) => {
    switchTab(-1, tab);
  },
  switch_tab_first: (tab) => {
    switchTabEdge("first", tab);
  },
  switch_tab_last: (tab) => {
    switchTabEdge("last", tab);
  },
  move_tab_right: (tab) => {
    moveTab(1, tab);
  },
  move_tab_left: (tab) => {
    moveTab(-1, tab);
  },
  go_back: (tab) => {
    navigateHistory(tab, "back");
  },
  go_forward: (tab) => {
    navigateHistory(tab, "forward");
  },
  zoom_in: (tab, message) => {
    changeZoom(tab, 1, message.zoomStep);
  },
  zoom_out: (tab, message) => {
    changeZoom(tab, -1, message.zoomStep);
  },
  zoom_reset: (tab) => {
    resetZoom(tab);
  },
  toggle_fullscreen: (tab) => {
    toggleFullscreen(tab);
  },
  search_selected_text: (tab, message) => {
    if (!message.selectionText) {
      return;
    }
    openSearchTab(message.selectionText, message.searchUrl);
  },
};

function addDebugEvent(event) {
  if (!event) {
    return;
  }
  debugEvents.push(event);
  if (debugEvents.length > DEBUG_LIMIT) {
    debugEvents.shift();
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    return;
  }
  if (message.type === "executeAction") {
    const action = ACTIONS[message.action];
    if (action) {
      action(sender.tab, message);
    }
    return;
  }
  if (message.type === "debugEvent") {
    addDebugEvent(message.event);
    return;
  }
  if (message.type === "getDebugLog") {
    sendResponse({ events: debugEvents });
    return;
  }
  if (message.type === "clearDebugLog") {
    debugEvents = [];
    sendResponse({ ok: true });
  }
});
