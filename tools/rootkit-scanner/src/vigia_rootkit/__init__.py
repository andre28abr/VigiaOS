"""Vigia Rootkit Scanner — wrapper chkrootkit + rkhunter com UI GTK4.

v0.2.0: reescrito do zero usando pattern identico ao Antivirus
(que funciona no Hub embedded). Sem widget compartilhado, sem
KPI cards horizontais — apenas Adw.PreferencesGroup tudo.
"""

__version__ = "0.2.2"
__app_id__ = "br.com.vigia.RootkitScanner"

WRAPPED_PACKAGES = ["chkrootkit", "rkhunter"]
