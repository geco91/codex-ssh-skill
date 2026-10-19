# Prüfungen und Stand der Live-Abnahme

Stand 19.10.2026. Die historischen Abschnitte dokumentieren lokale Prüfungen und
die anschließende AITL-Runde. Maßgeblich für den inzwischen hinzugekommenen
Produkt-MCP-/Gast-/HTTP-Nachweis ist das [Live-Protokoll](live-testproxmox.md).

Aktuell: Installation auf dem beauftragten Test-Proxmox und lokale MCP-/SSH-
Prüfung erfolgreich (`BOOTSTRAP_EXIT=0`, `MCP_LOCAL_OK`). Anschließend bestanden:
Host- und Gastzugang über die angebotenen Produkt-MCP-Werkzeuge, Debian-13-VM-
Anlage, fertiges Cloud-Init, Schlüssel-/Passwort-Login und Hello-World-HTTP 200.
Offen bleiben insbesondere ein separater Codex-Cloud-Task, Projekt-Tests mit
Commit-SHA, Wiederaufnahme nach Sitzungswechsel sowie Plain-Debian-Bootstrap.

## Historisch: erste lokale Prüfung

Am slepp-Commit `37381ddc68a941b62ed8557dcbb5644dc3b6c5fd` wurden sechs
vorhandene Tests ausgeführt, alle erfolgreich (8,061 Sekunden):

```sh
python -m unittest -v \
 tests.test_stdio_server.StdioServerTests.test_host_key_modes_through_tool_calls \
 tests.test_stdio_server.StdioServerTests.test_stdio_jsonrpc_round_trip \
 tests.test_stdio_server.StdioServerTests.test_stdio_ensure_session_reuses_existing_session \
 tests.test_ssh_tools.SshToolServiceTests.test_ssh_view_truncates_large_files_by_default \
 tests.test_ssh_tools.SshToolServiceTests.test_ssh_view_supports_view_range \
 tests.test_ssh_tools.SshToolServiceTests.test_ssh_ensure_session_reuses_named_session_across_many_round_trips
```

Zusätzlich einmalige Python-Smoke-Aufrufe mit `SshToolService` und dem bestehenden
`tests.helpers.create_fake_ssh` in temporären Verzeichnissen; keine neue
Testinfrastruktur im Repository. Ausgeführt mit `PYTHONPATH=src python` im
Upstream-Checkout. Fälle und belegte Ergebnisse:

| Szenario | Lokaler Nachweis | Grenze |
| --- | --- | --- |
| Verbindung/Ziel unbekannt | leeres `target` löst `ValidationError` aus; hier keine SSH-Tools konfiguriert, kein Remote-Aufruf | Zuordnung/Identitätsstopp zusätzlich am Skilltext geprüft |
| Harmloser Befehl | `printf hello; printf diagnostic >&2`: stdout `hello`, stderr `diagnostic`, Exit 0, kein Timeout | Fake-SSH führt lokal aus |
| Fehler | `exit 7`: Exitcode 7, `ok=false`, kein Timeout | kein Remote-Test |
| Timeout | `sleep 0.3` bei `timeout=0.05`: `timed_out=true`, `ok=false` | kein Nachweis, dass ein echter Remote-Prozess beendet wäre |
| Lange Ausgabe | vorhandener Trunkierungs- und `view_range`-Test erfolgreich | keine großen Logs über Tunnel übertragen |
| Wiederaufnahme | stabile Session zweimal sichergestellt, gleiche ID und `reused=true`; einmaliger Startmarker bleibt einmalig, Statusdatei 0, genau eine Session | kein Serverneustart simuliert; kein Nachweis dauerhafter Remote-Jobs |

Die zusätzlichen Assertions vergleichen die genannten Ergebnisfelder direkt.
Beim Wiederaufnahmefall wurde einmal `printf start >> <temporärer Marker>;
sleep 0.2; printf 0 > <temporäre Statusdatei>` geschrieben, danach nur dieselbe
Session wiedergefunden und gelesen. Alle temporären Sessions wurden geschlossen.

Skilltext zusätzlich anhand derselben Szenarien geprüft: fehlende Zielbindung und
unbekannter Hostschlüssel stoppen vor Verbindung; falsche Maschinen-ID stoppt vor
Arbeit; Timeout/fehlender Endstatus erzwingen Prüfung des alten Laufs. Dies ist
eine manuelle Regelprüfung, keine automatisierte Verhaltens-Evaluation eines Modells.
Markdown-Verweise, Frontmatter, kurze Einstiegsdatei, Git-Diff und ungewollte
Zugangsdaten wurden lokal geprüft. Keine VM-/MCP-Installation, Docker-SSH-Testserver,
Tunnel-Konfiguration, Push oder Veröffentlichung vorgenommen.

## Weiterführender Abnahmeplan

Benötigt werden eine ausdrücklich für die Abnahme freigegebene Testverbindung
**in der gewünschten Codex-App/Web-Cloud-Sitzung**, Zielalias/Konto,
geklärter Vertrauensmodus und Maschinenidentität, Arbeits-/Logpfad sowie bei
Code-Tests Checkout, Commit-SHA und Testbefehl. Der erlaubte Umfang muss benötigte
temporäre Dateien abdecken. Ein ausdrücklich freigegebener TOFU-Erstkontakt mit
Erstaufnahme folgt dem [Zugangsablauf](../.agents/skills/codex-ssh/references/zugang.md).
Tunnel-/Host-Zugangsdaten im geschützten Speicher hinterlegen; Gast-Test-Logins
nach der ausdrücklich gewünschten Betriebsregel in deren Proxmox-Description.

1. Betreiber prüft vorhandenen Tunnel mittels `doctor` und laufendem Client;
   Organisation/Workspace/Zielprodukt-Zuordnung prüfen. Das ist noch kein Testresultat.
2. Im tatsächlichen Cloud-Task Skill-Erkennung und angebotene MCP-Tools/Schemas
   protokollieren. Falls nicht verfügbar: dort stoppen und Produkt-/Account-Anbindung
   klären. Weder CLI-Nachweis noch funktionierende ChatGPT-AITL-Verbindung ersetzen das.
3. Mit vorbereitetem known_hosts und strikter Prüfung nur den Identitätscheck
   ausführen, Sollwerte lokal vergleichen. Fehlenden/falschen Schlüssel an einem
   isolierten Testprofil negativ prüfen, nie den bestehenden Vertrauensanker ändern.
4. Im erlaubten Testbereich `printf 'ok\n'`,
   `sh -c 'printf "expected failure\n" >&2; exit 7'` und einen kurzen `sleep 2`
   mit kürzerem Werkzeugtimeout prüfen. Exakte Ausgaben/Exitcodes/Timeout trennen;
   nach Timeout den zugeordneten Prozessstatus prüfen. Keine globale Prozessbereinigung.
5. Eine endliche Logdatei erzeugen (z. B. `seq 1 2000`), zwei begrenzte Bereiche
   lesen und Vollständigkeit markieren. Verfügbare Befehle vorher prüfen.
6. Einen eindeutig benannten kurzen Testlauf mit SHA, getrennten Logs, Laufkennung
   und Endstatus starten. Beobachtung kurz unterbrechen, vorhandenen Lauf wiederfinden,
   nur lesen und genau einen Start nachweisen. Einen fehlenden Endstatus ausdrücklich
   als unbekannt melden. Einen langen Integrationstest erst im dafür erteilten Umfang.
7. Bereinigte Resultate mit Datum, Produktoberfläche, SHA, Lauf-ID, Exitcode und
   offenen Grenzen festhalten. Erst dann den jeweiligen Live-Nachweis als bestanden
   bezeichnen. Bereinigung nur für selbst angelegte, freigegebene Testartefakte.

Der Infrastruktur-Smoke-Test ist bestanden. Die darüber hinausgehenden Negativ-,
Timeout-, Log- und Wiederaufnahmeszenarien dieses Plans sind noch offen.
Keine tatsächlichen Zieladressen, Tunnel-IDs, Maschinenkennungen oder Schlüssel
werden dafür im Repository hinterlegt.

## Historisch: Bootstrap-Skript, erster lokaler Stand

Nach dem ersten Folgeauftrag wurde `scripts/bootstrap-debian.sh` vorbereitet und
lokal geprüft, zu diesem Zeitpunkt noch nicht auf der Zielmaschine ausgeführt:

- `bash -n scripts/bootstrap-debian.sh`: erfolgreich.
- `uvx --from shellcheck-py shellcheck scripts/bootstrap-debian.sh`: erfolgreich;
  ShellCheck wurde dafür isoliert im lokalen Tool-Cache bereitgestellt.
- Hilfe, Standardmodus und `--dry-run`: Exit 0, keine Installation/Downloads.
  Unbekannte/zusätzliche Argumente: Exit 2.
- `--install` und `--check` als unprivilegierter Cloud-Benutzer: Exit 1 mit
  Root-Hinweis; noch vor jedem Betriebssystemeingriff.
- Beide tatsächlich heruntergeladenen Archive (MCP-Quellen und amd64-Client)
  entsprechen den im Skript eingetragenen SHA-256-Werten. arm64-Hash gegen
  GitHubs Release-Metadaten geprüft, arm64-Binärdatei hier nicht ausgeführt.
- Generierte SSH-Clientkonfiguration mit temporären Pfaden und `ssh -G` gelesen:
  Loopback, Port 22222, korrektes Konto, strikte Hostschlüsselprüfung, BatchMode,
  kein Agent-Forwarding. Dabei keine Verbindung hergestellt.
- Offizielles amd64-Client-Binary im Rechercheverzeichnis mit `--version` und
  `help quickstart` ausgeführt: v0.0.16; dokumentierte stdio-/Profilbefehle dort
  vorhanden. Kein Tunnel angelegt oder gestartet.

**Noch offen:** vollständiger Installationslauf auf einer frischen Debian-VM,
Paket-/Service-Verhalten auf Debian 12 und 13, tatsächlicher Loopback-SSH-Aufruf,
Neustart/Fehlerabbruch und anschließende Tunnel-/Codex-Live-Abnahme. ShellCheck
und `ssh -G` ersetzen diese Installationsprüfung nicht. Das Skript ist ein
vorbereiteter erster Stand, keine als VM-getestet ausgewiesene Installation.

## Historisch: Debian-/Proxmox-Modus und dauerhafte Test-Logins

Der Installer erkennt Plain Debian und Proxmox; die vorherige Proxmox-Sperre
wurde durch einen eigenen Hostpfad ersetzt. Die separate Admin-Option wird nur
auf Proxmox akzeptiert. Der Skill verwendet dort Gäste für Projekt-Tests und
speichert deren Test-Logins in der VM-Description, wie vom Benutzer beauftragt.

Erneut ausgeführt, erfolgreich:

```sh
python -m unittest discover -s tests -v
bash -n scripts/bootstrap-debian.sh
uvx --from shellcheck-py shellcheck scripts/bootstrap-debian.sh
```

Sechs Standardbibliothek-Tests, ohne zusätzliche Testplattform:

- Plain Debian 12/13 korrekt erkannt.
- Proxmox-Merkmale auf Debian 12/13 korrekt erkannt.
- Teilweise Proxmox-Merkmale führen zum Abbruch, kein Debian-Fallback.
- Nicht unterstütztes System abgewiesen.
- Unzulässige CLI-Kombinationen vor Installation abgewiesen.
- Tatsächlich generierte sshd-Konfiguration mit vorhandenem `sshd -T` für
  Testkonto/Root und beide Admin-Modi ausgewertet: Listener nur Loopback,
  Forwarding aus, Root nur im gewählten Admin-Modus mit separater Schlüsselquelle.

Dafür wurden keine Dienste gestartet, kein apt ausgeführt und keine Host-/VM-
Konfiguration verändert. Die temporären Hostschlüssel liegen nur im temporären
Testverzeichnis und werden wieder entfernt. Branchtests belegen die Erkennung,
keinen kompletten Paket-/Installationslauf auf den jeweiligen Betriebssystemen.
Description-Schema und Wiederaufnahme sind manuell am Skilltext geprüft;
kein tatsächlicher Gast-Login oder Description-Schreibvorgang ausgeführt.

Die vom Benutzer freigegebene AITL-Ausgabe zeigte einen Test-Proxmox 9.2.2 auf
Debian 13.5 mit aktivem SSH; `qm list` und `pct list` lieferten keine Gäste.
MCP-/Tunnel-Binaries wurden über `command -v` im PATH nicht gefunden. Der
Hello-World-Rückweg über menschlich geteilte Ausgabe funktionierte. Daraus
folgt kein SSH-MCP-/Secure-Tunnel-Nachweis und kein verlässlicher Exitcode.
Keine privaten Hostnamen, Bindungscodes oder tatsächlichen Credentials im Repo.

Der spätere Installationslauf auf dem beauftragten Test-Proxmox ist mit
`BOOTSTRAP_EXIT=0` und lokalen SSH-Selbstprüfungen belegt; Paketquellenreparatur
und genaue Grenzen stehen im [Live-Protokoll](live-testproxmox.md).

Zum Ende dieses früheren Prüfstands offen: Installation auf Plain Debian, VM-Anlage
mit gegebenem Storage/Bridge/Template, funktionierender dokumentierter Gast-Login,
erneutes Auffinden nach Sitzungswechsel und End-to-End-Test aus Codex. Für diese
Abnahme den Installer-Check von Tunnel-/VM-/Testresultaten getrennt protokollieren.

## Regelprüfung nach der ersten Praxisrunde

Die überarbeiteten Anweisungen sind gegen folgende Fälle zu prüfen. Das ist eine
manuelle Konsistenzprüfung des Texts, keine automatische Modell-Evaluation:

| Fall | Erwarteter Ablauf |
| --- | --- |
| Dokumentierter Bootstrap-Adminzugang vorhanden | Zuordnung und Alias zuerst lesen; vorhandenen Schlüssel/Pin verwenden; kein neues Root-Passwort verlangen |
| Hostschlüssel fehlt, TOFU für das Ziel schon freigegeben | Erster Identitätsaufruf mit `accept-new`, dauerhaft speichern, danach `yes`; keine neue Freigabefrage |
| TOFU ohne Soll-Maschinen-ID | Beobachtung lokal als Erstaufnahme festhalten, im freigegebenen Umfang weiterarbeiten; nicht unabhängig verifiziert nennen |
| TOFU noch nicht freigegeben | Einmal die fehlende zielbezogene Freigabe erfragen; vorher nicht verbinden |
| Schlüssel oder bekannte Maschinenidentität geändert | Stoppen und unabhängig klären; kein Entfernen oder Neupinnen vorhandener Einträge |
| Passwort nicht übergeben, SSH Exit 255 | Authentifizierungsfehler melden; Passwortgültigkeit bleibt ungeprüft; dokumentierte Anmeldung prüfen |
| VM-Auftrag bereits vollständig freigegeben | Identität, Bestand, Konfiguration und zugehörige Tests ohne weitere Routinefreigaben durchführen |
| Systemdisk importiert, Bootreihenfolge abweichend | Gespeicherte Konfiguration vor Start korrigieren; eigene VM diagnostizieren statt Duplikat anlegen |
| VLAN-Anschluss oder Tag unklar | Bridge-/Anschlusskonfiguration lesen; bei verbleibender Mehrdeutigkeit fragen, kein Tag aus der Subnetznummer ableiten |
| HTTP 200, aber falscher Inhalt oder unfertiges Provisioning | Keine vollständige Erfolgsmeldung; Provisioning, Dienst, Login und erwarteten Inhalt separat prüfen |

Veröffentlichte v0.1.0-ZIP/Prüfsumme und Installer bleiben unverändert. Aktuelle
Anweisungen liegen im Skillordner und im neuen v0.1.1-Download.

Für diesen Dokumentationsstand erneut lokal erfolgreich ausgeführt: alle sechs
vorhandenen Bootstrap-Unittests (einschließlich effektiver sshd-Konfiguration),
`bash -n scripts/bootstrap-debian.sh` und `git diff --check`. Lokale Markdown-
Linkziele, Skill-Frontmatter und der separat erzeugte Import-ZIP-Inhalt wurden
ebenfalls geprüft. Diese Prüfungen verändern den Test-Proxmox nicht und sind
kein erneuter Live-Test des überarbeiteten Skills.
