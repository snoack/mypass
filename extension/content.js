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

function Form(usernameInput, passwordInputs) {
  this._usernameInput  = usernameInput;
  this._passwordInputs = passwordInputs;

  this._changedValues  = [];
  this._usernameSelect = null;
}
Form.prototype = {
  _set: function(element, value) {
    var onInput = function() {
      var idx = this._changedValues.indexOf(changeInfo);
      if (idx != -1)
        this._changedValues.splice(idx, 1);

      element.removeEventListener("input", onInput);
    }.bind(this);

    var changeInfo = {
      element:  element,
      oldValue: element.value,
      onInput:  onInput
    };
    this._changedValues.push(changeInfo);

    element.value = value;
    element.addEventListener("input", onInput);
  },
  _replace: function(newElement, oldElement) {
    this._replacedElements.push({
      oldElement: oldElement,
      newElement: newElement
    });

    oldElement.parentNode.replaceChild(newElement, oldElement);
  },
  _createUsernameSelect: function(credentials, selected) {
    this._usernameSelect = document.createElement("select");

    this._usernameSelect.style.height  = this._usernameInput.offsetHeight + 'px';
    this._usernameSelect.style.width   = this._usernameInput.offsetWidth  + 'px';
    this._usernameSelect.style.display = getComputedStyle(this._usernameInput).display;

    for (var i = 0; i < credentials.length; i++) {
      var username = credentials[i].username;
      var option = document.createElement("option");

      if (username == selected)
        option.setAttribute("selected", "selected");

      option.value = option.textContent = username;
      this._usernameSelect.appendChild(option);
    }

    this._usernameSelect.addEventListener("change", function() {
      var username = this._usernameSelect.value;
      this._set(this._usernameInput, username);

      var password = getPassword(credentials, username);
      for (var i = 0; i < this._passwordInputs.length; i++)
        this._set(this._passwordInputs[i], password);
    }.bind(this));

    this._usernameInputDisplayValue    = this._usernameInput.style.getPropertyValue("display");
    this._usernameInputDisplayPriority = this._usernameInput.style.getPropertyPriority("display");

    this._usernameInput.style.setProperty("display", "none", "important");
    this._usernameInput.parentNode.insertBefore(this._usernameSelect, this._usernameInput);
  },
  fill: function(credentials) {
    var username = credentials[0].username;
    var password = credentials[0].password;

    if (this._usernameInput) {
      if (credentials.length > 1) {
        var username_ = this._usernameInput.value;
        var password_ = getPassword(credentials, username_);

        if (password_ != null) {
          username = username_;
          password = password_;
        }

        this._createUsernameSelect(credentials, username);
      }

      if (username)
        this._set(this._usernameInput, username);
    }

    for (var i = 0; i < this._passwordInputs.length; i++)
      this._set(this._passwordInputs[i], password);
  },
  restore: function() {
    while (this._changedValues.length > 0) {
      var changeInfo = this._changedValues.shift();
      var element = changeInfo.element;

      element.removeEventListener("input", changeInfo.onInput);
      element.value = changeInfo.oldValue;
    }

    if (this._usernameSelect) {
      this._usernameSelect.parentNode.removeChild(this._usernameSelect);
      this._usernameSelect = null;

      this._usernameInput.style.setProperty(
        "display", this._usernameInputDisplayValue,
                   this._usernameInputDisplayPriority
      );
    }
  }
};

function findForms() {
  var forms = [];

  var passwordInputs = document.querySelectorAll("input[type=password]");
  var seenFormElements = [];

  for (var i = 0; i < passwordInputs.length; i++)
  {
    var passwordInput = passwordInputs[i];
    var formElement = passwordInput.form;

    if (!formElement)
      forms.push(new Form(null, [passwordInput]));
    else if (seenFormElements.indexOf(formElement) == -1) {
      forms.push(new Form(
        formElement.querySelector("input[type=text],input[type=email],input:not([type])"),
        formElement.querySelectorAll("input[type=password]")
      ));

      seenFormElements.push(formElement);
    }
  }

  return forms;
}

function getPassword(credentials, username) {
  for (var i = 0; i < credentials.length; i++) {
    var token = credentials[i];

    if (token.username == username)
      return token.password;
  }
}

var forms = findForms();
if (forms.length > 0) {
  chrome.runtime.onMessage.addListener(function(message) {
    switch (message.action) {
      case "reveal-credentials":
        if (message.url == location.href)
          for (var i = 0; i < forms.length; i++)
            forms[i].fill(message.credentials);
        break;

      case "conceal-credentials":
        for (var i = 0; i < forms.length; i++)
          forms[i].restore();
        break;
    }
  });

  chrome.runtime.sendMessage({action: "request-credentials"});
}
