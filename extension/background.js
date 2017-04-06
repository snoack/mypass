/*
 * Copyright (c) 2014 Sebastian Noack
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 3 of the License, or (at your
 * option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 */

var tabs = {__proto__: null};
var lastError = null;

function setDetails(tabId, url, revealed) {
  var urls = tabs[tabId];

  if (!urls)
    urls = tabs[tabId] = {__proto__: null};

  urls[url] = revealed;
}

function showPageAction(tabId, state) {
  chrome.pageAction.setIcon({
    tabId: tabId,
    path: {
      "19": "icons/" + state + "-19.png",
      "38": "icons/" + state + "-38.png"
    }
  });
  chrome.pageAction.setPopup({
    tabId: tabId,
    popup: state == "locked" ? "popup.html" : ""
  });
  chrome.pageAction.show(tabId);
}

function setLocked() {
  for (var tabId in tabs) {
    tabId = parseInt(tabId);

    showPageAction(tabId, "locked");
    chrome.tabs.sendMessage(tabId, {action: "conceal-credentials"});

    for (var url in tabs[tabId])
      tabs[tabId][url] = false;
  }
}

function setUnlocked() {
  for (var tabId in tabs) {
    tabId = parseInt(tabId);

    for (var url in tabs[tabId]) {
      if (!tabs[tabId][url]) {
        revealCredentials(tabId, url);
        break;
      }
    }
  }
}

function lock() {
  chrome.runtime.sendNativeMessage(
    "org.snoack.mypass",
    {
      action: "lock-database"
    }
  );

  setLocked();
}

function unlock(passphrase, callback) {
  chrome.runtime.sendNativeMessage(
    "org.snoack.mypass",
    {
      action: "unlock-database",
      passphrase: passphrase
    },
    function(response) {
      if (response.status == "ok") {
        callback(true);
        setUnlocked();
        return;
      }

      callback(false);
    }
  );
}

function errorFromResponse(response) {
  if (response)
    return response.status;

  if (/^(Linux\b|MacIntel$)/.test(navigator.platform) && !/\bCrOS\b/.test(navigator.userAgent))
    return "not-installed";

  return "os-not-supported";
}

function revealCredentials(tabId, url) {
  chrome.runtime.sendNativeMessage(
    "org.snoack.mypass",
    {
      action: "get-credentials",
      url: url
    },
    function(response) {
      switch (response && response.status) {
        case "ok":
          chrome.tabs.sendMessage(
            tabId,
            {
              action: "reveal-credentials",
              url: url,
              credentials: response.credentials
            }
          );

        case "no-credentials":
          showPageAction(tabId, "unlocked");
          setDetails(tabId, url, true);
          setUnlocked();
          break;

        default:
          lastError = errorFromResponse(response);
          setDetails(tabId, url, false);
          setLocked();
          break;
      }
    }
  );
}

chrome.tabs.onRemoved.addListener(function(tabId) {
  delete tabs[tabId];
});

chrome.tabs.onUpdated.addListener(function(tabId, changeInfo) {
  if (changeInfo.status == "loading")
    delete tabs[tabId];
});

chrome.runtime.onMessage.addListener(function(message, sender, sendResponse) {
  switch (message.action) {
    case "unlock-database":
      unlock(message.passphrase, sendResponse);
      return true;

    case "request-credentials":
      revealCredentials(sender.tab.id, sender.url);
      return false;

    case "get-last-error":
      sendResponse(lastError);
      return false;
  }
});

chrome.pageAction.onClicked.addListener(lock);
