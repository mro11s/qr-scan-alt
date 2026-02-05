"""
Android-kompatibler QR-Code Scanner mit Kivy
Debug-Version: Rotation + Spiegelung testen
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.camera import Camera
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
import numpy as np
import cv2
import time


class QRScannerApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.camera = Camera(
            resolution=(1280, 720),
            play=False,
            index=-1
        )
        self.layout.add_widget(self.camera)

        self.qr_detector = cv2.QRCodeDetector()

        self.scanning = False
        self.last_scan_ts = 0  # Zeitstempel für 3-Sekunden-Intervall

        self.result_label = Label(
            text='Scanner bereit',
            size_hint=(1, 0.25),
            font_size='16sp',
            halign='center',
            valign='middle'
        )
        self.result_label.bind(
            width=lambda *x: setattr(self.result_label, 'text_size',
                                     (self.result_label.width, None))
        )
        self.layout.add_widget(self.result_label)

        buttons = BoxLayout(size_hint=(1, 0.15), spacing=10)

        self.toggle_button = Button(text='Scanner starten')
        self.toggle_button.bind(on_press=self.toggle_scanner)
        buttons.add_widget(self.toggle_button)

        clear_btn = Button(text='Löschen')
        clear_btn.bind(on_press=self.clear_result)
        buttons.add_widget(clear_btn)

        self.layout.add_widget(buttons)

        return self.layout

    def toggle_scanner(self, instance):
        if self.scanning:
            self.scanning = False
            self.camera.play = False
            Clock.unschedule(self.scan_qr_code)
            self.toggle_button.text = 'Scanner starten'
            self.result_label.text = 'Scanner gestoppt'
        else:
            self.scanning = True
            self.camera.play = True
            Clock.schedule_interval(self.scan_qr_code, 0.5)
            self.toggle_button.text = 'Scanner stoppen'
            self.result_label.text = 'Scanne QR-Code (Debug-Modus)…'

    def scan_qr_code(self, dt):
        # nur alle 3 Sekunden scannen
        now = time.time()
        if now - self.last_scan_ts < 3:
            return
        self.last_scan_ts = now

        if not self.camera.texture:
            return

        texture = self.camera.texture
        pixels = np.frombuffer(texture.pixels, dtype=np.uint8)
        img = pixels.reshape(texture.height, texture.width, 4)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        # Rotationen definieren
        rotations = [
            ("original", img),
            ("90° rechts", cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)),
            ("180°", cv2.rotate(img, cv2.ROTATE_180)),
            ("90° links", cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)),
        ]

        for rot_name, rot_img in rotations:
            # 1️⃣ ohne Spiegelung
            data, _, _ = self.qr_detector.detectAndDecode(rot_img)
            if data:
                self.result_label.text = (
                    f"QR gefunden ({rot_name})\n\n{data}"
                )
                return

            # 2️⃣ mit Spiegelung
            mirrored = cv2.flip(rot_img, 1)
            data, _, _ = self.qr_detector.detectAndDecode(mirrored)
            if data:
                self.result_label.text = (
                    f"QR gefunden ({rot_name} + gespiegelt)\n\n{data}"
                )
                return

        self.result_label.text = "Kein QR-Code erkannt\n(alle Rotationen getestet)"

    def clear_result(self, instance):
        self.result_label.text = 'Ergebnis gelöscht'

    def on_pause(self):
        if self.scanning:
            self.camera.play = False
        return True

    def on_resume(self):
        if self.scanning:
            self.camera.play = True


if __name__ == '__main__':
    QRScannerApp().run()
