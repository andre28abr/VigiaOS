# Vigia Common

Helpers compartilhados entre as ferramentas do VigiaOS. Centraliza
código que estava duplicado em ~15 `_helpers.py` por tool.

## Status

v0.1.0 — biblioteca interna. Sem GUI, sem entry point.

## API

### `vigia_common.helpers`

- `make_clamp(child, max_width=820, tightening=640)` — wrapper de
  `Adw.Clamp` com defaults da Vigia
- `show_error(parent, heading, message)` — `Adw.AlertDialog` modal
- `show_info(parent, heading, message)` — variante info
- `make_file_picker_row(title, entry, folder_only=False)` — row com
  Entry + botão de escolha de arquivo/pasta
- `copy_to_clipboard(widget, text)` — clipboard via display

### `vigia_common.markdown`

- `md_to_pango(md)` — converte markdown leve (`**bold**`, `*italic*`,
  `` `code` ``) para Pango markup

### `vigia_common.badges`

- `make_wrapped_packages_bar(packages)` — sub-bar do header com pills

### `vigia_common.layout`

Constantes de layout padronizadas (margens, spacing) usadas pelas tools:
- `MARGIN_OUTER_TOP = 24`
- `MARGIN_OUTER_BOTTOM = 32`
- `MARGIN_OUTER_SIDE = 28`
- `MARGIN_HEADER_LBL_BOTTOM = 8`
- `MARGIN_HEADER_DESC_BOTTOM = 24`
- `MARGIN_GROUP_TOP = 24`
- `MARGIN_ACTION_BOX_TOP = 16`
- `CONTENT_MAX_WIDTH = 820`
- `CONTENT_TIGHTENING = 640`

## Setup

```bash
pip install --user -e tools/vigia-common
# Depois as outras tools podem import: from vigia_common.helpers import make_clamp
```

## Migração

Os arquivos `_helpers.py` em cada tool foram preservados como
**re-exports** do `vigia_common`. Código existente que usa
`from .._helpers import make_clamp` continua funcionando.

Tools novas devem importar direto:
```python
from vigia_common.helpers import make_clamp, show_error, show_info
from vigia_common.markdown import md_to_pango
```
