# ORBIT

**Ein unabhängiger, durchsuchbarer App-Katalog für Android.**

[Store öffnen (nach Aktivierung von GitHub Pages)](https://1234taschenlampe.github.io/ORBIT/) · [APKs](https://github.com/1234Taschenlampe/ORBIT/tree/main/apks) · [Fehler melden](https://github.com/1234Taschenlampe/ORBIT/issues)

## Was ist enthalten?

- Responsive Store-Oberfläche mit Suche, Kategorien und App-Detailansichten
- **11 Projekte / 25 APK-Dateinamen** im Katalog (apps.json)
- Alle Versionen getrennt nach Projekt, inklusive Beta- und Debug-Kennzeichnung
- Automatische Prüfung, welche Dateien tatsächlich unter apks/ im Repository verfügbar sind
- Direkter Download **nur für nachweislich hochgeladene APKs**
- Keine QR-Codes und keine Fremdinstaller

**Status:** Die im Katalog eingetragenen APKs wurden nur auf Dateistruktur geprüft (ZIP-Integrität, AndroidManifest.xml, classes.dex und APK-Signaturblock). Installation und Laufzeitfunktionen auf realen Android-Geräten wurden **nicht** verifiziert. Bekannte Probleme einzelner Apps stehen im Katalog. Ein APK-Name wie „Release“ ist kein Nachweis für Fehlerfreiheit.

## Website aktivieren (einmalig)

GitHub Pages für dieses öffentliche Repository aktivieren:

1. **Settings** → **Pages**
2. Unter **Build and deployment**: **Deploy from a branch**
3. Branch **main** und Ordner **/(root)** wählen → **Save**
4. Nach erfolgreicher Bereitstellung: **https://1234taschenlampe.github.io/ORBIT/**

Falls GitHub Pages noch nicht aktiviert wurde, liegen die fertigen Store-Dateien bereits in index.html und apps.json, aber die öffentliche Website ist noch nicht über die Pages-Adresse erreichbar.

## APKs veröffentlichen

Die APKs werden ausschließlich in apks/ gespeichert. Das Verzeichnis wird nicht automatisch aus dem Katalog erzeugt.

Für das vorbereitete Archiv ORBIT_Alle_25_APKs.zip:

1. **Git für Windows** installieren und sich bei GitHub anmelden.
2. tools/ORBIT-Publish.ps1 herunterladen und neben das APK-Archiv legen.
3. In PowerShell ausführen:

    powershell -ExecutionPolicy Bypass -File .\ORBIT-Publish.ps1

Das Skript kopiert ausschließlich .apk-Dateien, prüft die ZIP/APK-Kennung und pusht den Commit nach main. Es verändert weder die Store-Website noch andere Dateien. Es benötigt Git-Zugang mit Schreibberechtigung.

**Wichtig:** GitHub warnt bei Dateien über 50 MB. Die größte der vorhandenen APKs ist knapp 78,1 MB groß und liegt damit unter der GitHub-Grenze von 100 MB pro Einzeldatei.

## Projekte

ReelGuard · LocalVoice · Tagezähler · Routinen · Privacy Guard · NächsteStunde · ReelFlow · Tune760Control · GrainFrame · NFC Lab · WiFiQuiet

## Wartung

- Neue App oder neue Version: Eintrag in apps.json ergänzen und die APK unter apks/ hochladen.
- Die Oberfläche zeigt eine Download-Aktion erst an, wenn die konkrete Datei über die öffentliche GitHub Contents API im APK-Verzeichnis nachgewiesen wurde.
- Funktionstests und bekannte Fehler müssen vor einer Statusänderung nachvollziehbar dokumentiert werden.
- APKs auf keinen Fall ohne Zustimmung veröffentlichen, wenn sie private Zugangsdaten, personenbezogene Daten oder fremde Software enthalten.

Dieses Projekt ist ein unabhängiger APK-Katalog und steht in keiner Verbindung mit dem Google Play Store.
