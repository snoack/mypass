if type -q register-python-argcomplete3 &&
   register-python-argcomplete3 --help | grep -q -- '--shell .*fish'
  register-python-argcomplete3 --shell fish mypass | .
end
