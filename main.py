
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
import time

# Android TTS
from jnius import autoclass, PythonJavaClass, java_method
from android.runnable import run_on_ui_thread

PythonActivity = autoclass('org.kivy.android.PythonActivity')
TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
Locale = autoclass('java.util.Locale')
Bundle = autoclass('android.os.Bundle')


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


# ---------------------------
# Native Android TTS (stabil)
# ---------------------------

class _TTSOnInitListener(PythonJavaClass):
    __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
    __javacontext__ = 'app'

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    @java_method('(I)V')
    def onInit(self, status):
        # Callback kann aus nicht-UI-Thread kommen -> via Kivy Clock zurück
        def _apply(dt):
            self.owner.is_ready = (status == TextToSpeech.SUCCESS)
            if self.owner.is_ready and self.owner.tts:
                # Sprache setzen (optional: Ergebnis prüfen)
                self.owner.tts.setLanguage(Locale.GERMAN)
                # Listener setzen (safe)
                self.owner.tts.setOnUtteranceProgressListener(self.owner._progress_listener)

                # Pending Speak nach Init (falls speak() zu früh kam)
                if self.owner._pending_text:
                    txt = self.owner._pending_text
                    self.owner._pending_text = None
                    self.owner.speak(txt)

        Clock.schedule_once(_apply, 0)


class _TTSProgressListener(PythonJavaClass):
    # UtteranceProgressListener ist eine (abstrakte) Klasse -> __javaclass__
    __javaclass__ = 'android/speech/tts/UtteranceProgressListener'
    __javacontext__ = 'app'

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    @java_method('(Ljava/lang/String;)V')
    def onStart(self, utteranceId):
        Clock.schedule_once(lambda dt: setattr(self.owner, 'is_speaking', True), 0)

    @java_method('(Ljava/lang/String;)V')
    def onDone(self, utteranceId):
        Clock.schedule_once(lambda dt: setattr(self.owner, 'is_speaking', False), 0)

    # required abstract (deprecated in API 21, but still present)
    @java_method('(Ljava/lang/String;)V')
    def onError(self, utteranceId):
        Clock.schedule_once(lambda dt: setattr(self.owner, 'is_speaking', False), 0)

    # newer overload (API 21+)
    @java_method('(Ljava/lang/String;I)V')
    def onError__2(self, utteranceId, errorCode):
        Clock.schedule_once(lambda dt: setattr(self.owner, 'is_speaking', False), 0)

    @java_method('(Ljava/lang/String;Z)V')
    def onStop(self, utteranceId, interrupted):
        Clock.schedule_once(lambda dt: setattr(self.owner, 'is_speaking', False), 0)


class AndroidTTS:
    """Wrapper für Android TTS über pyjnius, stabil Start/Stop + Init-Handling"""
    def __init__(self):
        self.tts = None
        self.is_ready = False
        self.is_speaking = False
        self._pending_text = None

        self._init_listener = _TTSOnInitListener(self)
        self._progress_listener = _TTSProgressListener(self)

        self._init_tts()

    @run_on_ui_thread
    def _init_tts(self):
        # Init ist asynchron -> OnInitListener setzt is_ready
        self.tts = TextToSpeech(PythonActivity.mActivity, self._init_listener)

    def speak(self, text: str):
        if not text or not text.strip():
            return

        # Wenn noch nicht bereit: merken und nach Init sprechen
        if not self.is_ready or not self.tts:
            self._pending_text = text
            return

        @run_on_ui_thread
        def _speak():
            b = Bundle()
            utt_id = str(int(time.time() * 1000))  # unique
            # QUEUE_FLUSH: bricht vorherige Queue ab
            self.tts.speak(text, TextToSpeech.QUEUE_FLUSH, b, utt_id)

        _speak()

    def stop(self):
        if not self.tts:
            return

        @run_on_ui_thread
        def _stop():
            # Immer stoppen (nicht vom eigenen Flag abhängig)
            self.tts.stop()
            self.is_speaking = False
            self._pending_text = None

        _stop()

    def shutdown(self):
        """Empfohlen, um native Ressourcen freizugeben."""
        if not self.tts:
            return

        @run_on_ui_thread
        def _shutdown():
            try:
                self.tts.stop()
                self.tts.shutdown()
            except Exception:
                pass
            self.tts = None
            self.is_ready = False
            self.is_speaking = False
            self._pending_text = None

        _shutdown()


class QRScannerApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # RotatedCamera verwenden
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
            self.result_label.text = f'QR erkannt:\n\n{data}'
            return

        self.result_label.text = 'Kein QR-Code gefunden'

    # ---------------- TTS ----------------
    def toggle_tts(self, instance):
        if self.tts_active:
            self.stop_tts()
        else:
            self.start_tts()

    def start_tts(self):
        text = ("Das ist ein Beispiel Text. Du kannst ihn jederzeit stoppen, "
                "indem du die Stop Funktion testest. Jetzt funktioniert es stabil auf Android.")
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

    def on_stop(self):
        # App wird wirklich beendet -> Ressourcen freigeben
        try:
            self.tts.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    QRScannerApp().run()
