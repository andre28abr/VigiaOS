# VigiaOS — zsh defaults
# Copiado para ~/.zshrc em usuarios novos (via /etc/skel/).
# Edite a vontade no seu home.

# ====== Historico ======
HISTFILE=~/.zsh_history
HISTSIZE=50000
SAVEHIST=50000
setopt SHARE_HISTORY HIST_IGNORE_DUPS HIST_IGNORE_SPACE HIST_VERIFY EXTENDED_HISTORY

# ====== Completion ======
autoload -Uz compinit && compinit -i
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'   # case-insensitive
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"

# ====== Key bindings ======
bindkey -e                                     # emacs mode (CTRL+A, CTRL+E, etc.)
bindkey '^[[A' history-search-backward         # arrow up: busca historico pelo prefixo
bindkey '^[[B' history-search-forward
bindkey '^[[H' beginning-of-line
bindkey '^[[F' end-of-line

# ====== Plugins (instalados via dnf) ======
[ -r /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ] && \
    source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh
[ -r /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ] && \
    source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

# ====== Cor do autosuggestion (combinar com zinc-500) ======
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#71717a'

# ====== Aliases ======
alias ll='ls -alF --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'
alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias gs='git status --short --branch'
alias gd='git diff'
alias gl='git log --oneline --graph --decorate -20'
alias k='kubectl'

# ====== VigiaOS branding ======
export VIGIAOS_USER=1

# ====== Starship prompt ======
command -v starship >/dev/null && eval "$(starship init zsh)"
