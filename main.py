from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.camera import Camera
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics import PushMatrix, PopMatrix, Rotate

import numpy as np
import cv2
import threading

# Android TTS
from jnius import autoclass
from android.runnable import run_on_ui_thread

PythonActivity = autoclass('org.kivy.android.PythonActivity')
TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
Locale = autoclass('java.util.Locale')


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


class AndroidTTS:
    """Wrapper für Android TTS über pyjnius"""
    def __init__(self):
        self.tts = TextToSpeech(PythonActivity.mActivity, None)
        self.tts.setLanguage(Locale.GERMAN)
        self.lock = threading.Lock()
        self.is_speaking = False

    def speak(self, text):
        if not text.strip():
            return

        def run():
            with self.lock:
                self.is_speaking = True
                self.tts.speak(text, TextToSpeech.QUEUE_FLUSH, None, "tts1")
                self.is_speaking = False

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        with self.lock:
            if self.is_speaking:
                self.tts.stop()
                self.is_speaking = False


class QRScannerApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # RotatedCamera wieder verwenden
        self.camera = RotatedCamera(
            resolution=(1280, 720),
            play=False,
            index=-1
        )
        self.layout.add_widget(self.camera)

        self.qr_detector = cv2.QRCodeDetector()
        self.scanning = False
        self.tts = AndroidTTS()
        self.tts_active = False

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

        buttons = BoxLayout(size_hint=(1, 0.2), spacing=10)

        self.toggle_button = Button(text='Scanner starten')
        self.toggle_button.bind(on_press=self.toggle_scanner)
        buttons.add_widget(self.toggle_button)

        self.tts_button = Button(text='Vorlesen')
        self.tts_button.bind(on_press=self.toggle_tts)
        buttons.add_widget(self.tts_button)

        clear_button = Button(text='Löschen')
        clear_button.bind(on_press=self.clear_result)
        buttons.add_widget(clear_button)

        self.layout.add_widget(buttons)
        return self.layout

    # ---------------- Scanner ----------------
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
            Clock.schedule_interval(self.scan_qr_code, 3.0)
            self.toggle_button.text = 'Scanner stoppen'
            self.result_label.text = 'Scanne QR-Code...'

    def scan_qr_code(self, dt):
        if not self.camera.texture:
            return

        texture = self.camera.texture
        pixels = np.frombuffer(texture.pixels, dtype=np.uint8)
        img = pixels.reshape(texture.height, texture.width, 4)

        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        # Original prüfen
        data, _, _ = self.qr_detector.detectAndDecode(img_bgr)
        if data:
            self.result_label.text = f'QR erkannt:\n\n{data}'
            return

        # Gespiegelt prüfen
        mirrored = cv2.flip(img_bgr, 1)
        data, _, _ = self.qr_detector.detectAndDecode(mirrored)
        if data:
            self.result_label.text = f'QR erkanntt:\n\n{data}'
            return

        self.result_label.text = 'Kein QR-Code gefunden'

    # ---------------- TTS ----------------
    def toggle_tts(self, instance):
        if self.tts_active:
            self.stop_tts()
        else:
            self.start_tts()

    def start_tts(self):
        text = "Das ist ein Beispiel Text. Du kannst ihn jederzeit stoppen, indem du die Stop Funktion testest. Klappt anscheinend nicht."
        if not text.strip():
            return
        self.tts_active = True
        self.tts_button.text = 'Stopp'
        self.tts.speak(text)

    def stop_tts(self):
        self.tts.stop()
        self.tts_active = False
        self.tts_button.text = 'Vorlesen'

    # ---------------- Misc ----------------
    def clear_result(self, instance):
        self.result_label.text = 'Ergebnis gelöscht'
        self.stop_tts()

    def on_pause(self):
        if self.scanning:
            self.camera.play = False
        self.stop_tts()
        return True

    def on_resume(self):
        if self.scanning:
            self.camera.play = True


if __name__ == '__main__':
    QRScannerApp().run()
