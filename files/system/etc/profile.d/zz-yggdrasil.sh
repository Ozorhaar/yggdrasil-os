# Yggdrasil OS shell flavour (sorted last so it wins over the base image's aliases)

YGG_FF='/usr/bin/fastfetch -c /usr/share/yggdrasil/fastfetch.jsonc'
alias fastfetch="$YGG_FF"
alias neofetch="$YGG_FF"
alias neowofetch="$YGG_FF"
alias yggdrasil="$YGG_FF"

if [ -n "${BASH_VERSION:-}" ] && [[ $- == *i* ]]; then
    # rune prompt:  ᛃ jason@yggdrasil ~/path ᚱ
    if [ -z "${YGG_PLAIN_PROMPT:-}" ]; then
        PS1='\[\e[38;2;200;162;90m\]ᛃ \[\e[38;2;232;220;196m\]\u\[\e[38;2;143;196;224m\]@\h \[\e[38;2;200;162;90m\]\w \[\e[38;2;224;112;58m\]ᚱ\[\e[0m\] '
    fi
    # show the world tree once per login session, in the first terminal opened
    if [ -z "${YGG_NO_GREETING:-}" ] && [ -n "${XDG_RUNTIME_DIR:-}" ] \
       && [ ! -e "$XDG_RUNTIME_DIR/yggdrasil-greeted" ] && command -v fastfetch >/dev/null; then
        touch "$XDG_RUNTIME_DIR/yggdrasil-greeted"
        $YGG_FF
    fi
fi
