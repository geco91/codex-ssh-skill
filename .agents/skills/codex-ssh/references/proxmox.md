# Debian oder Proxmox: Auftrag am richtigen Ort ausführen

## Modus und Rechte

Nach der Identitätsprüfung lokal konfigurierte Rolle mit beobachteter Umgebung
abgleichen. `/etc/pve` plus vorhandenes `pveversion` und `qm` kennzeichnet den
Proxmox-Ablauf. Nur ein Teil davon oder eine widersprüchliche Konfiguration:
Zustand klären, nicht auf normalen Debian-Installationsmodus zurückfallen.

- Plain Debian: direkt im freigegebenen Checkout auf dieser Maschine testen.
- Proxmox: MCP/Tunnel und erforderliche Verwaltungswerkzeuge auf dem Host;
  Projektabhängigkeiten und Tests in ausdrücklich zugeordneten Test-VMs.

Nutze vorhandene `qm`-/Proxmox-API-Funktionen. Ermittle tatsächliche Optionen
mit installierter Hilfe, statt Flags oder API-Endpunkte zu erfinden. Der
Bootstrap kann mit `--install --proxmox-admin` den privaten SSH-Alias
`codex-proxmox-host` als Host-Root einrichten. Das ist voller Hostzugriff,
keine technische Beschränkung auf einzelne VMIDs. Ohne diese Option verwendet
das Konto nur seine bestehenden Rechte; fehlende Verwaltungsrechte konkret melden.
Ein vorhandener autorisierter Proxmox-API-Zugang ist ebenso nutzbar.

## VM anlegen und wiederfinden

1. Lies zuerst `qm list` und die Beschreibungen der für den Auftrag relevanten
   VMs. Suche nach Aufgabe/Laufkennung und Projekt, nicht nur nach einem Namen.
   Lies vorhandene Gast-Logins aus deren Description. Nutze eine zugehörige
   vorhandene VM weiter, soweit deren Zustand zum Auftrag passt.
2. Vor einer Neuanlage müssen Umfang/Ressourcenrahmen, Zielnode, Storage, Bridge,
   freigegebenes Template oder Image und Herkunft/Integrität bekannt sein.
   Vorhandene Konfiguration bevorzugen; fehlende Werte konkret abfragen.
   Keine Beispiel-IP, Bridge, Storage-ID oder VMID als reale Vorgabe verwenden.
   Für statische Netze IP/Präfix, Gateway, DNS und vorgesehene Nutzung der Adresse
   klären. VLAN-Zugehörigkeit des vorhandenen Anschlusses von einem erforderlichen
   Gast-/Bridge-Tag unterscheiden: Hostadresse, Bridge-Ports und VLAN-Konfiguration
   lesen. Kein zusätzliches Tag allein aus der Nummer des Subnetzes ableiten;
   bei verbleibender Mehrdeutigkeit vor der Netzkonfiguration nachfragen.
3. Nutze bevorzugt ein vorhandenes geprüftes Debian-Cloud-Init-Template und
   `qm clone`, sonst den vorhandenen dokumentierten `qm create`-/Import-Ablauf.
   Cloud-Init, Testbenutzer, Login-Schlüssel und das verlangte Testpasswort
   gehören in den Gast. Konfiguration, Authentifizierungsregeln und verfügbaren
   Speicher prüfen; kein Dist-Upgrade oder Projektpakete auf dem Proxmox-Host.
4. Freie VMID unmittelbar vor Erstellen erneut prüfen; VMID/Projekt/Laufkennung
   und den jeweils erreichten Schritt sofort in der Description festhalten.
   Erst nach bestätigtem Erstellen die nächsten Schritte ausführen. Nach Timeout
   Bestand und Taskstatus prüfen, bevor create/clone erneut gesendet wird.
   Keine vorhandene fremde VM überschreiben oder automatisch löschen.
5. Schreibe die unten definierte Description einschließlich Login/Testpasswort
   bereits vor dem ersten Start, aktualisiere sie nach IP-/Identitätsprüfung.
   Nach Diskimport, Cloud-Init/Seed-Anbindung und Description-Änderungen die
   tatsächlich gespeicherte VM-Konfiguration lesen: richtige Systemdisk,
   Bootreihenfolge mit Systemdisk zuerst, Seed-Medium, NIC/Bridge und gegebenenfalls
   VLAN-Tag, Ressourcen und Guest-Agent-Kanal. Secrets aus der Ausgabe ausblenden.
   Einen Bootfehler der eigenen neuen VM über deren Konsole diagnostizieren
   und gezielt korrigieren; keine zweite VM auf Verdacht anlegen.
   Der Hersteller-Taskstatus oder `qm status` belegt noch keine SSH-Bereitschaft.
6. Ermittle die Gastadresse über vorhandene DHCP-/Cloud-Init-/Guest-Agent-Daten.
   Bei einem Klon eigene Maschinen-ID und eigene SSH-Hostschlüssel erzeugen
   lassen und prüfen; keine unveränderte Template-Identität als Gastnachweis nutzen.
   Pinne den Gast-Hostschlüssel bevorzugt über einen unabhängigen vertrauenswürdigen Kanal,
   z. B. bereits eingerichteten QEMU Guest Agent oder lokale Gastkonsole.
   Eine bloß ermittelte IP oder ein Netzwerk-Keyscan genügt dafür nicht.
   Nur bei ausdrücklicher Freigabe für diesen Gast gilt alternativ der
   [TOFU-Ablauf](zugang.md); dessen Grenze entsprechend kennzeichnen.
7. Ergänze einen eigenen SSH-Alias auf dem MCP-Host für die VM, mit deren Konto,
   Hostschlüsselbindung und begrenzten Verbindungszeiten. Der vorhandene
   SSH-MCP-Server kann dieses Gastziel über denselben Tunnel ansprechen.
   Wechsel explizit auf diesen Alias und prüfe Maschinen-ID, Benutzer und Pfad.
   Cloud-Code separat übertragen/bereitstellen; SHA und Arbeitsstand vergleichen.
8. Tests nach [Testablauf](ablauf.md) ausführen. VMID, Gastalias und Testlauf in der
   Description aktuell halten, dort keine ständig wachsenden Logs ablegen.
   Bei einem Hello-World-Webserver Cloud-Init/Provisioning-Endstatus, aktiven
   Webdienst, Gastzugang und HTTP 200 mit erwartetem Inhalt prüfen; zusätzlich
   aus dem vorgesehenen Netz außerhalb des Gasts abrufen, soweit erreichbar.
   Bei verlangtem Passwort-Login diesen tatsächlich testen oder als ungeprüft
   melden; ein erfolgreicher Schlüssel-Login beweist ihn nicht. Eine Paket-/
   Provisioning-SHA ersetzt keine getestete Projekt-Commit-SHA und umgekehrt.

Ein VM-Erstellungsauftrag mit gegebenem Ressourcenrahmen deckt die notwendigen
Routinebefehle ab. Nur fehlende Konfiguration/Rechte oder Erweiterungen des
Auftrags klären, nicht jeden bereits gedeckten Befehl erneut bestätigen lassen.

## Dauerhafte Description: explizit gewünschte Test-Logins

Die Proxmox-Description (im Summary sichtbar) ist die Wiederanlaufakte für
Benutzer und spätere Agentensitzungen. Speichere dort für **selbst angelegte,
zugeordnete Test-VMs** deren tatsächlichen Login-Benutzer und das tatsächliche
Testpasswort im Klartext. Erzeuge pro VM einen Test-Login; keine Platzhalter als
fertige Einrichtung ausweisen. Installiere/konfiguriere Gast-SSH so, dass der
dokumentierte Login tatsächlich funktioniert, und prüfe ihn. Ein Schlüssel
kann für die automatisierten MCP-Aufrufe zusätzlich verwendet werden.

Für das öffentliche Repository nur dieses Schema, Werte erst lokal erzeugen:

```text
Codex test VM — schema 1
Purpose/project: <PROJECT>
Task/run: <TASK_OR_RUN_ID>
Node / VMID / name: <NODE> / <VMID> / <NAME>
Created UTC: <UTC>
Template/image and version: <SOURCE>
Resources / storage / bridge: <CONFIGURED_VALUES>
Guest IP / SSH alias: <ADDRESS_AND_PREFIX> / <ALIAS>
Gateway / DNS / VLAN attachment: <CONFIGURED_VALUES>
Login user: <GUEST_TEST_USER>
Login password: <GENERATED_GUEST_TEST_PASSWORD>
Login verified UTC: <UTC_OR_PENDING>
Guest identity / SSH fingerprint: <VERIFIED_VALUES_OR_PENDING>
Trust mode / login methods tested: <PIN_OR_TOFU> / <KEY_PASSWORD_OR_PENDING>
Provisioning / service / HTTP checks: <STATUS_EXITCODES_AND_EXPECTED_CONTENT>
Checkout / tested SHA / logs: <PATHS_AND_SHA_OR_PENDING>
Provisioning state / active run: <STATE_AND_REFERENCE>
Retention / cleanup scope: <USER_AUTHORIZED_POLICY>
```

Beschreibung mit der vorhandenen Proxmox-Konfigurationsfunktion aktualisieren
(z. B. `qm set` mit `--description`, anhand installierter Hilfe prüfen).
Vorhandene Benutzertexte erhalten; nur den eigenen abgegrenzten Block ändern.
Keine Passwörter als feste Literale in öffentlichen Skripten oder Chatbefehlen
einbetten. Werte lokal erzeugen, beim Konfigurieren einsetzen und deren unnötige
Ausgabe/Trace-Logging vermeiden. Tunnel-Keys und Host-Root-Zugangsdaten gehören
nicht zu diesem Gast-Login-Block.

## Wiederaufnahme nach längerer Pause

Zuerst Hostidentität, VM-Bestand und passenden Description-Block lesen. VMID,
Zweck, Credentials und vorherige Laufkennung übernehmen; Istzustand/Gastidentität
erneut prüfen. Fehlende Daten oder ein Loginfehler sind ein konkreter
Reparaturschritt, kein Anlass für eine blinde Neuanlage oder Passwortrotation.
Vor dem erneuten Teststart alten Prozess/Lauf und Ergebnisdateien prüfen.
Löschen, Wiederherstellen von Snapshots oder Ersetzen einer VM nur im dafür
erteilten Umfang. Ein Installationsauftrag löscht keine älteren Test-VMs.
