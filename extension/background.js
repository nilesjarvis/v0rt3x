const HOST_NAME = "com.v0rt3x.ytdlp_bridge";
const MENU_ID = "download-with-ytdlp";

const YT_ID_REGEX = /^[A-Za-z0-9_-]{11}$/;

function extractWatchId(urlString) {
  try {
    const url = new URL(urlString);

    if (url.hostname.endsWith("youtube.com")) {
      if (url.pathname === "/watch") {
        const watchId = url.searchParams.get("v");
        if (watchId && YT_ID_REGEX.test(watchId)) {
          return watchId;
        }
      }

      if (url.pathname.startsWith("/shorts/")) {
        const maybeId = url.pathname.split("/").filter(Boolean)[1] || "";
        if (YT_ID_REGEX.test(maybeId)) {
          return maybeId;
        }
      }
    }

    if (url.hostname === "youtu.be") {
      const maybeId = url.pathname.replace(/^\//, "");
      if (YT_ID_REGEX.test(maybeId)) {
        return maybeId;
      }
    }
  } catch (err) {
    console.error("Failed to parse URL", err);
  }

  return null;
}

function setBadge(text, color = "#1f6feb") {
  browser.action.setBadgeBackgroundColor({ color });
  browser.action.setBadgeText({ text });
}

function setStatus(title, badge, color) {
  browser.action.setTitle({ title });
  setBadge(badge, color);
}

function createNativePort() {
  try {
    return browser.runtime.connectNative(HOST_NAME);
  } catch (err) {
    console.error("Native host connection failed", err);
    return null;
  }
}

function runDownload(watchId) {
  if (!watchId) {
    setStatus("Open a valid YouTube watch page, then click again.", "ERR", "#b42318");
    return;
  }

  const port = createNativePort();
  if (!port) {
    setStatus("Could not connect to native host. Reinstall it and retry.", "ERR", "#b42318");
    return;
  }

  setStatus(`Downloading ${watchId}: 0%`, "0%", "#1f6feb");

  const cleanup = () => {
    try {
      port.disconnect();
    } catch (err) {
      console.warn("Disconnect warning", err);
    }
  };

  port.onMessage.addListener(async (msg) => {
    const type = msg?.type;

    if (type === "progress") {
      const pct = Math.floor(Number(msg.percent || 0));
      if (Number.isFinite(pct)) {
        setStatus(`Downloading ${watchId}: ${pct}%`, `${pct}%`, "#1f6feb");
      }
      return;
    }

    if (type === "done") {
      setStatus(`Download completed for ${watchId}`, "OK", "#137333");
      cleanup();
      return;
    }

    if (type === "error") {
      const detail = typeof msg.error === "string" ? msg.error : "Unknown error";
      setStatus(`Download failed: ${detail}`, "ERR", "#b42318");
      cleanup();
      return;
    }
  });

  port.onDisconnect.addListener(() => {
    const maybeError = browser.runtime.lastError;
    if (maybeError) {
      setStatus(`Native host disconnected: ${maybeError.message}`, "ERR", "#b42318");
    }
  });

  port.postMessage({
    type: "download",
    watchId
  });
}

function getWatchIdFromContext(info, tab) {
  const candidates = [info?.linkUrl, info?.srcUrl, info?.pageUrl, tab?.url];

  for (const candidate of candidates) {
    if (typeof candidate !== "string" || candidate.length === 0) {
      continue;
    }

    const maybeId = extractWatchId(candidate);
    if (maybeId) {
      return maybeId;
    }
  }

  return null;
}

function setupContextMenu() {
  browser.contextMenus.removeAll().finally(() => {
    browser.contextMenus.create({
      id: MENU_ID,
      title: "Download video with yt-dlp",
      contexts: ["link", "video", "page"],
      documentUrlPatterns: ["*://*.youtube.com/*", "*://youtu.be/*"]
    });
  });
}

browser.runtime.onInstalled.addListener(() => {
  setupContextMenu();
});

browser.runtime.onStartup.addListener(() => {
  setupContextMenu();
});

browser.action.onClicked.addListener((tab) => {
  const watchId = extractWatchId(tab?.url || "");
  runDownload(watchId);
});

browser.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== MENU_ID) {
    return;
  }

  const watchId = getWatchIdFromContext(info, tab);
  if (!watchId) {
    setStatus("No valid YouTube video found in the selected context.", "ERR", "#b42318");
    return;
  }

  runDownload(watchId);
});

setupContextMenu();
