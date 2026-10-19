# Codex SSH Skill

Kleiner Anleitungsskill für vorhandene SSH-MCP-Werkzeuge an einer zugeordneten
Linux-Testmaschine oder einem Test-Proxmox. Codex entwickelt in der Cloud;
Tests laufen direkt auf Debian oder in Gästen des privaten Proxmox. Bestehendes
OpenSSH, SSH-MCP und Tunnel-Client werden verwendet, kein neuer Orchestrator.
Lizenz: vorhandene [MIT-Lizenz](LICENSE), auch für die neuen eigenen Dateien.

Erste Version: **v0.1.0** ·
[Skill-ZIP herunterladen](https://raw.githubusercontent.com/geco91/codex-ssh-skill/v0.1.0/downloads/v0.1.0/codex-ssh.zip) ·
[SHA-256-Prüfsumme](downloads/v0.1.0/SHA256SUMS) ·
[Versionshinweise](CHANGELOG.md).

Der Arbeitsstand nach v0.1.0 berücksichtigt den ersten erfolgreichen
MCP-/Gast-/HTTP-Test. Das versionierte v0.1.0-ZIP bleibt unverändert; aktuelle
Anweisungen einschließlich TOFU und Zugangsermittlung liegen im Skillordner.

## Installation und Nutzung

Der Skill liegt repositorylokal in
[`.agents/skills/codex-ssh/SKILL.md`](.agents/skills/codex-ssh/SKILL.md).
Für ein anderes Projekt den **ganzen Ordner** `codex-ssh` nach dessen
`.agents/skills/` kopieren. In Codex CLI/IDE mit `/skills` prüfen und
`$codex-ssh` aufrufen; bei fehlender Erkennung die Sitzung neu starten.
Ein Skill installiert oder registriert keine MCP-Verbindung. Die automatische
Erkennung im gewünschten App/Web-Cloud-Task muss dort separat geprüft werden.
Für einen Skill-Import per ZIP die verlinkte Datei verwenden; sie enthält den
Ordner `codex-ssh` mit Einstieg, Referenzen und MIT-Lizenz.
ZIP und Prüfsumme liegen versioniert unter `downloads/v0.1.0/` im Repository.

Beispielauftrag, sämtliche Namen/Pfade/SHA sind **Platzhalter**:

> Nutze $codex-ssh. Die lokale Zielzuordnung liegt in .local/target.toml.
> Prüfe die Identität der zugeordneten Test-VM und teste Commit <COMMIT_SHA>
> im freigegebenen Checkout. Du darfst dort Testlogs schreiben und den vorhandenen
> Integrationstest starten. Keine Installation und kein sudo. Nimm einen bereits
> gestarteten Lauf wieder auf. Berichte Exitcode und tatsächlichen Teststatus.

Erwarteter Ablauf: Werkzeuge/Ziel prüfen → Hostschlüsselbindung prüfen →
Maschinenidentität vergleichen → SHA/Arbeitsstand prüfen → Test einmal starten
oder vorhandenen Lauf lesen → begrenzt Logs/Endstatus lesen.
Beispielresultat (kein echter Test):
`<ALIAS> | <SHA> | <LAUF-ID> | Fehler; Exitcode 1; stderr: <bereinigter Testfehler>`.
Ohne erreichbare Werkzeuge lautet das Ergebnis „unbekannt: SSH-MCP nicht verfügbar“.

## Bereits eingerichteten Zugang verwenden

Vor neuen Passwort-/Schlüsselfragen zuerst Projektkontext und Einrichtungsprotokoll
lesen. Bei der hier dokumentierten Bootstrap-Installation läuft MCP als
`codex-test`. Für beauftragte Proxmox-Verwaltung ist mit `--proxmox-admin` der
SSH-Alias `codex-proxmox-host` eingerichtet: root über `127.0.0.1:22222`, mit
bereits vorhandenem separatem Schlüssel und gebundenem Hostschlüssel. Der Alias
`codex-test-local` ist dagegen der unprivilegierte Selbsttest auf demselben Host.
Beides sind keine Defaults für andere Installationen oder beliebige Verbindungen.

Private Schlüssel und SSH-Konfiguration liegen auf dem MCP-Host, nicht im
Codex-Cloud-Workspace. Das verwendete OpenSSH-MCP hat kein eigenes Passwortfeld;
dies beweist kein grundsätzliches Verbot von Passwortanmeldung. Der separate
Bootstrap-Listener erlaubt tatsächlich nur Schlüssel. Tunnel-Key,
SSH-Anmeldeschlüssel und SSH-Hostschlüssel erfüllen verschiedene Aufgaben.

Vorhandene geprüfte Hostschlüssel bevorzugen. Für ein eindeutig beauftragtes
neues Ziel ist nach ausdrücklicher Nutzerfreigabe TOFU mit `accept-new` möglich;
danach denselben gespeicherten Schlüssel mit `yes` prüfen. Ein geänderter
Schlüssel wird nicht automatisch übernommen. Details und Identitäts-Erstaufnahme:
[Zugang und Hostvertrauen](.agents/skills/codex-ssh/references/zugang.md).

## Debian oder Test-Proxmox initialisieren

Das vorbereitete [Bootstrap-Skript](scripts/bootstrap-debian.sh) läuft einmalig
**auf der Zielmaschine über deren lokale Konsole/AITL**. Es erkennt Debian oder
Proxmox automatisch und installiert vorhandene Komponenten,
ein Testkonto ohne sudo und einen separaten OpenSSH-Dienst nur auf
`127.0.0.1:22222`. Kein öffentliches Port-Forwarding, kein Zwischenrechner.
MCP-Server und Tunnel-Client laufen später auf dieser Maschine. Auf Proxmox
werden Projekt-Tests anschließend in zugeordneten Gast-VMs ausgeführt.

Der Download verwendet die erste veröffentlichte Version `v0.1.0`.
Als root auf Debian 12/13 oder einem Test-Proxmox 8/9 mit Internetzugang:

```sh
# Falls curl noch fehlt: apt-get update && apt-get install -y ca-certificates curl
curl --proto '=https' --tlsv1.2 -fSL \
  'https://raw.githubusercontent.com/geco91/codex-ssh-skill/v0.1.0/scripts/bootstrap-debian.sh' \
  -o bootstrap-debian.sh
less bootstrap-debian.sh                 # einmal lokal prüfen
bash bootstrap-debian.sh --dry-run       # nur Plan, keine Änderungen
bash bootstrap-debian.sh --install
```

Für den Test-Proxmox, auf dem Codex VMs anlegen/verwalten soll, stattdessen:

```sh
bash bootstrap-debian.sh --install --proxmox-admin
```

Diese ausdrücklich gewählte Option gibt dem MCP-Konto über einen separaten
Loopback-Schlüssel **vollen Host-Rootzugriff** als `codex-proxmox-host`.
Bestehende Host-SSH-Konfiguration und Root-Login-Schlüssel werden nicht verändert.
Ohne die Option bleiben die bisherigen Rechte des Testkontos maßgeblich.
Das Bootstrap erstellt noch keine Gäste; der Skill tut dies später im
beauftragten Ressourcenrahmen anhand vorhandener Storage-/Netz-/Template-Daten.

Danach `bash bootstrap-debian.sh --check` für den **lokalen** SSH-Nachweis.
Das ist noch keine Verbindung aus Codex. Anschließend als `codex-test` den
vorhandenen Tunnel-Client mit `help quickstart` einrichten, Runtime-Zugangsdaten
geschützt lokal zuführen und den Tunnel in der tatsächlichen Codex-Oberfläche
zuordnen. Das Skript startet keinen Tunnel und fragt keine Tokens ab.
Details, Betriebsgrenzen und Verhalten bei Abbruch: [Bootstrap](docs/bootstrap.md).

## Test-VMs auf Proxmox verwenden

> Nutze $codex-ssh auf dem zugeordneten Test-Proxmox. Suche zuerst nach einer
> passenden vorhandenen Test-VM und lies deren Description. Falls nötig, erstelle
> im lokal hinterlegten Ressourcenrahmen eine Debian-Test-VM aus dem freigegebenen
> Template. Hinterlege Gast-Login und Testpasswort in der Proxmox-Description.
> Prüfe den Gast als eigenes SSH-Ziel und führe die Integrationstests dort aus.

Der Skill unterscheidet Host-Verwaltung und Gast-Tests, findet nach einer Pause
VMID, Zweck, Benutzer und Testpasswort in der VM-Beschreibung wieder und prüft
vor Wiederholung alte Läufe. Gastzugriffe verwenden denselben SSH-MCP-Server
und Tunnel, mit eigenen SSH-Alias-/Identitätsdaten. Details:
[Proxmox-Ablauf](.agents/skills/codex-ssh/references/proxmox.md).

## Minimaler Betriebsaufbau

Voraussetzungen: vorhandener SSH-Zugang zur Debian-VM, dediziertes Testkonto mit
minimalen Rechten, geklärter Vertrauensmodus und Maschinenidentität,
freigegebener Checkout und Testbefehl. Ein privater Linux-Host, auch die VM selbst,
betreibt den vorhandenen MCP-Server und `openai/tunnel-client`.
Dieser Host erreicht die VM intern per SSH und OpenAI ausgehend per HTTPS/443.
Es braucht keinen Mac/Windows-Zwischenrechner und keine öffentlich erreichbare Shell.

Empfehlung für diesen Einstieg: [slepp/ssh-mcp](https://github.com/slepp/ssh-mcp)
als **stdio**-Kindprozess des Tunnel-Clients, kein zusätzlicher HTTP-Adapter.
Python ≥3.10 und OpenSSH auf dem privaten MCP-Host genügen für Befehle;
rsync/tmux sind nur für deren optionale Funktionen nötig. Version/Commit vor dem
späteren Betrieb fixieren; geprüfte Stände stehen in [Recherche](docs/recherche.md).
Das Bootstrap wurde inzwischen auf dem ausdrücklich beauftragten Test-Proxmox
installiert und dessen lokale SSH-Prüfungen bestanden. Ablauf und Grenzen:
[Live-Protokoll](docs/live-testproxmox.md). Dort ist inzwischen auch der erste
erfolgreiche Produkt-MCP-Aufruf mit Gastanlage und HTTP-Test dokumentiert.
Plain-Debian-Bootstrap und Wiederaufnahme nach Sitzungswechsel bleiben offen.

Die spätere Betreiberin/der Betreiber:

1. Installiert den gewählten vorhandenen Server in einer eigenen Umgebung;
   dessen stdio-Startbefehl ist der absolute Pfad zum installierten `ssh-mcp`.
2. Hinterlegt auf dem MCP-Host SSH-Alias, Testkonto, privaten Schlüssel/Agent und
   bevorzugt separat verifizierten known_hosts-Eintrag. Alternativ den oben
   beschriebenen ausdrücklich freigegebenen TOFU-Erstkontakt durchführen und
   dessen Status lokal festhalten. Danach `StrictHostKeyChecking yes`,
   `BatchMode yes`, kurze Verbindungszeit und deaktiviertes Agent-Forwarding.
   Keine ungeprüfte `ssh-keyscan`-Ausgabe als Vertrauensanker übernehmen.
3. Verwendet beim vorhandenen Tunnel-Client zuerst `tunnel-client help quickstart`.
   Laut [offiziellem Onboarding](https://github.com/openai/tunnel-client/blob/master/docs/onboarding.md)
   unterstützt `init` das Sample `sample_mcp_stdio_local`, `--profile`,
   `--tunnel-id` und `--mcp-command`. Reale Werte nur lokal ergänzen.
   Danach `tunnel-client doctor --profile <PROFIL> --explain` und
   `tunnel-client run --profile <PROFIL>` auf dem privaten Host.
   Keine Tunnel-ID oder Zugangsdaten in dieses Repository schreiben.
4. Ordnet den Tunnel im **tatsächlich unterstützten Zielprodukt** zu und prüft dort
   Tool-Discovery und sicheren Aufruf. ChatGPT-Verbindung und Codex-Cloud-Verbindung
   getrennt abnehmen. Ein CLI-stdio-Beispiel ist keine Cloud-Anbindungsanleitung.

## Konfiguration und Geheimnisse

Die Zielzuordnung ist eine lokale Konvention für diesen Skill, kein automatisch
ausgewertetes Serverformat. Lege sie z. B. in `.local/target.toml` an (ignoriert,
nicht befüllt mitgeliefert). Sie enthält MCP-Verbindungsname/Implementierung,
genauen SSH-Alias und Konto, bekannten Hostschlüssel-Fingerprint und Vertrauensmodus
(vorab geprüft oder TOFU mit zielbezogener Freigabe), Soll- oder erstmals
erfasste `/etc/machine-id`, Arbeits-/Logpfad, bei Code-Tests auch Checkout und
freigegebenen Testbefehl/Arbeitsumfang. Die Pfade des SSH-Clients und known_hosts
beziehen sich auf den **privaten MCP-Host**. Für mehrere Arbeitskontexte eine
explizite Zuordnung bereitstellen, keine automatische Wahl des ersten Hosts.

SSH-Konfiguration/known_hosts verbleiben geschützt auf dem MCP-Host; Schlüssel
im geeigneten geschützten Speicher oder SSH-Agent. Tunnel-Profil und
Organisation-/Workspace-Zuordnung verbleiben lokal beim Tunnel-Betreiber.
Runtime-Zugangsdaten über den unterstützten Secret-Speicher bzw. geschützte
Umgebungsreferenzen zuführen; Admin-Key nicht für den Dauerbetrieb verwenden.
Lokale Verzeichnisse/Logs privat halten (0700/0600), keine Secrets in Kommandos,
Transkripte, Screenshots oder Git schreiben. `.gitignore` ersetzt keine Prüfung.
Explizite Ausnahme für diesen Testbetrieb: Die tatsächlichen Gast-Login-Benutzer
und Testpasswörter werden in der jeweiligen Proxmox-Description hinterlegt und
bei Wiederaufnahme daraus gelesen. Das öffentliche Repository enthält nur das
Schema, keine tatsächlichen Credentials.

Der Skill ist eine Arbeitsanweisung, keine Sicherheitsgrenze. slepp erlaubt
generische Ziele und mächtige Werkzeuge einschließlich Port-Forwarding; nur die
benötigten Tools exponieren und den dedizierten MCP-Host/das Konto netzseitig
auf das Testziel beschränken. Keine produktiven Schlüssel/Agenten mitbenutzen.
Ein MCP-Server mit eigener Policy ist eine Alternative, wenn das erforderlich ist.

## Kompatibilität und Abnahme

Repositoryformat und generelle stdio-/Tunnel-Eignung sind dokumentiert.
Am 19.10.2026 wurden nach der AITL-Einrichtung tatsächliche SSH-MCP-Aufrufe über
die angebotene Produktverbindung ausgeführt: Hostidentität, Debian-13-Gastanlage,
geprüfter Gastzugang per Schlüssel und Passwort sowie Hello-World-HTTP 200.
Dies ist ein bestandener End-to-End-Smoke-Test dieser Verbindung, keine allgemeine
Produktzertifizierung. Ein separater Codex-Cloud-Task, vollständige Plain-Debian-
Bootstrap-Installation, Wiederaufnahme nach Neustart/Sitzungswechsel und ein
Projekt-Integrationstest mit Commit-SHA bleiben separat zu prüfen.
Vorhandenes Codex-Abo bevorzugen; Zugriffsrechte/Verfügbarkeit und etwaige Kosten
der Tunnel-Nutzung im eigenen Konto prüfen. Keine Agents-/Responses-API als
stillschweigender Ersatz und keine Zusage, alle Dienste seien im Abo enthalten.

[Recherche mit Quellen](docs/recherche.md) ·
[Lokale Prüfungen und Stand der Live-Abnahme](docs/pruefungen.md).
BI-MC „Codex SSH Zugriff“ ist der Hintergrund; setup-intranet und bestehende
BI-MC-/M8-/AITL-Läufe werden durch diesen Stand nicht verändert.
