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

var input = document.getElementById("passphrase");

function revealCredentials(tabId) {
  chrome.runtime.sendMessage(
    {action: "reveal-credentials", tabId},
    function(status) {
      document.documentElement.dataset.status = status;

      switch (status) {
        case "database-locked":
          input.focus();
          break;

        case "ok":
          setTimeout(function() { window.close(); }, 1000);
          break;
      }
    }
  );
}

chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
  var tabId = tabs[0].id;

  input.addEventListener("keyup", function(event) {
    if (event.keyCode != 13)
      return;

    chrome.runtime.sendMessage(
      {action: "unlock-database", passphrase: input.value},
      function(response) {
        input.value = ""
        if (response && response.status == "failure")
          document.documentElement.dataset.wrongPassphrase = "";
        else {
          revealCredentials(tabId);
          delete document.documentElement.dataset.wrongPassphrase;
        }
      }
    );
  });

  revealCredentials(tabId);
});

document.addEventListener("click", function(event) {
  if (event.target.localName == 'a' && event.target.href) {
    chrome.tabs.create({url: event.target.href});
    event.preventDefault();
  }
});
