# Recherche und Kompatibilitätsgrenzen

Geprüft am 19.10.2026; Beobachtungen sind Momentaufnahmen.
Die folgenden Abschnitte dokumentieren die ursprüngliche Auswahl und damaligen
Werkzeuggrenzen. Der spätere erfolgreiche Produkt-MCP-/Gast-/HTTP-Smoke-Test
steht im [Live-Protokoll](live-testproxmox.md#erste-produkt-mcp-gast-abnahme).
Die damalige Ablehnung von TOFU ist keine aktuelle Betriebsregel: ausdrücklich
freigegebenes zielbezogenes TOFU folgt heute dem
[Zugangsablauf](../.agents/skills/codex-ssh/references/zugang.md).

## Produktunterstützung

- [Offizielle Skill-Dokumentation](https://developers.openai.com/codex/skills)
  (Weiterleitung zu [Build skills](https://learn.chatgpt.com/docs/build-skills)):
  repositorylokal `.agents/skills/<name>/SKILL.md`, YAML-Frontmatter mit `name`
  und `description`; Referenzen optional. Hier bewusst nur Anweisungen und eine
  Ablaufreferenz. Kein erfundener MCP-Dependency-Eintrag ohne bekannten Server.
- [Offizielle MCP-Dokumentation](https://developers.openai.com/codex/mcp)
  (Weiterleitung zu [MCP, CLI-Oberfläche](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)):
  beschreibt stdio und Streamable HTTP. Eine dortige CLI-Konfiguration belegt
  nicht die Übernahme in einen App/Web-Cloud-Task.
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
  nennt Codex als unterstütztes Produkt und verweist für dessen Verwendung auf
  die jeweils unterstützte Produktoberfläche. Daraus folgt keine Garantie für
  diesen Account, dessen Oberfläche oder die konkrete Cloud-Sitzung.
- [Offizieller Client](https://github.com/openai/tunnel-client), gelesener Stand
  `2c3af61e507ee568f1d28ce60546952d09902f0a`, insbesondere
  [Onboarding](https://github.com/openai/tunnel-client/blob/2c3af61e507ee568f1d28ce60546952d09902f0a/docs/onboarding.md):
  private HTTP-Server und stdio-Kindprozesse werden unterstützt. Deshalb direkt
  stdio verwenden. Ausgehendes HTTPS ersetzt eine öffentliche MCP-/Shell-Freigabe.
  Ein Runtime-Key für den Tunnel ist keine Entscheidung, Agentenarbeit über die
  separat abgerechnete Agents API auszuführen. Tarifabdeckung wurde hier nicht geprüft.

## In dieser Sitzung beobachtet

Der Workspace war ohne Checkout. Das über die verbundene GitHub-Suche gefundene
Repository `geco91/codex-ssh-skill` wurde lokal geklont. Ausgangscommit:
`ec1b11e395ad6fba71f4b0b62834df754c1841b8`; nur LICENSE, Arbeitsbaum sauber,
keine AGENTS.md. Vorhandene MIT-Lizenz unverändert erhalten.

Cloud-Status: verbunden, aktuelle Beobachtungen, HTTP-Policy `unrestricted`
und `enforced`; keine konfigurierten Secrets/Runtime-Variablen/Outbound-Identitäten.
Netzwerkdatei: kein VPN, leere TCP-Zielbereiche. Diese Angaben belegen keinen
privaten SSH-Zugang. CLI vorhanden: `codex-cli 0.159.2`; in der lokalen
`~/.codex/config.toml` keine MCP-Servereinträge (nur Namen geprüft, keine Secrets).
Auch im exponierten Sitzungstoolkatalog keine SSH-MCP-Werkzeuge oder passende
Tunnel-Zielbindung. AITL-Tools sind sichtbar, wurden aber nicht aufgerufen.
Keine Ressourcen, Ports, Tunnel, Remote-Prozesse oder Board-Einträge verändert.

**Praktisch getestet:** ausschließlich lokale Testdouble-Aufrufe des ausgewählten
Servers; keine SSH-Verbindung, kein Tunnel und keine Skill-Ausführung im separaten
Codex-Cloud-Produkt. Der Skill ist formatkonform erstellt, keine Produktzertifizierung.

## Open-Source-Auswahl

| Kriterium | tufantunc/ssh-mcp (erster Prüfkandidat) | slepp/ssh-mcp (gewählt) |
| --- | --- | --- |
| Geprüfter Commit | `58b03f10b0d184fa31573b2ea79f378aa8285ff2` | `37381ddc68a941b62ed8557dcbb5644dc3b6c5fd` |
| Lizenzdatei | MIT, Copyright 2025 Tufan Tunç | MIT, Copyright 2025 |
| Wartung | nicht archiviert, letzter Branchcommit 14.10.2026 | nicht archiviert, letzter Branchcommit 15.10.2026 |
| Architektur | TypeScript, ssh2, Rollen/Policy/Approval, stdio und HTTP | Python ≥3.10, OpenSSH, stdio, keine Python-Runtime-Abhängigkeiten |
| Belegte Tools | `read-command`, `run-command`, `privileged-command`, `signal-process`, Session-/SFTP-Tools | `ssh_exec`, `ssh_view`, Datei-/Transfer-Tools, `ssh_ensure_session`, `ssh_list_sessions`, `ssh_write_session`, `ssh_read_session`, Forwarding |
| Hostvertrauen | `trustedHostKey`-Pin; `--hostKeyMode=strict`; Default TOFU genügt hier nicht | vorhandene OpenSSH-Konfiguration; pro Aufruf known_hosts und strikte Prüfung möglich; keine sichere Voreinstellung unterstellen |
| Testnachweise | CI-Definition mit Unit/Integration/e2e und Docker-SSH-Servern; eigene Suite hier nicht ausgeführt | unittest-Suite mit Fake-SSH und stdio-JSON-RPC; ausgewählte Tests hier selbst ausgeführt |

Quellbelege, jeweils auf den geprüften Stand fixiert:

- tufantunc: [Lizenz](https://github.com/tufantunc/ssh-mcp/blob/58b03f10b0d184fa31573b2ea79f378aa8285ff2/LICENSE),
  [Tools](https://github.com/tufantunc/ssh-mcp/tree/58b03f10b0d184fa31573b2ea79f378aa8285ff2/src/tools),
  [Hostprüfung](https://github.com/tufantunc/ssh-mcp/blob/58b03f10b0d184fa31573b2ea79f378aa8285ff2/src/ssh/host-key.ts),
  [CI](https://github.com/tufantunc/ssh-mcp/blob/58b03f10b0d184fa31573b2ea79f378aa8285ff2/.github/workflows/ci.yml).
  GitHub meldete für diesen Commit u. a.
  [Run 38550284557](https://github.com/tufantunc/ssh-mcp/actions/runs/38550284557)
  als `completed/success`. Kein eigener Sicherheits- oder Integrationstest.
- slepp: [Lizenz](https://github.com/slepp/ssh-mcp/blob/37381ddc68a941b62ed8557dcbb5644dc3b6c5fd/LICENSE),
  [Implementierung](https://github.com/slepp/ssh-mcp/blob/37381ddc68a941b62ed8557dcbb5644dc3b6c5fd/src/ssh_mcp/ssh.py),
  [Tests](https://github.com/slepp/ssh-mcp/tree/37381ddc68a941b62ed8557dcbb5644dc3b6c5fd/tests),
  [CI](https://github.com/slepp/ssh-mcp/blob/37381ddc68a941b62ed8557dcbb5644dc3b6c5fd/.github/workflows/ci.yml).
  GitHub meldete u. a.
  [Run 38767403342](https://github.com/slepp/ssh-mcp/actions/runs/38767403342)
  für diesen Commit als `completed/success`. Die Testdouble-Suite belegt keine
  echte Hostschlüsselvalidierung oder OpenAI-Produktkompatibilität.

Entscheidung: slepp passt zum kleinen Einstieg, weil der vorhandene OpenSSH-Client
und stdio ohne weitere Adapter reichen. Seine generischen Ziele und Werkzeuge
verlangen eingeschränkte Betriebsrechte und Netzreichweite. tufantunc bleibt
eine geeignete Option bei Bedarf an serverseitigen Profilen/Policies. Keine
README-Aussage, grüner CI-Status oder Quelltextsichtung ersetzt eigene Live- und
Sicherheitsprüfung. Es wurde kein Upstream-Code ins Repository übernommen.

## Erweiterung für den beauftragten Test-Proxmox

Die spätere, ausdrücklich freigegebene AITL-Leserunde belegt Proxmox 9.2.2 auf
Debian 13.5 und aktives Host-SSH. Sie ist weiterhin kein Nachweis für SSH-MCP
über Secure MCP Tunnel aus Codex. Es wurden nur Bestands-/Versionsdaten gelesen.

Die offiziellen Proxmox-Webseiten waren beim Abruf mit HTTP 403 nicht lesbar.
Als Primärquelle wurde stattdessen die
[Cloud-Init-Dokumentation im offiziellen Proxmox-Repository](https://github.com/proxmox/pve-docs/blob/2e161a79bbcce5e8d99816564ac54c7438abcdaf/qm-cloud-init.adoc)
gelesen. Sie beschreibt Templates, `qm clone`, Gast-SSH-/Netzkonfiguration und
Cloud-Init im Gast. Der Skill verwendet diese vorhandenen Abläufe statt eigener
VM-Orchestrierung. Tatsächliche Optionen und Ressourcen müssen zur installierten
Proxmox-Version passen; Installation/VM-Anlage wurden hier nicht getestet.

Gastbenutzer und Testpasswort in der VM-Description sind eine ausdrückliche
Betriebsentscheidung des Benutzers für die angelegten Test-VMs, keine
herstellerseitige Empfehlung oder Behauptung einer geheimen Description.
