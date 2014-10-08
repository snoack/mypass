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

function Field(element) {
	this.element = element;

	this._oldValue = null;
	this._newElement = null;

	element.addEventListener("change", this._onChange.bind(this));
}
Field.prototype = {
	_onChange: function() {
		this._oldValue = null;
	},

	set: function(value) {
		this._oldValue = this.element.value;
		this.element.value = value;
	},
	restore: function() {
		if (this._oldValue != null) {
			this.element.value = this._oldValue;
			this._oldValue = null;
		}

		if (this._newElement != null) {
			this._newElement.parentNode.replaceChild(this.element, this._newElement);
			this._newElement = null;
		}
	},
	replace: function(element) {
		element.name = this.element.name;

		element.style.height  = this.element.offsetHeight + 'px';
		element.style.width   = this.element.offsetWidth  + 'px';
		element.style.display = getComputedStyle(this.element).display;

		this.element.parentNode.replaceChild(element, this.element);
		this._newElement = element;
	}
};

function findFields() {
	var usernameField = null;
	var passwordField = null;

	var passwordInput = document.querySelector("input[type=password]");
	if (passwordInput) {
		passwordField = new Field(passwordInput);

		if (passwordInput.form) {
			var usernameInput = passwordInput.form.querySelector("input[type=text],input[type=email]");
			if (usernameInput)
				usernameField = new Field(usernameInput);
		}
	}

	return {username: usernameField, password: passwordField};
}

function getPassword(credentials, username) {
	for (var i = 0; i < credentials.length; i++) {
		var token = credentials[i];

		if (token.username == username)
			return token.password;
	}
}

function createUsernameSelect(credentials, selected) {
	var select = document.createElement("select");

	for (var i = 0; i < credentials.length; i++) {
		var username = credentials[i].username;
		var option = document.createElement("option");

		if (username == selected)
			option.setAttribute("selected", "selected");

		option.value = option.textContent = username;
		select.appendChild(option);
	}

	select.addEventListener("change", function(event) {
		fields.password.set(getPassword(credentials, select.value));
	});

	return select;
}

var fields = findFields();
if (fields.password) {
	chrome.runtime.onMessage.addListener(function(message) {
		switch (message.action) {
			case "reveal-credentials":
				if (message.url == location.href) {
					var credentials = message.credentials;

					var username = credentials[0].username;
					var password = credentials[0].password;

					if (fields.username) {
						if (credentials.length > 1) {
							var username_ = fields.username.element.value;
							var password_ = getPassword(credentials, username_);

							if (password != null) {
								username = username_;
								password = password_;
							}

							fields.username.replace(createUsernameSelect(credentials, username));
						} else if (username) {
							fields.username.set(username);
						}
					}

					fields.password.set(password);
				}
				break;

			case "conceal-credentials":
				if (fields.username)
					fields.username.restore();

				fields.password.restore();
				break;
		}
	});

	chrome.runtime.sendMessage({action: "request-credentials"});
}
