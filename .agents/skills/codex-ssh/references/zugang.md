# Vorhandenen Zugang finden und prüfen

## Zuerst Projektkontext, dann Rückfragen

Lies die tatsächlich zugängliche Projekt-README, Bootstrap-Dokumentation,
Live-Protokolle und lokale Zielzuordnung. Ein leerer Cloud-Workspace beweist
nicht, dass auf dem privaten MCP-Host keine SSH-Konfiguration existiert.
Ist das beauftragte Repository über eine angebotene Verbindung erreichbar,
dort nachlesen. Nicht auf ein anderes Projekt oder einen anderen Runner wechseln.

Beim Bootstrap dieses Projekts sind folgende Rollen dokumentiert. Die Aliase
sind nur bei belegter Zuordnung zu dieser Installation zu verwenden, niemals
als allgemeine Defaults für beliebige MCP-Verbindungen:

| Zweck | SSH-Ziel | Konto / Zugang |
| --- | --- | --- |
| Unprivilegierter Selbsttest auf dem Host | `codex-test-local` | `codex-test`, vorhandener Loopback-Schlüssel |
| Beauftragte Proxmox-Verwaltung mit installiertem `--proxmox-admin` | `codex-proxmox-host` | root, separater vorhandener Admin-Schlüssel |
| Arbeit im Gast | auftragsbezogener Gastalias | eigener Gastbenutzer, eigene Identität und Hostschlüsselbindung |

Die beiden Hostaliase verwenden auf dem **MCP-Host** `127.0.0.1:22222`.
Der Tunnel/MCP-Prozess läuft als `codex-test`; das ist nicht der Benutzer des
administrativen SSH-Ziels. Clientkonfiguration und Schlüssel liegen dort unter
`/var/lib/codex-test/.ssh/`, das lokale Identitätsmanifest unter
`/etc/codex-ssh/identity.txt`. Die ausführliche lokale Einrichtungsnotiz liegt
unter `/opt/codex-ssh/README.txt`. Pfade nicht im Cloud-Workspace voraussetzen.
Die erste Verbindung bleibt auf den begrenzten Identitätscheck beschränkt.
Zielbezogene lokale Metadaten anschließend nur über einen bereits zugeordneten
Zugang lesen; fehlende unabhängige Prüfung nicht durch Selbstauskunft ersetzen.

## Drei getrennte Aufgaben

- **Tunnel-Zugang:** verbindet den privaten MCP-Prozess mit dem Produkt.
  Ein Runtime-Key ist kein SSH-Passwort und kein SSH-Schlüssel.
- **SSH-Anmeldung:** beweist den Benutzer gegenüber dem Zielserver. Private
  Schlüssel oder ein SSH-Agent gehören auf den MCP-Host; das Ziel hat den
  passenden öffentlichen Anmeldeschlüssel. Der Bootstrap hat diese bereits
  eingerichtet. Nicht vorsorglich neue Schlüssel oder ein Root-Passwort anfordern.
- **SSH-Hostschlüssel:** weist den Server gegenüber dem Client aus. Er existiert
  auch bei Passwortanmeldung und ist vom Anmeldeschlüssel zu unterscheiden.

`slepp/ssh-mcp` verwendet OpenSSH und dessen bestehende Konfiguration. Die hier
geprüften Werkzeugschemas haben kein eigenes Passwortargument. Das ist kein
generelles Verbot von Passwortanmeldung. Der separate Bootstrap-Listener ist
jedoch tatsächlich auf Schlüsselanmeldung eingestellt; das bestehende
System-SSH kann eine andere Konfiguration haben.

`Permission denied` ohne übergebenes Passwort beweist nicht, dass das vom Nutzer
genannte Passwort falsch ist. Auch eine MCP-Session garantiert keinen bedienbaren
SSH-Loginprompt. Erst dokumentierten Alias, Konto, Schlüssel-/Agent-Konfiguration
und tatsächliche Schemas prüfen. `env`/`cwd` eines Remote-Kommandos sind kein
Passwortkanal für den lokalen SSH-Client. Falls kein unterstützter Weg existiert,
genau diese Lücke melden, keine Passwörter in Befehlsargumente, Logs oder Git
schreiben und keine eigenen SSH-Server oder Tunnel als Ersatz bauen.

## Hostvertrauen beim Erstkontakt

1. Vorhandenes geprüftes known_hosts oder Server-Pin mit `yes` bevorzugen. Der
   Bootstrap bindet den lokal erzeugten Loopback-Hostschlüssel bereits direkt;
   für diesen Zugang ist kein neuer TOFU-Schritt erforderlich.
2. Fehlt für ein eindeutig beauftragtes Ziel nur der Hostschlüssel, kann der
   Nutzer TOFU ausdrücklich freigeben. Ohne vorherige Freigabe einmal knapp
   erläutern und fragen; eine vorhandene zielbezogene Freigabe reicht aus.
3. Beim freigegebenen Erstkontakt `strict_host_key_checking: "accept-new"`
   verwenden. Der bekannte Hosts-Speicher muss auf dem MCP-Host dauerhaft sein,
   z. B. über dessen vorhandene Konfiguration oder `known_hosts_file`.
   Das speichert den zuerst gesehenen Schlüssel, nicht dessen unabhängige Prüfung.
   Auch bei fehlgeschlagener Benutzeranmeldung kann dieser schon gespeichert sein.
4. Danach mit `strict_host_key_checking: "yes"` weiterarbeiten. Maschinen-ID,
   Benutzer und Arbeitsverzeichnis mit vorhandenen Sollwerten vergleichen. Gibt
   es im freigegebenen TOFU-Modus noch keine Soll-Maschinen-ID, die Beobachtung
   lokal als Erstaufnahme erfassen und den Auftrag fortsetzen. Ergebnis:
   „TOFU; Identität erstmals erfasst“, nicht „unabhängig verifiziert“.
5. Ein Schlüsselwechsel ist kein neuer Erstkontakt: stoppen und Ursache unabhängig
   klären. Kein automatisches Entfernen alter Einträge, `no`/`off` oder stilles
   Neupinnen. Bekannte Identitätsabweichungen ebenfalls nicht als TOFU behandeln.

Bei selbst angelegten Gästen kann der verifizierte Host über QEMU Guest Agent
oder Gastkonsole den öffentlichen Gast-Hostschlüssel und die Maschinen-ID liefern.
Diese Bindung bevorzugen. Ein Netzwerk-Keyscan allein ist keine unabhängige
Verifikation. Eine Host-TOFU-Freigabe gilt nicht automatisch für jeden neuen Gast.
