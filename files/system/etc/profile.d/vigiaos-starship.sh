# VigiaOS — Starship prompt para bash (fallback caso o user ainda nao migrou para zsh).
# Em zsh, o starship eh iniciado via ~/.zshrc (de /etc/skel/.zshrc).

if [ -n "${BASH_VERSION:-}" ] && command -v starship >/dev/null 2>&1; then
    eval "$(starship init bash)"
fi
