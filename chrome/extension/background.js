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

function setDetails(tabId, url, revealed) {
	var urls = tabs[tabId];

	if (!urls)
		urls = tabs[tabId] = {__proto__: null};

	urls[url] = revealed;
}

function showPageActionLocked(tabId) {
	chrome.pageAction.setIcon({
		tabId: tabId,
		path: {
			"19": "icons/locked-19.png",
			"38": "icons/locked-38.png"
		}
	});
	chrome.pageAction.setPopup({
		tabId: tabId,
		popup: "popup.html"
	});
	chrome.pageAction.show(tabId);
}

function showPageActionUnlocked(tabId) {
	chrome.pageAction.setIcon({
		tabId: tabId,
		path: {
			"19": "icons/unlocked-19.png",
			"38": "icons/unlocked-38.png"
		}
	});
	chrome.pageAction.setPopup({
		tabId: tabId,
		popup: ""
	});
	chrome.pageAction.show(tabId);
}

function setLocked() {
	for (var tabId in tabs) {
		tabId = parseInt(tabId);

		showPageActionLocked(tabId);
		chrome.tabs.sendMessage(tabId, {action: "conceal-password"});

		for (var url in tabs[tabId])
			tabs[tabId][url] = false;
	}
}

function setUnlocked() {
	for (var tabId in tabs) {
		tabId = parseInt(tabId);

		for (var url in tabs[tabId]) {
			if (!tabs[tabId][url]) {
				revealPassword(tabId, url);
				break;
			}
		}
	}
}

function lock() {
	chrome.runtime.sendNativeMessage(
		"org.wallunit.mypass",
		{
			action: "lock-database"
		}
	);

	setLocked();
}

function unlock(passphrase, callback) {
	chrome.runtime.sendNativeMessage(
		"org.wallunit.mypass",
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

function revealPassword(tabId, url) {
	chrome.runtime.sendNativeMessage(
		"org.wallunit.mypass",
		{
			action: "get-password",
			url: url
		},
		function(response) {
			switch (response.status) {
				case "ok":
					chrome.tabs.sendMessage(
						tabId,
						{
							action: "reveal-password",
							url: url,
							password: response.password
						}
					);

				case "no-password":
					showPageActionUnlocked(tabId);
					setDetails(tabId, url, true);
					setUnlocked();
					break;

				case "database-locked":
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

		case "request-password":
			revealPassword(sender.tab.id, sender.url);
			return false;
	}
});

chrome.pageAction.onClicked.addListener(lock);
