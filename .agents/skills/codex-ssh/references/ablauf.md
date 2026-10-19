# Vorhandene Werkzeuge nutzen

Die folgenden Namen sind am geprüften Upstream-Stand belegt, keine Garantie für
die aktuelle Verbindung. Immer zuerst deren tatsächliches Schema lesen.

| Fähigkeit | slepp/ssh-mcp | tufantunc/ssh-mcp v2 |
| --- | --- | --- |
| Begrenzter Befehl | `ssh_exec` | `read-command`, `run-command` |
| Session finden | `ssh_list_sessions` | `list-sessions` |
| Session eröffnen | `ssh_ensure_session` | `open-session` |
| Ausgabe nachlesen | `ssh_read_session` | `read-session-output` |
| Datei abschnittweise | `ssh_view` mit `view_range` | angebotenes Dateiwerkzeug/Lesebefehl prüfen |

## Kleiner Befehl (slepp)

Zuerst [Zugang und Vertrauensmodus](zugang.md) klären. Im normalen Betrieb:
`ssh_exec` mit zugeordnetem
`target`, `cwd`, `strict_host_key_checking: "yes"`, lokalem `known_hosts_file`,
`timeout: 10`, `tty: false`. `extra_ssh_args: ["-o", "BatchMode=yes",
"-o", "ConnectTimeout=5"]` verhindert interaktive Anmeldung und lange Verbindungsversuche.
Alle Ziel-/Pfadangaben aus lokaler Konfiguration übernehmen, nicht erraten.
`stdout`, `stderr`, `exit_code`, `timed_out` getrennt auswerten.
Exitcode 255 ist häufig SSH-/Transportfehler; nicht automatisch Testfehler nennen.
Für ausdrücklich freigegebenes TOFU beim ersten Identitätsaufruf stattdessen
`strict_host_key_checking: "accept-new"` verwenden, danach `yes`. Vorhandene
Alias-Konfiguration übernehmen; nicht ohne Anlass einen neuen Login einrichten.

`ssh_exec` hat am geprüften Stand keinen allgemeinen Ausgabe-Cap als Argument.
Potentiell große Ausgabe deshalb in eine geschützte Datei im freigegebenen
Arbeitsbereich umleiten und mit `ssh_view` in endlichen Bereichen lesen, z. B.
`view_range: [1, 100]`. Auch eine einzelne Zeile kann sehr groß sein; dann ein
vorhandenes bytebegrenztes Lesewerkzeug oder `head -c` verwenden. Die Umleitung
ist eine Dateiänderung und braucht passenden Arbeitsumfang.

## Längerer Test

1. Prüfe im vorgesehenen Checkout `git rev-parse HEAD` und
   `git status --porcelain`; uncommittierte Änderungen ausdrücklich festhalten.
   Gleiche SHA mit dem Cloud-Auftrag ab. Keine fremden Änderungen überschreiben;
   fehlende Übertragung/Checkout separat melden. Kein Test gegen stillschweigend
   anderen Code. Bei Upload-Werkzeugen beziehen sich „lokale“ Pfade auf den
   MCP-Host, nicht automatisch auf den Codex-Cloud-Checkout.
2. Nutze bevorzugt den bereits vorhandenen Test-Runner mit Lauf-ID und Status.
   Sonst reicht eine vorhandene MCP-Session. Bei slepp zuerst `ssh_list_sessions`
   mit Ziel und stabilem `session_name` lesen. `ssh_ensure_session` kann eine
   fehlende Session **neu erzeugen**; Wiederverwendung allein beweist nicht,
   dass ein früherer Test beendet ist. Session-IDs gelten nur bis Serverneustart.
3. Für einen neuen Lauf eine eindeutige Laufkennung und einen noch nicht
   existierenden privaten Ergebnisordner im freigegebenen Bereich verwenden.
   In der Session den Test einmal starten, stdout/stderr in getrennte Dateien
   umleiten, Shell-PID sowie Startzeit/Prozess-Startmerkmal und SHA erfassen.
   Den echten Test-Exitcode unmittelbar danach in eine separate Statusdatei
   schreiben, möglichst über temporäre Datei und atomisches Umbenennen.
   Keine Erfolgsbewertung aus dem Exitcode eines Hintergrundstarts ableiten.
   Diese wenigen Shell-Schritte auf den vorhandenen Projekt-Testbefehl anpassen;
   keine universelle Runner-Implementierung hinzufügen.
4. Nur kurz lesen: bei slepp `ssh_read_session` etwa mit `wait_seconds: 1` und
   `max_output_chars: 4096`. `pending_output_chars`, Trunkierung und Verluste
   beachten; Session-PTY mischt ggf. Streams. Die getrennten Testlogs bleiben
   maßgeblich. Ein neuer Shell-Prompt liefert keinen Test-Exitcode.
5. Nach Verbindungsabbruch zuerst gespeicherte Laufdaten, Sessionliste, Statusdatei
   und Prozess prüfen. PID allein genügt wegen Wiederverwendung nicht: Startzeit,
   Befehl, Arbeitsverzeichnis und Laufkennung vergleichen. Lebender passender
   Prozess: weiter beobachten. Vorhandener Endstatus: auswerten. Fehlende Session
   oder verschwundener Prozess ohne Endstatus: **unbekannt**, nicht neu starten,
   bis geklärt ist, ob ein alter Test weiterläuft. Für neue Versuche neue Lauf-ID.

Eine MCP-Session ist keine Zusage, dass Prozesse Tunnel-/Serverneustarts überleben.
Für solche Anforderungen einen bereits vorhandenen dauerhaften Runner/tmux/systemd-
Ablauf verwenden und dessen Zustand prüfen. Falls nichts vorhanden ist, Grenze
melden. Timeout/Abbruch kann einen Remote-Prozess zurücklassen. Beenden nur den
eindeutig zugeordneten Lauf und nur im erteilten Umfang; kein globales `pkill`.

## Ergebnisformat

`Zielalias | SHA (+ dirty falls zutreffend) | Test/Lauf-ID | Erfolg/Fehler/Timeout/unbekannt`

Dazu Vertrauensmodus (vorab geprüft / TOFU-Erstaufnahme), Exitcode oder
„nicht verfügbar“, kurze stdout-/stderr-Belege,
Ausgabevollständigkeit und lokale Logreferenz. Keine privaten Identitätswerte
oder Geheimnisse kopieren. Noch laufend: „unbekannt, läuft noch“, mit nächstem
begrenztem Statusschritt. Ein Timeout sagt zunächst nur etwas über das jeweilige
Zeitlimit aus, nicht über das Ende des Remote-Tests.

Für einen reinen VM-/Webserver-Auftrag statt einer nicht vorhandenen Code-SHA
Image-Version und Prüfsumme festhalten. Provisioning-Endstatus, Gastidentität,
getestete Anmeldeart und HTTP-Status mit erwartetem Seiteninhalt getrennt belegen.
