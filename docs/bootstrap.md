# Bootstrap auf Debian oder einem Test-Proxmox

Ergänzung zum ursprünglichen Skillauftrag: ein öffentlich bereitstellbares
Installationsskript vorbereiten. Anschließend wurde dessen Installation auf dem
Test-Proxmox ausdrücklich beauftragt und über AITL ausgeführt; siehe
[Live-Protokoll](live-testproxmox.md). Der Installer bleibt unverändert; die
spätere MCP-/VM-Abnahme ist dort als eigener Schritt dokumentiert.

## Was der erste manuelle Schritt erledigt

Auf der Zielmaschine zunächst die lokale Konsole/AITL öffnen. Es besteht
zu diesem Zeitpunkt noch keine Shell-Verbindung aus Codex. Das Skript aus der
README herunterladen, prüfen und als root mit `--install` starten. Ohne Parameter
oder mit `--dry-run` erkennt es den lokalen Plattformtyp und zeigt einen Plan;
das ist keine Installationssimulation und prüft weder Netzwerk noch Paketverfügbarkeit.

Voraussetzungen: Debian 12/13, laufendes systemd, amd64/arm64, `ss` aus iproute2,
Paketquellen und ausgehendes HTTPS zu GitHub, codeload.github.com und PyPI.
Die Zielmaschine vor Installation prüfen. Proxmox wird anhand von `/etc/pve`
sowie vorhandenem `pveversion` und `qm` erkannt. Teilweise vorhandene Merkmale
führen zu einem Fehler, nie zu einem stillen Debian-Fallback. Vorhandenes
OpenSSH wird auf Proxmox vorausgesetzt und muss aktiv sein. Die Erkennung deckt
Debian 12/13 mit passenden Proxmox-Komponenten ab; Versions-/Installationstests
auf realen Proxmox-8/9-Hosts bleiben Teil der Live-Abnahme.

Das Skript:

- installiert nur fehlende Pakete für Python-venv, curl/CA, OpenSSL und OpenSSH
  (`--no-upgrade`; transitive Paketabhängigkeiten können weitere Änderungen erfordern);
- installiert slepp/ssh-mcp vom geprüften Commit in eine eigene venv;
- installiert OpenAIs Tunnel-Client v0.0.16 mit mitgeliefertem cloudflared,
  Manifest und Lizenzhinweisen nach `/opt/codex-ssh`;
- prüft fest eingetragene SHA-256-Werte der Upstream-Downloads; kein `latest`-Download;
- erzeugt das eigene Konto `codex-test`, ohne sudo-Rechte, und private lokale
  Loopback-Schlüssel; kein Schlüsselinhalt wird ausgegeben oder veröffentlicht;
- startet ausschließlich den separaten Dienst `codex-ssh-loopback.service` auf
  `127.0.0.1:22222`, mit Schlüsselauthentifizierung und ausgeschaltetem Forwarding;
- pinnt dessen direkt lokal erzeugten Hostschlüssel im known_hosts des Testkontos;
  dies verwendet keinen ungeprüften Netzwerk-Scan als Vertrauensanker;
- führt einen kurzen lokalen SSH-Aufruf aus, schreibt Identitätsdaten ausschließlich
  nach `/etc/codex-ssh/identity.txt` und meldet die ausstehende Tunnel-/Codex-Prüfung.

Für spätere Sitzungen liegt außerdem `/opt/codex-ssh/README.txt` mit Plattform,
Alias-/Programm-/Konfigurationspfaden und Wiederaufnahmehinweisen auf der Maschine.
Der Agent findet die Gast-Logins danach im jeweiligen VM-Description-Block.

Für die Nutzung einer bereits eingerichteten Installation zuerst
[Zugang und Hostvertrauen](../.agents/skills/codex-ssh/references/zugang.md) lesen.
Das MCP stellt den SSH-Client auf diesem privaten Host bereit; seine Aliase und
Schlüssel werden dort ausgewertet. Der Agent muss sie nicht nochmals in die
Cloud kopieren. Ein normales Root-Passwort ist für den vorhandenen Admin-Alias
nicht erforderlich. Das Manifest bleibt eine lokale Identitätsreferenz; nach
TOFU beobachtete Angaben sind keine unabhängige Erstverifikation.

Auf Proxmox gibt es zwei explizite Installationsvarianten:

- `--install`: Infrastruktur und unprivilegiertes Testkonto; vorhandene separat
  eingerichtete Verwaltungsrechte/API-Zugänge weiterverwenden.
- `--install --proxmox-admin`: zusätzlich separater SSH-Alias
  `codex-proxmox-host` für **vollen Host-Rootzugriff** über Loopback. Ein eigener
  Schlüssel liegt unter `/var/lib/codex-test/.ssh/proxmox_admin`, der erlaubte
  öffentliche Schlüssel unter `/etc/codex-ssh/proxmox-admin-authorized_keys`.
  Der eigene sshd erlaubt Root nur mit diesem Schlüssel; bestehendes System-SSH
  und `/root/.ssh/authorized_keys` bleiben unangetastet. Das ist keine
  serverseitige Einschränkung auf bestimmte VMs. Der Skill bindet den Arbeitsumfang.

Die Admin-Option ist auf Plain Debian unzulässig. Auch auf Proxmox startet der
Tunnel-Client später als `codex-test`, nicht als Root. Das Bootstrap erstellt,
startet oder löscht keine VMs und nimmt keine Änderungen an Bridges, Storage
oder Clusterkonfiguration vor. Es richtet nur den Zugang für den anschließenden
VM-Arbeitsauftrag ein. Tests und deren Abhängigkeiten gehören dann in Gäste.

Wenn OpenSSH-Server vorher nicht installiert war, werden die neuen Standardunits
`ssh.service`/`ssh.socket` maskiert, damit auch bei Neustart kein neuer öffentlicher
Standardlistener startet. Eine temporäre `policy-rc.d` blockiert automatische
Dienststarts während dieser Paketinstallation und wird anschließend entfernt.
Bei bestehender Service-Policy oder SSH-Anpassung stoppt das Skript stattdessen.
Eine bereits installierte OpenSSH-Konfiguration wird nicht umgeschrieben oder
abgeschaltet; deren bisherige Erreichbarkeit bleibt Betreiberverantwortung.
Die apt-Installation fehlender Pakete kann Abhängigkeiten und Paket-Hooks
ausführen. Ein allgemeines Host-Upgrade ist nicht Teil dieses Skripts.

Falls vorhandene Enterprise-Quellen `401 Unauthorized` liefern, lässt sich für
einen einzelnen Lauf eine bereits vorhandene Debian-Quelldatei auswählen:
`CODEX_SSH_APT_SOURCES=<ABSOLUTE_VORHANDENE_SOURCES_DATEI>` vor dem
Installationsaufruf setzen. Das ändert keine permanente apt-Konfiguration und
schaltet keine Signaturprüfung ab. Alternativ auf einem beauftragten Test-Proxmox
die offiziellen No-Subscription-Quellen mit Sicherung der Originale konfigurieren.
Diese Hostentscheidung nimmt das Bootstrap nicht automatisch vor.

Die Quellarchive und Client-Binärarchive sind gepinnt, apt-Pakete und Python-
Buildabhängigkeiten (z. B. setuptools) werden aus den konfigurierten Quellen
bezogen. Das ist kein vollständig reproduzierbarer oder unabhängig auditierter
Build. Die Client-Version wurde gegen GitHubs Release-Metadaten/Checksumme geprüft;
die aktuell im eigenen Platform-Konto unterstützte Version zusätzlich abgleichen.

## Was noch manuell bleibt

1. Als root `/etc/codex-ssh/identity.txt` lokal prüfen. Die Maschinen-ID ist noch
   kein Beleg, dass die Maschine das beabsichtigte Ziel ist: zunächst in der
   richtigen Host-/Gastkonsole verifizieren. Werte in die lokale Zielzuordnung
   für den Codex-Auftrag übernehmen, nicht ins öffentliche Repository.
2. Mit `runuser -l codex-test` zum Testkonto wechseln, `umask 077` setzen und
   `/opt/codex-ssh/tunnel-client help quickstart` lesen. Als stdio-Befehl
   `/var/lib/codex-test/mcp/bin/ssh-mcp` verwenden. Keine sudo-/Root-MCP-Verbindung.
3. Im vorgesehenen OpenAI-Konto Tunnel und Workspace-Zuordnung prüfen/anlegen.
   Runtime-Key geschützt lokal eingeben, niemals als Shell-Argument oder Chattext.
   Konkrete Flags und Secret-Referenzen anhand der installierten Client-Hilfe und
   des [offiziellen Onboardings](https://github.com/openai/tunnel-client/blob/master/docs/onboarding.md)
   verwenden. Für dauerhaften Betrieb dessen vorhandenen Runtime-Mechanismus nutzen;
   hier wird kein eigener Tunnel-Dienst oder Supervisor gebaut.
4. Tools in der tatsächlichen Codex-Cloud-Sitzung entdecken und die
   [Live-Abnahme](pruefungen.md) durchführen. Alias `codex-test-local`, Konto
   `codex-test`, Arbeitsbereich `/var/lib/codex-test/work`, Logs
   `/var/lib/codex-test/results`; Commit/Checkout und Testbefehl fehlen noch.
   Diese lokalen Standardwerte sind kein eingebautes Ziel im Skill.
5. Bei Proxmox Node, Storage, Bridge, Template/Image und Ressourcenrahmen lokal
   zuordnen. Danach den [Proxmox-Skillablauf](../.agents/skills/codex-ssh/references/proxmox.md)
   verwenden: passende VM wiederfinden oder anlegen, Gast-Login/Testpasswort in
   deren Description speichern, SSH/Identität prüfen und im Gast testen. Die
   Description ist auch für Benutzer und neue Agentensitzungen die Wiederanlaufakte.

Bis Schritt 4 ist die Maschine lokal vorbereitet, aber kein Fernzugriff aus Codex
nachgewiesen. Ein laufender Tunnel allein genügt ebenfalls nicht.

## Wiederholung und Fehler

`--check` prüft nur vorhandenen lokalen Dienst/SSH und Client-Version. Es sagt
nichts über MCP-Discovery, Tunnel, Prozesswiederaufnahme oder Tests aus.
Eine vollständig markierte Installation wird bei identischem `--install` nur
geprüft; eine abweichende Plattform oder Admin-Option wird abgewiesen. Keine
stillen Rechteänderungen bei Wiederholung. `--check` benötigt keine Admin-Option.
Bei vorhandenen reservierten Pfaden oder Konto wird nichts überschrieben. Nach
Teilabbruch zuerst Zustand prüfen; kein blindes Löschen, kein automatischer
Rollback. Eventuell installierte Pakete, Maskierungen und ein bereits gestarteter
Loopback-Dienst bleiben bestehen. Für eine wirklich frische VM ist Wiederherstellen
eines vorherigen Proxmox-Snapshots häufig der klare neue Ausgangspunkt.

Kein automatisches Deinstallationsskript: vor Löschen von Benutzer, Logs oder
Checkout deren Inhalte prüfen. Den eigenen Loopback-Dienst kann der Betreiber
gezielt mit `systemctl disable --now codex-ssh-loopback.service` stoppen.
