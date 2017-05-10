/*
 * Copyright (c) 2014-2017 Sebastian Noack
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

function revealCredentials(tabId, callback) {
  var pendingFrames = 0;
  var status = "no-login-form";

  var checkDone = function() {
    if (pendingFrames == 0) {
      chrome.runtime.onMessage.removeListener(onMessage);
      callback(status);
    }
  };

  var onMessage = function(message, sender, sendResponse) {
    if (message.action != "report-document" || sender.tab.id != tabId)
      return;

    if (message.hasLogin) {
      chrome.runtime.sendNativeMessage(
        "org.snoack.mypass",
        {action: "get-credentials", url: sender.url},
        function (response) {
          status = response ? response.status : "not-installed";
          sendResponse(response && response.credentials);

          pendingFrames--;
          checkDone();
        }
      );
      return true;
    }

    pendingFrames--;
    checkDone();
  };

  chrome.tabs.executeScript(
    tabId, {file: "content.js", allFrames: true},
    function(results) {
      if (!chrome.runtime.lastError)
        pendingFrames += results.length;
      checkDone();
    }
  );

  chrome.runtime.onMessage.addListener(onMessage);
}

chrome.runtime.onMessage.addListener(function(message, sender, sendResponse) {
  switch (message.action) {
    case "reveal-credentials":
      revealCredentials(message.tabId, sendResponse);
      return true;

    case "unlock-database":
      chrome.runtime.sendNativeMessage("org.snoack.mypass", message, sendResponse);
      return true;
  }
});

chrome.runtime.onInstalled.addListener(function() {
  chrome.contextMenus.create({id: "lock", title: "Lock database", contexts: ["browser_action"]});
});

chrome.contextMenus.onClicked.addListener(function(info) {
	if (info.menuItemId == "lock")
		chrome.runtime.sendNativeMessage("org.snoack.mypass", {action: "lock-database"});
});
