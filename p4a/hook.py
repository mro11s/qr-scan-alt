from pathlib import Path
from pythonforandroid.toolchain import ToolchainCL

def after_apk_build(toolchain: ToolchainCL):
    manifest_file = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    xml = manifest_file.read_text(encoding="utf-8")

    # Wenn <queries> schon existiert -> nichts tun
    if "<queries>" in xml:
        return

    queries_xml = """
    <queries>
        <intent>
            <action android:name="android.intent.action.TTS_SERVICE" />
        </intent>
    </queries>
    """

    # Insert direkt vor </manifest>
    new_xml = xml.replace("</manifest>", f"{queries_xml}\n</manifest>")
    manifest_file.write_text(new_xml, encoding="utf-8")
    print("Added <queries> for TTS_SERVICE to AndroidManifest.xml")