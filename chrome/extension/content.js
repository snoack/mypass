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

var input = document.querySelector("input[type='password']");

if (input) {
	var oldValue = null;

	input.addEventListener("change", function(event) {
		oldValue = null;
	});

	chrome.runtime.onMessage.addListener(function(message) {
		switch (message.action) {
			case "reveal-password":
				if (message.url == location.href) {
					if (oldValue == null)
						oldValue = input.value;

					input.value = message.password;
				}
				break;

			case "conceal-password":
				if (oldValue != null)
					input.value = oldValue;
				break;
		}
	});

	chrome.runtime.sendMessage({action: "request-password"});
}
