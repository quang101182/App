"""Usage : python test_garde_webapk_samsung.py <paquet WebAPK>
3 scenarios x 3 cycles (force-stop + relance) dans la WebAPK secondaire du Samsung.
A : toucher, retour -> reste au 1er plan ; retour immediat -> quitte.
B : toucher, retour, attendre 4 s, toucher, retour -> reste encore (garde reposee au geste)."""
import subprocess, time, sys
A = r"C:/Users/quang/AppData/Local/Android/Sdk/platform-tools/adb.exe"
S = ["-s", "RFCT32ATWGJ"]
PKG = sys.argv[1]   # paquet WebAPK de la secondaire (adb shell pm list packages | findstr webapk) -- jamais ecrit ici : depot public
def adb(*a):
    return subprocess.run([A, *S, *a], capture_output=True, text=True).stdout
def dansApp():
    r = adb("shell", "dumpsys activity activities | grep topResumedActivity")
    return "SameTaskWebApkActivity" in r
def lancer():
    adb("shell", "am", "force-stop", PKG); time.sleep(1)
    adb("shell", "monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1"); time.sleep(10)
def toucher(): adb("shell", "input", "tap", "200", "300"); time.sleep(1.5)   # texte d'aide, zone neutre
def retour(p=0.8): adb("shell", "input", "keyevent", "KEYCODE_BACK"); time.sleep(p)
ok = ko = 0
def verif(nom, cond):
    global ok, ko
    ok += cond; ko += not cond; print(("OK " if cond else "KO ") + nom)
for c in range(3):
    lancer(); verif(f"c{c} lancee", dansApp())
    toucher(); retour(); verif(f"c{c} A 1er retour = reste", dansApp())
    retour(1.5); verif(f"c{c} A 2e retour rapide = quitte", not dansApp())
    lancer(); toucher(); retour(); verif(f"c{c} B 1er retour = reste", dansApp())
    time.sleep(4); toucher(); retour(); verif(f"c{c} B apres nouveau toucher = reste encore", dansApp())
    time.sleep(0.3)
print(f"VERDICT {ok}/{ok+ko}")
adb("shell", "am", "force-stop", PKG)
