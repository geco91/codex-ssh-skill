# Live-Einrichtung über AITL, 19.10.2026

Vom Benutzer ausdrücklich freigegebener Test-Proxmox. Die Befehle wurden über
die vorhandene AITL-Anbindung zur lokalen Prüfung übertragen; ausgewertet wurde
die anschließend menschlich geteilte Terminalausgabe. Private Hostnamen,
Bindungscodes und Zugangsdaten bleiben außerhalb dieses Repositorys.

## Beobachtet und ausgeführt

- Proxmox 9.2.2, Debian 13.5, vorhandenes aktives SSH. Die gelesenen
  `qm list`-/`pct list`-Ausgaben zeigten keine Gäste.
- Das Bootstrap wurde vor Ausführung übertragen und auf dem Host per SHA-256
  geprüft: `fed824d64fc8ac8651e3b421ce28ebc7a92b14e8a5e07a5b831e038d0ba33bcb`.
  Dies ist der ausgeführte Snapshot; die spätere lokale Ergänzung der optionalen
  apt-Quelldateiauswahl ist darin noch nicht enthalten.
- Erster Installationslauf: `BOOTSTRAP_EXIT=100`, weil beide aktiven Proxmox-
  Enterprise-Quellen mit `401 Unauthorized` antworteten. Zu diesem Zeitpunkt
  waren die reservierten Installationspfade und das Testkonto noch nicht vorhanden.
- Auf ausdrücklichen Auftrag wurden die originalen Dateien
  `pve-enterprise.sources` und `ceph.sources` gesichert, beide Enterprise-Einträge
  mit `Enabled: no` deaktiviert und `proxmox.sources` mit `pve-no-subscription`
  ergänzt. Ceph-Konfiguration war nicht vorhanden. Bestehender Proxmox-Signaturschlüssel
  bleibt verwendet; keine abgeschaltete Signaturprüfung und kein Paketupgrade.
- Backup auf dem Testhost:
  `/root/codex-ssh-bootstrap-fed824d64fc8/apt-sources-backup`.
- Anschließendes `apt-get update`: `APT_UPDATE_EXIT=0`; die offizielle
  No-Subscription-Paketliste wurde erfolgreich geladen.

Quelle für den Repository-Eintrag:
[offizielle Proxmox-Paketquellen-Dokumentation](https://github.com/proxmox/pve-docs/blob/master/pve-package-repos.adoc).

## Installationsstatus

Der erneute Installationslauf mit `--install --proxmox-admin` endete mit
`BOOTSTRAP_EXIT=0`. Die geteilte Ausgabe belegt:

- slepp-ssh-mcp 0.2.0 in der eigenen venv installiert;
- Tunnel-Client 0.0.16 installiert, beide Upstream-Downloads mit passender Prüfsumme;
- eigener Loopback-SSH-Dienst aktiviert;
- `loopback-ssh-ok` für das Testkonto;
- erfolgreicher Root-Identitäts-/Proxmox-Versionscheck über den eigenen Admin-Alias.

apt installierte vier neue Python-venv/Wheel-Pakete und aktualisierte vier
Python-3.13-Abhängigkeiten von Debian-Revision deb13u2 auf deb13u5. Ein allgemeines
Proxmox-Upgrade fand nicht statt. `--no-upgrade` verhindert nicht jede von einem
neu installierten Paket benötigte Abhängigkeitsaktualisierung.

Ein zusätzlicher lokaler Test des installierten MCP-Programms ist mit
`MCP_LOCAL_OK` belegt: initialize, Tool-Discovery und zwei harmlose `ssh_exec`-
Aufrufe lieferten die erwarteten Ausgaben, Exitcode 0 und keinen Timeout.
Getestet wurden Hello World als `codex-test` und `id -u` über den Proxmox-
Admin-Alias. Beide Konten liegen auf dem Host; die Bezeichnung „guest-account“
im einmaligen Prüfmarker meinte das unprivilegierte Testkonto, keine existierende
Gast-VM. Es wurde weiterhin keine VM erstellt.

Die Runtime-Zugangsdaten wurden anschließend verdeckt lokal unter
`/var/lib/codex-test/.config/codex-ssh/` eingegeben. Die Bestätigung
`TUNNEL_CREDENTIALS_READY` liegt vor; tatsächliche Werte wurden nicht geteilt.
Der vorhandene Tunnel-Client hat den Alias `codex-test-proxmox` gestartet und
anschließend dessen Status gelesen: `process_running=true`, `healthy=true`,
`ready=true`, `CONNECT_EXIT=0`, `STATUS_EXIT=0`. Das Profil liegt unter
`/var/lib/codex-test/.config/codex-ssh/profiles/codex-ssh.yaml` und verwendet eine
Dateireferenz auf den Runtime-Key. Es wurde keine kostenpflichtige
Agentenausführung als Ersatz gestartet.

Das aktive Control-Plane-Polling war im gelesenen Status noch `unknown`
(kein Live-Admin-Systemsnapshot). Eine zusätzliche doctor-/Health-Abfrage wurde
über AITL vorgeschlagen, deren geteiltes Ergebnis steht noch aus. Der Benutzer
meldete die Verbindung des Tunnels als MCP mit dem Namen „Codex-Proxmox“.
In dieser Sitzung sind dessen SSH-Tools bislang nicht sichtbar; kein echter
Aufruf über diese neue Produktverbindung ausgeführt. Lokale Bereitschaft,
Benutzerbericht und bestandene Produkt-End-to-End-Abnahme bleiben getrennt.

Ein erfolgreicher AITL-Rückweg oder apt-Update ist weiterhin kein Nachweis für
SSH-MCP über Secure MCP Tunnel aus Codex. Tunnel-Zuordnung, VM-Anlage,
Gast-Description mit tatsächlichem Test-Login und Integrationstest bleiben
getrennte Abnahmeschritte.
