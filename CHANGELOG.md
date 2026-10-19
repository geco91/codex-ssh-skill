# Versionshinweise

## Unveröffentlicht

- Dokumentierte SSH-Aliase und vorhandene Schlüssel vor neuen Zugangsrückfragen
  ermitteln; Tunnel-, Benutzeranmeldung und Hostschlüssel klar unterscheiden.
- Zielbezogen ausdrücklich freigegebenes TOFU mit `accept-new`, dauerhaftem
  known_hosts und anschließend `yes`; keine automatische Schlüsselrotation.
- Identitäts-Erstaufnahme ohne Soll-Maschinen-ID als TOFU kennzeichnen; bei
  Hostverwaltung keinen unnötigen Projekt-Checkout verlangen.
- Gedeckte VM-Routine ohne wiederholte Freigabefragen, gespeicherte Boot-/Disk-/
  Netzkonfiguration kontrollieren und VLAN-Anschluss von Gast-Tag unterscheiden.
- Provisioning, tatsächliche Gast-Anmeldearten und erwartete HTTP-Antwort getrennt
  prüfen und in der Wiederanlaufakte dokumentieren.
- Ersten erfolgreichen Produkt-MCP-/Gast-/HTTP-Smoke-Test dokumentieren;
  frühere Prüfstände und noch offene Abnahmen getrennt halten.

Installer und veröffentlichte v0.1.0-Downloads bleiben unverändert. Der aktuelle
Skill-Arbeitsstand wird aus `.agents/skills/codex-ssh/` übernommen.

## v0.1.0 — 2026-10-19

Erster veröffentlichter Stand für vorhandenes SSH-MCP über Secure MCP Tunnel.

- Repositorylokaler Skill für Debian-Tests, Test-Proxmox und zugeordnete Gast-VMs.
- Host-/Gastidentität, begrenzte Befehle, Logbereiche und wiederaufnehmbare Tests.
- VM-Description als Wiederanlaufakte einschließlich der ausdrücklich gewünschten
  Gast-Test-Logins; keine tatsächlichen Credentials im Repository oder Download.
- Debian-/Proxmox-Bootstrap mit festgelegten Upstream-Versionen und Prüfsummen,
  privatem Loopback-SSH und optionalem Proxmox-Verwaltungszugang.
- Installierbare Skill-ZIP und Dokumentation zu Aufbau, Auswahl, Prüfungen und
  beobachteter Live-Einrichtung auf einem Test-Proxmox.

Geprüft: sechs lokale Bootstrap-Tests, Shell-Syntax/ShellCheck, Skillformat und
Referenzen sowie tatsächlich ausgeführte lokale MCP-/SSH-Aufrufe auf dem
Test-Proxmox. Der Tunnel-Client meldete einen laufenden, lokal bereiten Prozess.

Noch offen: bestätigtes Control-Plane-Polling, echter SSH-MCP-Aufruf aus der
gewünschten Codex-Oberfläche, Gast-VM-Anlage/Testlauf und vollständige Installation
auf Plain Debian. Diese Version behauptet keine bestandene Cloud-End-to-End-Abnahme.
