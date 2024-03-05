if type -q register-python-argcomplete &&
   register-python-argcomplete --help | grep -q -- '--shell .*fish'
  register-python-argcomplete --shell fish mypass | .
end
