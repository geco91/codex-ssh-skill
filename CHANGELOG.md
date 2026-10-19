# Versionshinweise

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
