"""Программа сервиса: открывается в браузере, услуги запускаются кнопками.

    python app.py          # только на этом ноутбуке
    python app.py --lan    # открыть и с телефона в той же Wi-Fi сети
"""
import argparse
import datetime as dt
import html
import json
import socket
import sys
import threading
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

import specs
import tesla
import vin as vin_mod
from i18n import LANGS, alert, t as tr, ui_strings
from services import BY_ID, GROUPS, SERVICES, localized

ROOT = Path(__file__).resolve().parent
UI = ROOT / "ui" / "index.html"
JOBS = ROOT / "jobs"
SETTINGS = ROOT / "settings.json"
DEFAULT_SETTINGS = {
    "lang": "ru", "interface": "simulate", "channel": "PCAN_USBBUS1", "bitrate": 500000,
    "toolbox_url": "https://toolbox.tesla.com", "shop_name": "Tesla сервис", "shop_phone": "", "currency": "₾",
}

jobs = {}
lock = threading.Lock()


def load_settings():
    try:
        return {**DEFAULT_SETTINGS, **json.loads(SETTINGS.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(DEFAULT_SETTINGS)


def save_job(job):
    JOBS.mkdir(exist_ok=True)
    data = {k: v for k, v in job.items() if not k.startswith("_")}
    (JOBS / f"{job['id']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_jobs():
    for f in sorted(JOBS.glob("*.json")) if JOBS.exists() else []:
        try:
            job = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if job.get("status") in ("running", "capturing"):
            job["status"] = "open"  # программу закрыли посреди записи
        jobs[job["id"]] = job


def clean_client(client):
    client = dict(client or {})
    client["vin"] = (client.get("vin") or "").strip().upper()
    return client


def car_line(client):
    parts = [client.get("car"), client.get("year"), client.get("vin") and f"VIN {client['vin']}"]
    return ", ".join(p for p in parts if p)


def start_capture(job, stage):
    """Запускает запись с машины в фоне. stage: report | before | after."""
    settings = load_settings()
    lang = settings["lang"]
    service = localized(BY_ID[job["service"]], lang)
    stop = threading.Event()
    job["_stop"] = stop
    job["status"] = "capturing"

    def log(line):
        with lock:
            job["log"].append(f"{dt.datetime.now():%H:%M:%S} {line}")

    def run():
        try:
            log(tr("log.cap_" + stage, lang))
            log_path = tesla.capture(settings["interface"], settings["channel"], settings["bitrate"],
                                     service.get("minutes", 1), stop=stop, progress=log, lang=lang)
            title = service["name"] if stage == "report" else tr("title." + stage, lang, name=service["name"])
            out, summary = tesla.make_report(log_path, car_line(job["client"]), title, lang, job["client"])
            job["captures"][stage] = {"report": out.name, "alerts": summary["alerts"], "findings": summary["findings"]}
            log(tr("log.report_ready", lang, name=out.name))
            for level, text, _ in summary["findings"]:
                log({"ok": "✔", "warn": "⚠", "bad": "✖"}[level] + " " + text)
            if summary["alerts"]:
                log(tr("log.car_alerts", lang) + "; ".join(alert(a, lang) for a in summary["alerts"]))
            job["status"] = "open"
        except Exception as e:
            log(tr("log.error", lang, error=e))
            traceback.print_exc()
            job["status"] = "error"
        finally:
            job.pop("_stop", None)
            save_job(job)

    threading.Thread(target=run, daemon=True).start()


def render_act(job):
    """Акт выполненных работ для клиента."""
    e = html.escape
    s = load_settings()
    lang = s["lang"]
    service = localized(BY_ID[job["service"]], lang)
    c = job["client"]
    steps = "".join(f"<li>☑ {e(t)}</li>" for i, t in enumerate(service.get("steps", []))
                    if job["steps_done"].get(str(i)))
    caps = job["captures"]
    compare = ""
    if "before" in caps and "after" in caps:
        before, after = set(caps["before"]["alerts"]), set(caps["after"]["alerts"])
        name = lambda a: e(alert(a, lang))
        fixed = "".join(f"<li style='color:#1a7f37'>✔ {name(a)}</li>" for a in sorted(before - after))
        left = "".join(f"<li style='color:#b35900'>⚠ {name(a)}</li>" for a in sorted(before & after))
        new = "".join(f"<li style='color:#c62828'>✖ {name(a)} ({tr('act.new', lang)})</li>" for a in sorted(after - before))
        compare = f"<h2>{tr('act.compare', lang)}</h2><ul>{fixed + left + new or '<li>' + tr('act.compare_none', lang) + '</li>'}</ul>"
    links = "".join(f"<li><a href='/reports/{e(v['report'])}'>{e(v['report'])}</a></li>" for v in caps.values())
    price = f"{job['price']} {s['currency']}" if job.get("price") else "—"
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{tr('act.title', lang)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#222}}
td{{padding:4px 12px 4px 0}}li{{margin:4px 0;list-style:none}}small{{color:#777}}</style></head><body>
<h1>{tr('act.title', lang)}</h1>
<p><b>{e(s['shop_name'])}</b> {e(s['shop_phone'])}<br><small>№ {e(job['id'])} · {e(job['finished'] or '')}</small></p>
<table><tr><td>{tr('act.client', lang)}</td><td><b>{e(c.get('name', ''))}</b> {e(c.get('phone', ''))}</td></tr>
<tr><td>{tr('act.car', lang)}</td><td><b>{e(car_line(c))}</b></td></tr>
<tr><td>{tr('act.service', lang)}</td><td><b>{e(service['name'])}</b></td></tr>
<tr><td>{tr('act.price', lang)}</td><td><b>{e(price)}</b></td></tr></table>
{f"<h2>{tr('act.done', lang)}</h2><ul>{steps}</ul>" if steps else ''}{compare}
{f"<h2>{tr('act.notes', lang)}</h2><p>{e(job['notes'])}</p>" if job.get('notes') else ''}
{f"<h2>{tr('act.reports', lang)}</h2><ul>{links}</ul>" if links else ''}
</body></html>"""


def capture_metrics(capture):
    """Ключевые цифры визита из JSON отчёта: пробег, деградация, разбаланс, 12V."""
    try:
        s = json.loads((tesla.REPORTS / capture["report"]).with_suffix(".json").read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        return {}
    raw = s.get("raw", {})
    return {"odometer": raw.get("Odometer3B6"), "degradation": s.get("degradation_pct"),
            "imbalance": round(s["bricks"]["delta"] * 1000) if "bricks" in s else None,
            "v12": raw.get("v12vBattVoltage261")}


def car_jobs(vin):
    vin = (vin or "").strip().upper()
    if len(vin) != 17:
        return []
    with lock:
        found = [j for j in jobs.values() if (j["client"].get("vin") or "").upper() == vin]
    return sorted(found, key=lambda j: j["created"], reverse=True)


def car_summary(vin):
    """Коротко о машине: для подсказки при вводе VIN и списка машин."""
    found = car_jobs(vin)
    if not found:
        return None
    client = next((j["client"] for j in found if j["client"].get("name")), found[0]["client"])
    return {"vin": vin.upper(), "visits": len(found), "last": found[0]["created"][:10],
            "name": client.get("name", ""), "phone": client.get("phone", ""),
            "car": client.get("car", ""), "year": client.get("year", ""), "variant": client.get("variant", "")}


def render_car_history(vin):
    """Страница истории машины: визиты, что делали, изменения показателей."""
    e = html.escape
    s = load_settings()
    lang = s["lang"]
    found = car_jobs(vin)
    info = car_summary(vin)
    colors = {"ok": "#1a7f37", "warn": "#b35900", "bad": "#c62828"}
    icons = {"ok": "✔", "warn": "⚠", "bad": "✖"}
    fmt_date = lambda iso: f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"

    origin = vin_mod.decode(vin) or {}
    origin_line = ""
    if origin.get("tesla") and origin.get("plant"):
        origin_line = e(tr("vin.origin", lang, plant=origin["plant"], country=tr("vin.country." + origin["country"], lang)))

    trend, visits, total = [], [], 0.0
    for job in found:
        service = localized(BY_ID[job["service"]], lang)
        caps = job["captures"]
        main = caps.get("after") or caps.get("report") or caps.get("before")
        if main:
            m = capture_metrics(main)
            if any(v is not None for v in m.values()):
                trend.append((job["created"], m))
        try:
            total += float(str(job.get("price") or 0).replace(",", "."))
        except ValueError:
            pass
        findings = "".join(f'<li style="color:{colors[l]}">{icons[l]} {e(t)}</li>'
                           for l, t, *_ in (main or {}).get("findings", []))
        alerts = "".join(f"<li>⚠ {e(alert(a, lang))}</li>" for a in (main or {}).get("alerts", []))
        links = [f"<a href='/reports/{e(c['report'])}' target='_blank'>{tr('ui.report', lang)} "
                 f"{({'report': '', 'before': tr('ui.before', lang), 'after': tr('ui.after', lang)})[k]}</a>"
                 for k, c in caps.items()]
        if job.get("act"):
            links.append(f"<a href='/reports/{e(job['act'])}' target='_blank'><b>{tr('ui.act', lang)}</b></a>")
        price = f" · {e(str(job['price']))} {e(s['currency'])}" if job.get("price") else ""
        visits.append(f"""<div class="visit"><div class="vhead"><b>{fmt_date(job['created'])}</b> · {e(service['name'])}
<span class="badge">{tr('ui.status_' + job['status'], lang)}</span>{price}</div>
{f'<ul>{findings}{alerts}</ul>' if findings or alerts else ''}
{f"<p><i>{e(job['notes'])}</i></p>" if job.get('notes') else ''}
{f'<p class="links">{" · ".join(links)}</p>' if links else ''}</div>""")

    def cell(v, digits=1):
        return "—" if v is None else f"{v:,.{digits}f}".replace(",", " ")
    trend_rows = "".join(f"<tr><td>{fmt_date(d)}</td><td>{cell(m['odometer'], 0)}</td><td>{cell(m['degradation'])}</td>"
                         f"<td>{cell(m['imbalance'], 0)}</td><td>{cell(m['v12'], 2)}</td></tr>" for d, m in reversed(trend))
    trend_html = ""
    if trend_rows:
        trend_html = (f"<h2>{tr('hist.trend', lang)}</h2><table><tr><th>{tr('hist.date', lang)}</th>"
                      f"<th>{tr('sig.Odometer3B6', lang)}</th><th>{tr('row.degradation', lang)}</th>"
                      f"<th>{tr('row.imbalance', lang)}</th><th>{tr('sig.v12vBattVoltage261', lang)}</th></tr>{trend_rows}</table>")
    head = ""
    if info:
        head = (f"<p><b>{e(info['car'])} {e(str(info['year']))}</b> · VIN {e(info['vin'])}<br>"
                f"{e(info['name'])} {e(info['phone'])}<br>{origin_line}</p>"
                f"<p>{tr('hist.visits', lang, n=info['visits'])} · {tr('hist.total', lang, sum=cell(total, 0) + ' ' + s['currency'])}</p>")
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{tr('hist.title', lang)}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#222}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:6px 8px;border-bottom:1px solid #ddd;text-align:left}}
th{{font-size:13px;color:#777;font-weight:600}}.visit{{border:1px solid #e3e5e9;border-radius:10px;padding:12px 14px;margin:10px 0}}
.vhead{{font-size:16px}}.badge{{font-size:12px;background:#eef0f3;border-radius:99px;padding:2px 8px;margin-left:6px}}
ul{{padding-left:0;list-style:none;margin:8px 0}}li{{margin:3px 0}}.links{{font-size:14px;margin:6px 0 0}}
a{{color:#2563eb}}</style></head><body>
<h1>{tr('hist.title', lang)}</h1>{head}{trend_html}
<h2>{tr('hist.timeline', lang)}</h2>{"".join(visits) or '<p>—</p>'}
<p><small style="color:#777">{e(s['shop_name'])} {e(s['shop_phone'])}</small></p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, body, ctype="application/json; charset=utf-8", code=200):
        if not isinstance(body, bytes):
            body = (json.dumps(body, ensure_ascii=False) if "json" in ctype else body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def job_view(self, job):
        return {k: v for k, v in job.items() if not k.startswith("_")}

    def do_GET(self):
        path = unquote(self.path.split("?")[0])
        if path == "/":
            return self.send(UI.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/catalog":
            settings = load_settings()
            lang = settings["lang"]
            return self.send({"groups": [[g, tr("group." + g, lang)] for g in GROUPS],
                              "services": [localized(s, lang) for s in SERVICES],
                              "settings": settings, "langs": LANGS, "ui": ui_strings(lang),
                              "variants": [{"id": v["id"], "model": v["model"], "years": v["years"], "name": v["name"]}
                                           for v in specs.VARIANTS]})
        if path == "/api/vin":
            lang = load_settings()["lang"]
            query = dict(q.split("=", 1) for q in self.path.partition("?")[2].split("&") if "=" in q)
            d = vin_mod.decode(unquote(query.get("v", "")))
            if not d:
                return self.send({})
            if not d["tesla"]:
                return self.send({"lines": [tr("vin.not_tesla", lang)], "warn": True})
            lines = []
            if d["plant"]:
                lines.append(tr("vin.origin", lang, plant=d["plant"], country=tr("vin.country." + d["country"], lang)))
            lines.append(tr("vin.market." + d["market"], lang))
            if d["check_ok"] is False:
                lines.append(tr("vin.check_bad", lang))
            return self.send({"model": d["model"], "year": d["year"], "lines": lines, "warn": d["check_ok"] is False})
        if path == "/api/jobs":
            with lock:
                items = sorted((self.job_view(j) for j in jobs.values()), key=lambda j: j["created"], reverse=True)
            return self.send(items[:100])
        if path == "/api/cars":
            with lock:
                vins = {(j["client"].get("vin") or "").upper() for j in jobs.values()}
            cars = [c for c in (car_summary(v) for v in vins if len(v) == 17) if c]
            return self.send(sorted(cars, key=lambda c: c["last"], reverse=True))
        if path.startswith("/api/car/"):
            return self.send(car_summary(path.rsplit("/", 1)[1]) or {})
        if path.startswith("/car/"):
            return self.send(render_car_history(path.rsplit("/", 1)[1]), "text/html; charset=utf-8")
        if path.startswith("/api/job/"):
            job = jobs.get(path.rsplit("/", 1)[1])
            if not job:
                return self.send({"error": "job not found"}, code=404)
            with lock:
                return self.send(self.job_view(job))
        if path.startswith("/reports/"):
            f = (tesla.REPORTS / path[len("/reports/"):]).resolve()
            if f.parent == tesla.REPORTS.resolve() and f.is_file():
                return self.send(f.read_bytes(), "text/html; charset=utf-8")
        self.send({"error": "not found"}, code=404)

    def do_POST(self):
        path = unquote(self.path.split("?")[0])
        data = self.body()
        if path == "/api/settings":
            settings = {**load_settings(), **{k: v for k, v in data.items() if k in DEFAULT_SETTINGS}}
            settings["bitrate"] = int(settings["bitrate"])
            if settings["lang"] not in LANGS:
                settings["lang"] = "ru"
            SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
            return self.send(settings)
        if path == "/api/jobs":
            lang = load_settings()["lang"]
            service = BY_ID.get(data.get("service"))
            if not service:
                return self.send({"error": "unknown service"}, code=400)
            service = localized(service, lang)
            job = {"id": f"{dt.datetime.now():%Y%m%d-%H%M}-{uuid.uuid4().hex[:4]}", "service": service["id"],
                   "service_name": service["name"], "client": clean_client(data.get("client", {})),
                   "created": dt.datetime.now().isoformat(timespec="seconds"), "finished": None,
                   "status": "open", "log": [], "steps_done": {}, "captures": {}, "notes": "", "price": ""}
            if service["mode"] == "partner":
                job["log"].append(tr("log.partner", lang))
            jobs[job["id"]] = job
            if service["mode"] == "auto":
                start_capture(job, "report")
            save_job(job)
            return self.send(self.job_view(job))
        if path.startswith("/api/job/"):
            _, _, _, job_id, action = path.split("/")
            job = jobs.get(job_id)
            if not job:
                return self.send({"error": "job not found"}, code=404)
            if action == "capture":
                if job["status"] == "capturing":
                    return self.send({"error": tr("log.busy", load_settings()["lang"])}, code=409)
                start_capture(job, data.get("stage", "report"))
            elif action == "stop" and job.get("_stop"):
                job["_stop"].set()
            elif action == "update":
                for key in ("notes", "price", "steps_done", "client"):
                    if key in data:
                        job[key] = data[key]
            elif action == "finish":
                for key in ("notes", "price", "steps_done"):
                    if key in data:
                        job[key] = data[key]
                if "client" in data:
                    job["client"] = clean_client(data["client"])
                job["finished"] = f"{dt.datetime.now():%d.%m.%Y %H:%M}"
                job["status"] = "done"
                tesla.REPORTS.mkdir(exist_ok=True)
                act = tesla.REPORTS / f"act-{job['id']}.html"
                act.write_text(render_act(job), encoding="utf-8")
                job["act"] = act.name
            save_job(job)
            with lock:
                return self.send(self.job_view(job))
        self.send({"error": "not found"}, code=404)


def lan_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--lan", action="store_true", help="разрешить вход с телефона в той же сети")
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()

    load_jobs()
    server = ThreadingHTTPServer(("0.0.0.0" if args.lan else "127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"Программа открыта: {url}")
    if args.lan:
        print(f"С телефона (та же Wi-Fi сеть): http://{lan_ip()}:{args.port}")
    print("Закрыть: Ctrl+C")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
