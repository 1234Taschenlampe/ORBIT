# ORBIT – Update-System (technische Vorschau)

**Stand:** 02.11.2026. Der Update-Feed und ein Kotlin-Referenzclient sind im Repository. **Der Client ist noch in keiner der bisherigen APKs eingebaut**, und es wurde kein neuer Android-Build erstellt oder auf einem Gerät getestet.

## Architektur

1. **APK hochladen:** Jede veröffentlichte Datei liegt unter apks/ und ist in apps.json registriert.
2. **Automatisches Indexing:** Ein GitHub-Actions-Workflow startet nach Änderungen an apks/ und erzeugt updates.json aus den tatsächlich vorhandenen APK-Binärdateien.
3. **Metadaten:** Paketkennung, versionCode, versionName, min/target SDK, SHA-256 der Datei und SHA-256 des APK-Signaturzertifikats.
4. **Update prüfen:** Ein ORBIT-Client vergleicht die installierte App mit dem Feed. Es werden nur **höhere versionCodes mit gleicher Paketkennung und exakt passendem aktuellem Signaturzertifikat** vorgeschlagen; Debug- und Beta-Builds werden in der Referenzimplementierung nicht automatisch angeboten.
5. **Automatischer Download:** Nach Zustimmung des Nutzers oder nach ausdrücklicher Aktivierung einer Update-Einstellung kann der Client die Datei im Hintergrund laden. Der SHA-256-Prüfsummenvergleich ist Pflicht.
6. **Installation:** Androids offizieller Paketinstaller übernimmt. Normalerweise muss der Nutzer die Installation bestätigen.

**Empfehlung:** Eine eigenständige ORBIT-Android-App dient künftig als zentraler Update-Manager für alle ORBIT-Apps; so müssen die bisherigen Apps nicht alle einzeln mit einem Updater nachgerüstet werden. Für eine zentrale App sind Paket-Sichtbarkeit per <queries> und konsistente Release-Signaturen zu berücksichtigen.

## Wichtige Einschränkungen

- Solange der Ordner apks/ fehlt, bleibt updates.json bewusst leer.
- Ein installierter Altbuild kann **nicht** einfach über ein anders signiertes APK aktualisiert werden. Das trifft insbesondere auf ReelGuard, Tagezähler und mehrere Routinen-/WiFiQuiet-Builds zu. Datenmigration und Neuinstallation können notwendig sein.
- LocalVoice v0.3.x (Tastatur) und v0.4.x (Overlay) sind **unterschiedliche Paketkennungen** und dürfen nicht als identische Update-Reihe behandelt werden.
- Selbstsignierte APKs brauchen ein **langfristig gesichertes, nicht öffentliches Release-Keystore**. Der Keystore darf niemals in GitHub eingecheckt werden.
- Eine statische Prüfung der Signaturzertifikate ist nicht gleichbedeutend mit vollständiger kryptografischer APK-Verifikation. Vor einem offiziellen Release apksigner verify sowie echte Geräte-Tests durchführen.
- Berechtigungen und Android-Versionen müssen auf dem Zielgerät geprüft werden.
- Die externe GitHub-API erlaubt bei anonymen API-Anfragen derzeit nur begrenzte Abrufe. Die Android-App soll bevorzugt den statischen updates.json-Feed lesen und mit ETag/Cache höchstens ca. einmal täglich aktualisieren.
- Downloads über HTTPS durchführen; Datei-Hash prüfen; keine APK ohne verständliche Einwilligung installieren.
- Vollständig unbeaufsichtigte Installation ist auf normalen Geräten nicht allgemein garantiert: Android setzt hierfür enge Bedingungen (PackageInstaller, Installer-of-record, Update Ownership, API-Level), und kann die Systembestätigung verlangen.

## Dateien

- tools/build_updates.py: Standard-Python-Skript, liest ausschließlich veröffentlichte APKs und erstellt updates.json.
- .github/workflows/refresh-updates.yml: aktualisiert den Index nach APK-Uploads.
- updater/OrbitUpdateClient.kt: **nicht kompiliertes Referenzmodul** für Prüfung, Download und Start des Android-Paketinstallers.

## Einbindung in ein bestehendes Android-Studio-Projekt

In AndroidManifest.xml zusätzlich:
- android.permission.INTERNET
- android.permission.REQUEST_INSTALL_PACKAGES, wenn Nutzer APKs über diese App installieren sollen
- FileProvider unter application, authority PACKAGE_NAME.orbit.fileprovider, exported=false und grantUriPermissions=true
- Meta-Data android.support.FILE_PROVIDER_PATHS -> res/xml/orbit_file_paths.xml
- Für eine zentrale Store-App: <queries> für bekannte Paketkennungen, damit sie unter Android 11+ gefunden werden können.

res/xml/orbit_file_paths.xml:

    <?xml version="1.0" encoding="utf-8"?>
    <paths xmlns:android="http://schemas.android.com/apk/res/android">
        <cache-path name="orbit_updates" path="orbit/" />
    </paths>

Gradle-Abhängigkeit für FileProvider: androidx.core:core (zu einer kompatiblen stabilen Version, abhängig vom Projekt).

**Threads:** check() und download() auf einem Worker-Thread ausführen. launchInstaller() aus einer UI-Aktion aufrufen. Für tägliche Prüfungen WorkManager mit eindeutiger periodischer Arbeit und Netzwerk-Constraints einsetzen.

**Dieses Modul ist noch kein fertiger App Store und ersetzt keine Tests.**
