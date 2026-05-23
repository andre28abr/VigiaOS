"""Tab Suggestions: lista de melhorias sugeridas pelo Lynis."""

from __future__ import annotations

from ..backend import Finding, LynisReport
from .warnings import FindingsListTab


class SuggestionsTab(FindingsListTab):
    SEVERITY_CSS = "warning"
    EMPTY_TITLE = "Sem suggestions"
    EMPTY_DESC = "Nenhuma sugestao de melhoria. Execute uma auditoria na aba 'Resumo'."

    def _extract_findings(self, report: LynisReport) -> list[Finding]:
        return list(report.suggestions)
