"""Testes para constantes de layout em vigia_common.

Garantem que os valores nao mudem acidentalmente — se mudarem, todos
os 16 _helpers.py das tools podem ficar visualmente inconsistentes.
"""

from __future__ import annotations

import vigia_common


def test_margin_outer_top():
    assert vigia_common.MARGIN_OUTER_TOP == 24


def test_margin_outer_bottom():
    assert vigia_common.MARGIN_OUTER_BOTTOM == 32


def test_margin_outer_side():
    assert vigia_common.MARGIN_OUTER_SIDE == 28


def test_margin_header_lbl_bottom():
    assert vigia_common.MARGIN_HEADER_LBL_BOTTOM == 8


def test_margin_header_desc_bottom():
    assert vigia_common.MARGIN_HEADER_DESC_BOTTOM == 24


def test_margin_group_top():
    assert vigia_common.MARGIN_GROUP_TOP == 24


def test_margin_action_box_top():
    assert vigia_common.MARGIN_ACTION_BOX_TOP == 16


def test_content_max_width():
    assert vigia_common.CONTENT_MAX_WIDTH == 820


def test_content_tightening():
    assert vigia_common.CONTENT_TIGHTENING == 640


def test_consistency_margins_are_positive():
    """Sanidade: todas as margens devem ser positivas."""
    constants = [
        vigia_common.MARGIN_OUTER_TOP,
        vigia_common.MARGIN_OUTER_BOTTOM,
        vigia_common.MARGIN_OUTER_SIDE,
        vigia_common.MARGIN_HEADER_LBL_BOTTOM,
        vigia_common.MARGIN_HEADER_DESC_BOTTOM,
        vigia_common.MARGIN_GROUP_TOP,
        vigia_common.MARGIN_ACTION_BOX_TOP,
    ]
    for c in constants:
        assert c > 0


def test_content_tightening_smaller_than_max():
    """CONTENT_TIGHTENING deve ser <= CONTENT_MAX_WIDTH."""
    assert vigia_common.CONTENT_TIGHTENING <= vigia_common.CONTENT_MAX_WIDTH
