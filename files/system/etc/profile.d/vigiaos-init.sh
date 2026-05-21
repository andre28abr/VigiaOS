# VigiaOS — first-run user config sync.
# Sourced por bash/zsh em todo login. Custo: ~1ms quando ja inicializado.

if [ -z "${VIGIAOS_INIT_DONE:-}" ] && [ -x /usr/libexec/vigiaos-sync-user-config ]; then
    if [ ! -e "$HOME/.config/vigiaos/initialized" ]; then
        /usr/libexec/vigiaos-sync-user-config >/dev/null 2>&1 || true
    fi
    export VIGIAOS_INIT_DONE=1
fi
