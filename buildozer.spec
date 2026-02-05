# Buildozer Konfiguration für QR-Code Scanner Android App

[app]

# App-Name (wie er auf dem Gerät erscheint)
title = QR Scanner

# Package-Name (eindeutig, reverse domain)
package.name = qrscanner

# Package-Domain (reverse domain notation)
package.domain = org.qrapp

# Quellcode-Verzeichnis
source.dir = .

# Haupt-Python-Datei
source.include_exts = py,png,jpg,kv,atlas

# Version
version = 1.0

# Requirements (WICHTIG: opencv, NICHT opencv-python!)
# python3 = Python 3
# kivy = Kivy Framework
# opencv = OpenCV für Android (wird von p4a kompiliert)
# numpy = NumPy (Abhängigkeit von OpenCV)
requirements = python3==3.10.11,hostpython3==3.10.11,kivy,opencv,numpy,pyjnius

# Orientierung (portrait, landscape, sensor)
orientation = portrait

# Services (nicht benötigt für diese App)
#services = 

# Android Permissions
# CAMERA = Kamera-Zugriff erforderlich!
android.permissions = CAMERA, INTERNET

# App-Icon (optional, falls vorhanden)
#icon.filename = %(source.dir)s/data/icon.png

# Presplash (optional, Ladebildschirm)
#presplash.filename = %(source.dir)s/data/presplash.png

# Android API Level
# API 31 = Android 12 (empfohlen für moderne Geräte)
android.api = 31

# Minimale API (Android 5.0 = API 21)
android.minapi = 21

# NDK Version (für native Kompilierung)
android.ndk = 25b

# (str) Filename to the hook for p4a
p4a.hook = p4a/hook.py


# Build-Tools
android.accept_sdk_license = True

# Architektur (armeabi-v7a = ARM 32-bit, arm64-v8a = ARM 64-bit)
# arm64-v8a für moderne Geräte empfohlen
android.archs = arm64-v8a

# App-Theme
#android.theme = @android:style/Theme.NoTitleBar

# Wakelock (Bildschirm bleibt an)
android.wakelock = True

# Logcat-Filter während Build
android.logcat_filters = *:S python:D

# Gradle Dependencies (falls zusätzliche Android-Libs benötigt)
#android.gradle_dependencies = 

# Android-Add-JARs
#android.add_jars = 

# Fullscreen
fullscreen = 0

[buildozer]

# Log-Level (0 = nur Errors, 2 = debug)
log_level = 2

# Warnung bei Root
warn_on_root = 1

# Build-Verzeichnis
build_dir = ./.buildozer

# Bin-Verzeichnis (APK Output)
bin_dir = ./bin
