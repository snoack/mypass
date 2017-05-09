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

(function() {
  var passwordFields = document.querySelectorAll("input[type=password]");

  chrome.runtime.sendMessage(
    {action: "report-document", hasLogin: passwordFields.length > 0},
    function(credentials) {
      if (!credentials)
        return;

      fields: for (var i = 0; i < passwordFields.length; i++) {
        var passwordField = passwordFields[i];

        if (passwordField.form && credentials[0].username)
          for (var j = 0; j < passwordField.form.elements.length; j++) {
            var element = passwordField.form.elements[j];

            if (element.localName == "input" && (element.type == "text" ||
                                                 element.type == "email")) {
              for (var k = 0; k < credentials.length; k++) {
                if (credentials[k].username == element.value) {
                  passwordField.value = credentials[k].password;
                  continue fields;
                }
              }

              element.value = credentials[0].username;
              break;
            }
          }

        passwordField.value = credentials[0].password;
      }
    }
  );
})();
