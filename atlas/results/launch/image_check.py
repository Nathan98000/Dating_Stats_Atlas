"""Before the first deploy (docs/deploy.md, "Look inside both images"):
build both images locally from the repository root, as `fly deploy` does,
and list what goes into them.

Four things are looked at:

1. The build context: what `fly deploy` uploads to Fly.io's remote
   builder. Run from the repository root, flyctl sends the working
   directory ("For Dockerfile and Buildpack builds, this is the build
   context", docs.fly.io/launch/monorepo) filtered by the .dockerignore
   there (--ignorefile "Defaults to the .dockerignore file in the working
   directory", docs.fly.io/flyctl/deploy). BuildKit applies the same file,
   so a scratch build that copies the whole context and exports it gives
   exactly those files.
2. The API image: under /app only requirements.lock, atlas/__init__.py,
   atlas/api/ and atlas/model/ without their tests, each file the
   repository's own (tracked, byte-identical); no build artifact baked in.
3. The web image: the Next.js build, its node_modules, the four pages'
   texts (byte-identical to docs/) and the public photographs.
4. Both images run together on a private network, as on Fly.io, with the
   test fixture build mounted: the pages answer, and neither app's log
   holds a search or a visitor's address (what `fly logs` would carry).

In all three: nothing from the data, the results, the pipeline, the
decision records, git or a private folder; no key file; no secret (the
patterns below, and the values of the pipeline's two API keys, read from
their gitignored files and never printed); no personal email or
home-folder path; nothing of Pew's table (pew_history_scan's detector,
which reads the private copy). node_modules is listed, not read.

    PYTHONPATH=. .venv/bin/python atlas/results/launch/image_check.py \
        --out atlas/results/launch/image_check.json

The images build for this Mac's platform (linux/arm64); Fly.io's builders
make linux/amd64, which changes the compiled dependencies, not which of
the project's files go in.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

TAGS = {"api": "dsa-check/atlas-api:launch", "web": "dsa-check/atlas-web:launch"}
DOCKERFILES = {"api": "atlas/api/Dockerfile", "web": "atlas/web/Dockerfile"}
PAGES = ("methodology.md", "crime.md", "privacy.md", "terms.md")

# what .dockerignore lets through, and what it keeps out of those folders
ALLOWED = ("requirements.lock", "atlas/__init__.py", "atlas/api/", "atlas/model/",
           *(f"atlas/docs/{p}" for p in PAGES), "atlas/web/")
EXCLUDED = ("atlas/model/tests/", "atlas/api/tests/", "atlas/web/node_modules/",
            "atlas/web/.next", "atlas/web/content/", "atlas/web/test-results/",
            "atlas/web/playwright-report/", "atlas/web/e2e/", "atlas/web/tests/")
NEVER_PREFIX = ("atlas/data/", "atlas/results/", "atlas/pipeline/", "atlas/docs/decisions/",
                ".git/", ".github/", ".claude/", ".venv/", ".pytest_cache/")
NEVER_PART = re.compile(r"(^|/)(private|__pycache__|\.DS_Store)(/|$)", re.I)
KEY_FILE = re.compile(r"(^|/)(\.env[^/]*|id_(rsa|ed25519|ecdsa)[^/]*|[^/]*\.(pem|key|p12|pfx|jks|keystore)"
                      r"|[^/]*credentials[^/]*|\.npmrc|\.netrc|\.pypirc|[^/]*api[ _-]?key[^/]*)$", re.I)
SECRETS = {
    "private key": rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "AWS access key": rb"\bAKIA[0-9A-Z]{16}\b",
    "GitHub token": rb"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{22,}",
    "Fly.io token": rb"FlyV1 fm\d_|\bfo1_[A-Za-z0-9_-]{20,}",
    "Slack token": rb"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "Google API key": rb"\bAIza[0-9A-Za-z_-]{35}\b",
    "sk- style API key": rb"\bsk-(ant-)?[A-Za-z0-9_-]{24,}",
    "Stripe live key": rb"\b[rs]k_live_[A-Za-z0-9]{16,}",
}
PERSONAL = {"personal email": rb"nathan98000@gmail\.com", "home-folder path": rb"/Users/nathann\b"}
KEY_VALUE_FILES = {"CENSUS_API_KEY": "CENSUS_API_KEY.txt", "FBI_CDE_API_KEY": "FBI Crime Data API Key.txt"}
# an .npmrc is a key file only when it carries credentials; settings alone are not
NPMRC_AUTH = re.compile(rb"_auth|_password|:username|:email", re.I)


def sh(*args: str, stdin: bytes | None = None) -> bytes:
    return subprocess.run(args, input=stdin, cwd=REPO, check=True, capture_output=True).stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Scanner:
    """Secrets, the two key values, personal details and Pew, per file."""

    def __init__(self):
        from atlas.pipeline.build import pew_guard as G
        from atlas.pipeline.build import pew_history_scan as P
        self.P = P
        self.det = P.Detector(P.load_rows(G.require_pew_table()))
        self.key_values = {}
        for name, fname in KEY_VALUE_FILES.items():
            f = REPO / fname
            v = f.read_text().strip().encode() if f.exists() else b""
            self.key_values[name] = v if len(v) >= 8 else None
        self.files = 0

    def __call__(self, path: str, data: bytes, into: dict) -> None:
        self.files += 1
        for label, rx in SECRETS.items():
            if re.search(rx, data):
                into["secrets"].append({"file": path, "pattern": label})
        for label, rx in PERSONAL.items():
            if re.search(rx, data):
                into["personal"].append({"file": path, "what": label})
        for name, v in self.key_values.items():
            if v and v in data:
                into["key_values"].append({"file": path, "key": name})
        why = self.P.failing(self.P.inspect(self.det, path, data))
        if why:
            into["pew"].append({"file": path, "why": why})

    def keys_checked(self) -> dict:
        return {k: ("checked" if v else "no key file") for k, v in self.key_values.items()}


def findings() -> dict:
    return {"secrets": [], "key_values": [], "personal": [], "pew": []}


def tracked() -> set[str]:
    return set(sh("git", "ls-files", "-z").decode().split("\0")) - {""}


def build_all() -> None:
    for name in TAGS:
        sh("docker", "build", "-q", "-f", DOCKERFILES[name], "-t", TAGS[name], ".")


def check_context(scan: Scanner, git_files: set[str]) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "context"
        sh("docker", "build", "-q", "-f", "-", "--output", f"type=local,dest={dest}", ".",
           stdin=b"FROM scratch\nCOPY . /\n")
        out = {"files": 0, "bytes": 0, "by_area": Counter(), "bytes_by_area": Counter(),
               "outside_allowed": [], "excluded_but_present": [], "never": [], "key_files": [],
               "key_file_names_cleared": [],
               "not_in_git": Counter(), "not_in_git_examples": {}, **findings()}
        for f in sorted(p for p in dest.rglob("*") if p.is_file()):
            rel = f.relative_to(dest).as_posix()
            data = f.read_bytes()
            out["files"] += 1
            out["bytes"] += len(data)
            area = "/".join(rel.split("/")[:2]) if rel.startswith("atlas/") else rel
            if rel.startswith("atlas/web/public/cities/"):
                area = "atlas/web/public/cities (photographs)"
            out["by_area"][area] += 1
            out["bytes_by_area"][area] += len(data)
            if not rel.startswith(ALLOWED):
                out["outside_allowed"].append(rel)
            if rel.startswith(EXCLUDED):
                out["excluded_but_present"].append(rel)
            if rel.startswith(NEVER_PREFIX) or NEVER_PART.search(rel):
                out["never"].append(rel)
            if KEY_FILE.search(rel):
                if rel.endswith(".npmrc") and not NPMRC_AUTH.search(data):
                    out["key_file_names_cleared"].append(
                        {"file": rel, "why": "npm settings only, no credentials"})
                else:
                    out["key_files"].append(rel)
            if rel not in git_files:
                folder = rel.rsplit("/", 1)[0]
                out["not_in_git"][folder] += 1
                out["not_in_git_examples"].setdefault(folder, rel)
            scan(rel, data, out)
    return out


def walk_image(tag: str, want, visit) -> list[tuple[str, int]]:
    """Every regular file in the image (path, size); ``visit(path, data)``
    for each one ``want(path)`` asks for, as the export streams past."""
    cid = sh("docker", "create", tag).decode().strip()
    files = []
    try:
        p = subprocess.Popen(["docker", "export", cid], stdout=subprocess.PIPE)
        with tarfile.open(fileobj=p.stdout, mode="r|") as tf:
            for m in tf:
                if not m.isfile():
                    continue
                name = m.name.lstrip("/")
                files.append((name, m.size))
                if want(name):
                    visit(name, tf.extractfile(m).read())
        p.wait()
    finally:
        sh("docker", "rm", cid)
    return files


def image_meta(tag: str) -> dict:
    info = json.loads(sh("docker", "image", "inspect", tag))[0]
    cfg = info["Config"]
    return {"image": tag, "id": info["Id"], "inspect_size_bytes": info["Size"],
            "platform": f'{info["Os"]}/{info["Architecture"]}',
            "config": {"env": [e for e in cfg.get("Env") or [] if not e.startswith(("PATH=", "GPG_KEY="))],
                       "cmd": cfg.get("Cmd"), "workdir": cfg.get("WorkingDir"),
                       "exposed_ports": sorted(cfg.get("ExposedPorts") or {}),
                       "user": cfg.get("User") or "root"}}


def ours_outside_app(files: list[tuple[str, int]]) -> list[str]:
    return [n for n, _ in files if not n.startswith("app/")
            and (n.startswith(("repo/", "data/")) or "/atlas/" in f"/{n}")]


def check_api(scan: Scanner, git_files: set[str]) -> dict:
    contents: dict[str, bytes] = {}
    files = walk_image(TAGS["api"], lambda n: n.startswith("app/"), contents.__setitem__)
    out = {**image_meta(TAGS["api"]), "app_files": [], "unexpected": [], "not_identical": [],
           "not_in_git": [], "tests_present": [], "outside_app": ours_outside_app(files),
           "atlas_in_site_packages": [n for n, _ in files if "site-packages/atlas" in n],
           **findings()}
    expected_prefix = ("atlas/api/", "atlas/model/")
    for name in sorted(contents):
        rel = name[len("app/"):]
        data = contents[name]
        out["app_files"].append({"path": rel, "bytes": len(data), "sha256": sha(data)})
        if not (rel in ("requirements.lock", "atlas/__init__.py") or rel.startswith(expected_prefix)):
            out["unexpected"].append(rel)
        if "/tests/" in f"/{rel}":
            out["tests_present"].append(rel)
        local = REPO / rel
        if not local.exists() or local.read_bytes() != data:
            out["not_identical"].append(rel)
        if rel not in git_files:
            out["not_in_git"].append(rel)
        scan(f"api:{rel}", data, out)
    shipped = {f["path"] for f in out["app_files"]}
    out["tracked_files_left_out"] = sorted(
        f for f in git_files if f.startswith(expected_prefix) and "/tests/" not in f"/{f}"
        and f not in shipped)
    return out


def check_web(scan: Scanner) -> dict:
    out = {**findings(), "app_files_read": 0}
    content: dict[str, bytes] = {}
    pub: dict[str, str] = {}
    pkg: dict = {}

    def visit(name: str, data: bytes) -> None:
        rel = name[len("app/"):]
        out["app_files_read"] += 1
        scan(f"web:{rel}", data, out)
        if rel.startswith("content/"):
            content[rel[len("content/"):]] = data
        elif rel.startswith("public/"):
            pub[rel[len("public/"):]] = sha(data)
        elif rel == "package.json":
            pkg.update(json.loads(data))

    files = walk_image(TAGS["web"], lambda n: n.startswith("app/") and not n.startswith("app/node_modules/"),
                       visit)
    app = [(n[len("app/"):], s) for n, s in files if n.startswith("app/")]
    top, top_bytes = Counter(), Counter()
    for n, s in app:
        top[n.split("/")[0]] += 1
        top_bytes[n.split("/")[0]] += s
    out.update(image_meta(TAGS["web"]))
    out["app_top"] = {k: {"files": top[k], "bytes": top_bytes[k]} for k in sorted(top)}
    out["outside_app"] = ours_outside_app(files)
    # the four pages' texts, as synced from docs/
    out["content"] = {"files": sorted(content),
                      "identical_to_docs": {p: content.get(p) == (REPO / "atlas/docs" / p).read_bytes()
                                            for p in PAGES}}
    # the public folder, against this machine's atlas/web/public
    local_pub = {p.relative_to(REPO / "atlas/web/public").as_posix(): sha(p.read_bytes())
                 for p in (REPO / "atlas/web/public").rglob("*") if p.is_file() and p.name != ".DS_Store"}
    out["public"] = {"files": len(pub), "by_extension": dict(Counter(Path(p).suffix.lower() for p in pub)),
                     "identical_to_local": pub == local_pub}
    out["next_cache_bytes"] = sum(s for n, s in app if n.startswith(".next/cache/"))
    # node_modules: listed, not read
    mods = {n.split("/")[1] if not n.split("/")[1].startswith("@") else "/".join(n.split("/")[1:3])
            for n, _ in app if n.startswith("node_modules/") and n.count("/") >= 2}
    out["node_modules"] = {"packages_top_level": len(mods),
                           "dev_dependencies_present": sorted(d for d in pkg.get("devDependencies", {}) if d in mods)}
    return out


SMOKE_QS = "sex=female&self_age=33&age=29-41&marital=never&edu=bachelors"
SMOKE_PAGES = ("/about", "/privacy", "/terms", f"/?{SMOKE_QS}", f"/city/new-york-new-york?{SMOKE_QS}",
               f"/compare/new-york-new-york/austin-texas?{SMOKE_QS}")
SMOKE_MARKERS = ("self_age", "29-41", "marital=", "bachelors")
IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def smoke() -> dict:
    """Both images run together on a private network, as on Fly.io, with the
    test fixture build mounted: every page answers, the privacy page carries
    docs/privacy.md's sections, and neither app's log holds the search or a
    visitor's address (the API's requests all come from the web app; the
    web server logs none)."""
    import time
    import urllib.error
    import urllib.request
    fix = REPO / "atlas/model/tests/golden/fixture_build"
    net, api, web, port = "dsa-check-net", "dsa-check-api", "dsa-check-web", 3199

    def clean() -> None:
        subprocess.run(["docker", "rm", "-f", api, web], capture_output=True)
        subprocess.run(["docker", "network", "rm", net], capture_output=True)

    def get(path: str) -> tuple[int, bytes]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except OSError:
            return 0, b""

    clean()
    try:
        sh("docker", "network", "create", net)
        sh("docker", "run", "-d", "--name", api, "--network", net, "-v", f"{fix}:/data/build:ro", TAGS["api"])
        sh("docker", "run", "-d", "--name", web, "--network", net, "-e", f"ATLAS_API_URL=http://{api}:8000",
           "-p", f"127.0.0.1:{port}:3000", TAGS["web"])
        for _ in range(90):
            if get("/about")[0] == 200:
                break
            time.sleep(1)
        statuses, bodies = {}, {}
        for p in SMOKE_PAGES:
            statuses[p], bodies[p] = get(p)
        logs = {}
        for name in (api, web):
            r = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
            logs[name] = r.stdout + r.stderr
        web_ip = json.loads(sh("docker", "inspect", web))[0]["NetworkSettings"]["Networks"][net]["IPAddress"]
    finally:
        clean()
    sections = re.findall(r"^## (.+)$", (REPO / "atlas/docs/privacy.md").read_text(), re.M)
    api_lines = re.findall(r'(\S+):\d+ - "(GET|POST) (\S+) HTTP', logs[api])
    leaks = [f"{name}: {m}" for name, text in logs.items() for m in SMOKE_MARKERS if m in text]
    leaks += [f"{api}: a request from {ip}" for ip, _, _ in api_lines if ip != web_ip]
    leaks += [f"{web}: an address {ip}" for ip in set(IP.findall(logs[web])) if ip != web_ip]
    leaks += [f"{web}: a request line" for line in logs[web].splitlines() if re.search(r"\b(GET|POST) /", line)]
    return {"pages": statuses,
            "privacy_sections_shown": all(s.encode() in bodies["/privacy"] for s in sections),
            "api_requests": sorted(Counter(f"{m} {p}" for _, m, p in api_lines).items()),
            "api_requests_from_web_only": all(ip == web_ip for ip, _, _ in api_lines),
            "web_log_lines": len(logs[web].splitlines()),
            "leaks": leaks}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-build", action="store_true", help="use the images already tagged")
    a = ap.parse_args()
    if not a.no_build:
        build_all()
    scan = Scanner()
    git_files = tracked()
    ver = json.loads(sh("docker", "version", "--format", "{{json .}}"))
    rec = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "head": sh("git", "rev-parse", "--short=12", "HEAD").decode().strip(),
           "working_tree_changes": sh("git", "status", "--porcelain").decode().splitlines(),
           "docker": {"client": ver["Client"]["Version"], "server": ver["Server"]["Version"]},
           "how": {"api": f"docker build -f {DOCKERFILES['api']} -t {TAGS['api']} .",
                   "web": f"docker build -f {DOCKERFILES['web']} -t {TAGS['web']} .",
                   "context": "printf 'FROM scratch\\nCOPY . /\\n' | docker build -f - "
                              "--output type=local,dest=<dir> ."},
           "context": check_context(scan, git_files),
           "api": check_api(scan, git_files),
           "web": check_web(scan),
           "run_together": smoke()}
    rec["keys_checked"] = scan.keys_checked()
    rec["files_scanned"] = scan.files
    ctx, api, web = rec["context"], rec["api"], rec["web"]
    problems = {
        "context: outside what .dockerignore allows": ctx["outside_allowed"],
        "context: excluded folders present": ctx["excluded_but_present"],
        "context: data, results, pipeline, records, git or private": ctx["never"],
        "context: key files": ctx["key_files"],
        "api: unexpected files under /app": api["unexpected"],
        "api: tests shipped": api["tests_present"],
        "api: not byte-identical to the repository": api["not_identical"],
        "api: not tracked in git": api["not_in_git"],
        "api: project files outside /app": api["outside_app"] + api["atlas_in_site_packages"],
        "web: project files outside /app": web["outside_app"],
        "web: a page text differs from docs/": [p for p, ok in web["content"]["identical_to_docs"].items() if not ok],
        "run together: a page did not answer 200": [p for p, c in rec["run_together"]["pages"].items() if c != 200],
        "run together: the privacy page lacks a section of docs/privacy.md":
            [] if rec["run_together"]["privacy_sections_shown"] else ["/privacy"],
        "run together: a log holds a search or a visitor's address": rec["run_together"]["leaks"],
    }
    for part in ("context", "api", "web"):
        for kind in ("secrets", "key_values", "personal", "pew"):
            problems[f"{part}: {kind}"] = rec[part][kind]
    rec["problems"] = {k: v for k, v in problems.items() if v}
    rec["verdict"] = "clean" if not rec["problems"] else "look at problems"
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: dict(o) if isinstance(o, Counter) else str(o)) + "\n")
    print(json.dumps({"verdict": rec["verdict"], "problems": rec["problems"],
                      "context_files": ctx["files"], "api_app_files": len(api["app_files"]),
                      "web_app_files_read": web["app_files_read"], "files_scanned": scan.files}, indent=1))


if __name__ == "__main__":
    main()
