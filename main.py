from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.camera import Camera
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from datetime import datetime

import numpy as np
import cv2


class RotatedCamera(Camera):
    """Kamera-Widget mit 90°-Drehung nach rechts (nur Anzeige!)"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate(angle=-90, origin=self.center)
        with self.canvas.after:
            PopMatrix()
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self.rot.origin = self.center


class QRScannerApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Gedrehtes Kamera-Widget (Option B)
        self.camera = RotatedCamera(
            resolution=(1280, 720),
            play=False,
            index=-1
        )
        self.layout.add_widget(self.camera)

        self.qr_detector = cv2.QRCodeDetector()
        self.last_scan = None

        self.result_label = Label(
            text='Scanner bereit',
            size_hint=(1, 0.2),
            font_size='18sp',
            halign='center',
            valign='middle'
        )
        self.result_label.bind(
            size=lambda *x: setattr(self.result_label, 'text_size', self.result_label.size)
        )
        self.layout.add_widget(self.result_label)

        buttons = BoxLayout(size_hint=(1, 0.15), spacing=10)

        self.toggle_button = Button(text='Scanner starten')
        self.toggle_button.bind(on_press=self.toggle_scanner)
        buttons.add_widget(self.toggle_button)

        clear_button = Button(text='Löschen')
        clear_button.bind(on_press=self.clear_result)
        buttons.add_widget(clear_button)

        self.layout.add_widget(buttons)

        self.scanning = False
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
            Clock.schedule_interval(self.scan_qr_code, 3.0)  # ⏱️ alle 3 Sekunden
            self.toggle_button.text = 'Scanner stoppen'
            self.result_label.text = 'Scanne QR-Code...'

    def scan_qr_code(self, dt):
        if not self.camera.texture:
            return

        texture = self.camera.texture
        pixels = np.frombuffer(texture.pixels, dtype=np.uint8)
        img = pixels.reshape(texture.height, texture.width, 4)

        # RGBA → BGR
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        # 1️⃣ Original prüfen
        data, _, _ = self.qr_detector.detectAndDecode(img_bgr)
        if data:
            self.result_label.text = f'QR erkannt (original):\n\n{data}'
            return

        # 2️⃣ Gespiegelt prüfen
        mirrored = cv2.flip(img_bgr, 1)
        data, _, _ = self.qr_detector.detectAndDecode(mirrored)
        if data:
            self.result_label.text = f'QR erkannt (gespiegelt):\n\n{data}'
            return

        self.result_label.text = 'Kein QR-Code gefunden'

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
