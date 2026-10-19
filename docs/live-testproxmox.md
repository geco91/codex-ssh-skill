# Live-Einrichtung und erster MCP-/Gast-Test, 19.10.2026

Vom Benutzer ausdrücklich freigegebener Test-Proxmox. Die Befehle wurden über
die vorhandene AITL-Anbindung zur lokalen Prüfung übertragen; ausgewertet wurde
die anschließend menschlich geteilte Terminalausgabe. Private Hostnamen,
Bindungscodes und Zugangsdaten bleiben außerhalb dieses Repositorys.
Die folgenden Abschnitte bis „Erste Produkt-MCP-/Gast-Abnahme“ beschreiben den
früheren AITL-Prüfstand; der spätere Nachweis folgt am Ende.

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

## Erste Produkt-MCP-/Gast-Abnahme

In der anschließenden Sitzung waren die SSH-Werkzeuge der ausgewählten
Codex-Proxmox-Produktverbindung tatsächlich angeboten und aufrufbar. Ein direkter
Anmeldeversuch mit der privaten Hostadresse wurde nach ausdrücklich freigegebenem
TOFU mit Exitcode 255 (`Permission denied`) beendet. Das genannte Passwort wurde
dabei nicht übergeben; dies war kein Nachweis eines falschen Passworts. Auch die
versuchte MCP-Session öffnete keinen bedienbaren SSH-Passwortprompt.

Nach Recherche im Repository wurde der bereits eingerichtete Alias
`codex-proxmox-host` mit strikter Hostschlüsselprüfung verwendet. Der begrenzte
Identitätsaufruf lieferte Exitcode 0, root und das erwartete Arbeitsverzeichnis.
Die Maschinen-ID stimmte mit dem beim Bootstrap hinterlegten lokalen Manifest
überein. Der Admin-Alias nutzte also die vorhandene Schlüssel-/Hostbindung;
er benötigte den TOFU-Schritt der direkten Verbindung nicht.

Der Bestand enthielt noch keine VMs. Im beauftragten Ressourcenrahmen wurde
eine Debian-13-Test-VM mit einer CPU, 1024 MiB RAM und 8 GiB Systemdisk angelegt.
Verwendet wurde das offizielle `debian-13-generic-amd64.qcow2` aus
`https://cloud.debian.org/images/cloud/trixie/latest/`, geprüft gegen die per
HTTPS gelieferte SHA512SUMS-Datei. Die tatsächlich verwendete Prüfsumme ist in
der lokalen VM-Akte hinterlegt. Das ist ein Prüfsummennachweis, kein zusätzlich
durchgeführter Signaturnachweis. Die vorhandene Bridge transportierte bereits
das beauftragte Gastnetz; ein zusätzliches Gast-VLAN-Tag wurde nicht gesetzt.
Private Adressen, Maschinenkennungen, Schlüssel und Gastpasswort stehen nicht
in diesem öffentlichen Protokoll.

Der erste Start zeigte Netzwerkboot und „No bootable device“. Die gespeicherte
Bootreihenfolge enthielt die Systemdisk nicht. Nach Stoppen ausschließlich der
eigenen neuen VM, explizitem Setzen von `order=scsi0` und erneutem Start bootete
Debian. Die Ursache für die zuvor abweichende Reihenfolge wurde nicht abschließend
geklärt; künftig nach den Konfigurationsänderungen den gespeicherten Stand lesen.

Belegte Endergebnisse dieser Sitzung:

- Provisioning-Skript endete mit gespeicherten Status 0; der Bootfehler wurde
  anschließend korrigiert. `cloud-init status --wait` meldete `status: done`.
- Der Gast meldete Debian 13.7; nginx und QEMU Guest Agent waren `active`.
- Öffentlicher Gast-Hostschlüssel und Maschinen-ID wurden über den QEMU Guest
  Agent erfasst und für einen eigenen Gastalias verwendet. Der Gast-Identitäts-
  aufruf über MCP endete mit Exitcode 0 und stimmte mit diesen Werten überein.
- Schlüssel-Login über den Gastalias und separater Passwort-Login über den
  vorhandenen OpenSSH-Client wurden geprüft; der Passworttest lieferte Exitcode 0.
  Das Passwort wurde lokal erzeugt und aus der geschützten Akte verwendet.
- HTTP-Abruf der Gastadresse auf Port 80 lieferte im Gast HTTP 200 und den
  erwarteten Hello-World-Inhalt; derselbe Inhalt war auch vom Proxmox-Host abrufbar.
- Tatsächlicher Gastbenutzer, Testpasswort, Image-Prüfsumme, geprüfte Identität
  und Ergebnisstatus wurden in der Proxmox-Description der zugeordneten VM
  hinterlegt. Der Benutzer bestätigte den ersten kleinen Test als erfolgreich.

Damit ist erstmals der konkrete Weg Produkt-MCP → Proxmox → Gast → HTTP belegt.
Es war ein Infrastruktur-/Webserver-Smoke-Test ohne Projekt-Checkout oder
Projekt-Commit-SHA. Ein anderer Codex-Cloud-Task, Wiederaufnahme nach Sitzungs-
oder Serverwechsel, negative Hostschlüsseltests, Projekt-Integrationstests und
vollständiger Plain-Debian-Bootstrap sind damit nicht geprüft.
