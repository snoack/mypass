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

var input = document.getElementById("passphrase");

input.addEventListener("keyup", function(event) {
	if (event.keyCode != 13)
		return;

	chrome.runtime.sendMessage(
		{
			action: "unlock-database",
			passphrase: input.value
		},
		function(success) {
			if (success) {
				window.close();
			} else {
				input.classList.add("error");
				input.value = "";
			}
		}
	);
});

input.addEventListener("input", function(event) {
	input.classList.remove("error");
});
