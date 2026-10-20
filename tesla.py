"""Диагностика Tesla Model 3 / Y по CAN-шине (только чтение).

Команды:
    python tesla.py listen   --interface pcan  --channel PCAN_USBBUS1 --minutes 5
    python tesla.py listen   --interface slcan --channel COM3          --minutes 5
    python tesla.py report   logs/2026-10-19_18-00-00.asc --car "Model 3 2019 VIN..."
    python tesla.py simulate              # фейковый лог для проверки без машины
"""
import argparse
import datetime as dt
import html
import json
import random
import sys
import time
from pathlib import Path

import can
import cantools

import carmap
import specs
import vin as vin_mod
from i18n import alert, t as tr

ROOT = Path(__file__).resolve().parent
DBC_FILE = ROOT / "dbc" / "Model3CAN.dbc"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"

# Ключевые сигналы для отчёта; подписи на трёх языках — в i18n.py (ключи sig.<имя>)
KEY_SIGNALS = [
    "Odometer3B6", "SOCUI292", "SOCave292", "BattVoltage132", "SmoothBattCurrent132",
    "BMS_nominalFullPackEnergy", "BattBeginningOfLifeEnergy292", "BMS_nominalEnergyRemaining",
    "BMSminPackTemperature", "BMSmaxPackTemperature", "BattBrickVoltageMin332", "BattBrickVoltageMinNum332",
    "BattBrickVoltageMax332", "BattBrickVoltageMaxNum332", "v12vBattVoltage261",
    "TotalChargeKWh3D2", "TotalDischargeKWh3D2",
    "TPMSFLpressure31F", "TPMSFRpressure31F", "TPMSRLpressure31F", "TPMSRRpressure31F",
]

# Ориентировочные пороги для подсказок (не официальные значения Tesla)
CELL_DELTA_WARN = 0.030  # В, разбаланс ячеек
CELL_DELTA_BAD = 0.080
DEGRADATION_WARN = 15.0  # %
DEGRADATION_BAD = 25.0
LOW_12V = 12.2  # В


def load_db():
    return cantools.database.load_file(DBC_FILE, strict=False)


def open_bus(interface, channel, bitrate):
    """Открывает адаптер в режиме «только слушать», если адаптер это умеет."""
    kwargs = {"interface": interface, "channel": channel, "bitrate": bitrate}
    if interface == "pcan":
        kwargs["state"] = can.BusState.PASSIVE
    elif interface == "slcan":
        kwargs["listen_only"] = True
    else:
        print(f"! Для '{interface}' режим только-чтение не настроен, адаптер может отвечать на шине")
    return can.Bus(**kwargs)


def capture(interface, channel, bitrate=500000, minutes=3.0, stop=None, progress=print, lang="ru"):
    """Пишет данные с шины в logs/*.asc и возвращает путь к логу.

    interface="simulate" — без машины, тестовые данные. stop — threading.Event для досрочной остановки.
    """
    LOGS.mkdir(exist_ok=True)
    stem = f"{dt.datetime.now():%Y-%m-%d_%H-%M-%S}"
    log_path = LOGS / f"{stem}.asc"
    n = 2
    while log_path.exists():
        log_path = LOGS / f"{stem}-{n}.asc"
        n += 1
    if interface == "simulate":
        progress(tr("log.simulate", lang))
        write_simulated(log_path)
        return log_path

    db = load_db()
    bus = open_bus(interface, channel, bitrate)
    state = {}
    count = 0
    progress(tr("log.recording", lang, minutes=f"{minutes:g}", file=log_path.name))
    deadline = time.time() + minutes * 60
    next_print = time.time() + 2
    with can.ASCWriter(log_path) as writer:
        try:
            while time.time() < deadline and not (stop and stop.is_set()):
                msg = bus.recv(timeout=1)
                if msg is None:
                    continue
                writer.on_message_received(msg)
                count += 1
                decode_into(db, msg, state)
                if time.time() >= next_print:
                    next_print = time.time() + 2
                    progress(live_line(state, count, lang))
        except KeyboardInterrupt:
            pass
        finally:
            bus.shutdown()
    progress(tr("log.recorded", lang, count=count))
    if count == 0:
        progress(tr("log.nothing", lang))
    return log_path


def cmd_listen(args):
    print("Остановить: Ctrl+C")
    log_path = capture(args.interface, args.channel, args.bitrate, args.minutes, lang=args.lang)
    print(f"Отчёт: python tesla.py report {log_path.relative_to(ROOT)}")


LIVE_SIGNALS = ["SOCUI292", "BattVoltage132", "SmoothBattCurrent132", "BMSmaxPackTemperature", "v12vBattVoltage261"]


def live_line(state, count, lang="ru"):
    parts = [f"{tr('log.messages', lang)} {count}"]
    for name in LIVE_SIGNALS:
        if name in state:
            parts.append(f"{tr('live.' + name, lang)} {state[name]['last']:.1f}")
    return " | ".join(parts)


def decode_into(db, msg, state):
    """Раскодирует сообщение и обновляет last/min/max по каждому сигналу."""
    try:
        values = db.decode_message(msg.arbitration_id, msg.data, decode_choices=False)
    except (KeyError, ValueError, cantools.database.DecodeError):
        return
    for name, value in values.items():
        if not isinstance(value, (int, float)):
            continue
        s = state.get(name)
        if s is None:
            state[name] = {"last": value, "min": value, "max": value, "msg": msg.arbitration_id}
        else:
            s["last"] = value
            s["min"] = min(s["min"], value)
            s["max"] = max(s["max"], value)


def analyze(log_path, lang="ru", car=None):
    """car: {"model", "year", "variant", "vin"} из карточки клиента — для норм по комплектации."""
    car = car or {}
    db = load_db()
    state = {}
    count = 0
    for msg in can.LogReader(str(log_path)):
        if msg.is_error_frame or msg.is_remote_frame:
            continue
        count += 1
        decode_into(db, msg, state)

    last = lambda name: state.get(name, {}).get("last")
    summary = {"log": str(log_path), "messages": count, "values": {}, "rows": [], "findings": [], "alerts": []}
    summary["raw"] = {name: round(state[name]["last"], 3) for name in KEY_SIGNALS if name in state}
    for name, value in summary["raw"].items():
        summary["values"][tr("sig." + name, lang)] = value

    # Происхождение по VIN; модель и год берём из VIN, если в карточке пусто
    origin = vin_mod.decode(car.get("vin"))
    if origin and origin.get("tesla"):
        summary["origin"] = origin
        car = {**car, "model": car.get("model") or origin["model"], "year": car.get("year") or origin["year"]}

    # Комплектация: выбранная вручную или определённая по ёмкости новой батареи
    bol = last("BattBeginningOfLifeEnergy292")
    variant = specs.BY_ID.get(car.get("variant") or "")
    auto = variant is None
    if auto and car.get("model"):
        variant = specs.guess(car["model"], car.get("year"), bol)
    if variant:
        summary["variant"] = {"id": variant["id"], "name": f'{variant["model"]} {variant["name"]}', "auto": auto}
    chem = variant["chem"] if variant else None

    # Напряжения всех ячеек (Brick0..Brick107, нумеруем с 1 как BMS); нули — ячеек нет в этой батарее
    bricks = {int(n[5:]) + 1: s["last"] for n, s in state.items()
              if n.startswith("Brick") and n[5:].isdigit() and s["last"] > 0.5}
    delta = None
    if bricks:
        lo = min(bricks, key=bricks.get)
        hi = max(bricks, key=bricks.get)
        delta = bricks[hi] - bricks[lo]
        summary["bricks"] = {"count": len(bricks), "min": [lo, round(bricks[lo], 4)],
                             "max": [hi, round(bricks[hi], 4)], "delta": round(delta, 4),
                             "all": {k: round(v, 4) for k, v in sorted(bricks.items())}}
        add_level(summary, delta, CELL_DELTA_WARN, CELL_DELTA_BAD,
                  tr("find.cells", lang, mv=f"{delta * 1000:.0f}", cell=lo), "battery")

    # Деградация: сравниваем с типичной для такого пробега, без пробега — с фиксированными порогами
    km = last("Odometer3B6")
    full = last("BMS_nominalFullPackEnergy")
    ref = bol or (sum(variant["kwh"]) / 2 if variant else None)
    deg = exp = None
    if full and ref:
        deg = (1 - full / ref) * 100
        summary["degradation_pct"] = round(deg, 1)
        if km:
            exp = specs.expected_degradation(km)
            add_level(summary, deg - exp, specs.DEG_WARN_OVER, specs.DEG_BAD_OVER, tr("find.degradation_exp", lang, pct=f"{deg:.1f}",
                                                     exp=f"{exp:.0f}", km=f"{km:,.0f}".replace(",", " ")), "battery")
        else:
            add_level(summary, deg, DEGRADATION_WARN, DEGRADATION_BAD,
                      tr("find.degradation", lang, pct=f"{deg:.1f}", full=f"{full:.1f}", bol=f"{ref:.1f}"), "battery")
    if bol and variant and not (variant["kwh"][0] - 1 <= bol <= variant["kwh"][1] + 1) and not auto:
        summary["findings"].append(["warn", tr("find.bol_mismatch", lang, kwh=f"{bol:.1f}", lo=variant["kwh"][0],
                                               hi=variant["kwh"][1]), "battery"])

    cell_range = specs.CELL_RANGE.get(chem)
    if cell_range and bricks:
        for v in (summary["bricks"]["min"][1], summary["bricks"]["max"][1]):
            if not cell_range[0] <= v <= cell_range[1]:
                summary["findings"].append(["warn", tr("find.cell_range", lang, v=f"{v:.3f}", lo=cell_range[0],
                                                       hi=cell_range[1]), "battery"])

    for name in ("BMSminPackTemperature", "BMSmaxPackTemperature"):
        temp = last(name)
        if temp is not None and not specs.PACK_TEMP_WARN[0] <= temp <= specs.PACK_TEMP_WARN[1]:
            summary["findings"].append(["warn", tr("find.temp", lang, t=f"{temp:.0f}"), "battery"])

    v12 = state.get("v12vBattVoltage261", {}).get("min")
    lv = specs.lv_type(variant, state.get("v12vBattVoltage261", {}).get("max"))
    if v12 is not None and v12 < specs.LV_RANGES[lv]["low"]:
        summary["findings"].append(["warn", tr("find.low12v", lang, v=f"{v12:.2f}"), "front"])

    tire_rec = variant["tire"] if variant else 2.9
    tires_seen = False
    for wheel in ("FL", "FR", "RL", "RR"):
        bar = last(f"TPMS{wheel}pressure31F")
        if bar is None or bar < 0.5:  # 0 — датчик не передаёт
            continue
        tires_seen = True
        add_level(summary, abs(bar - tire_rec), specs.TIRE_WARN, specs.TIRE_BAD,
                  tr("find.tire", lang, wheel=tr("wheel." + wheel, lang), bar=f"{bar:.2f}", rec=tire_rec), "tires",
                  quiet_ok=True)

    alerts_seen = False
    for name, s in sorted(state.items()):
        msg_name = db.get_message_by_frame_id(s["msg"]).name
        if "alert" in msg_name.lower():
            alerts_seen = True
            if s["max"] >= 1 and name not in carmap.IGNORED_ALERTS:
                summary["alerts"].append(name)

    if not summary["findings"] and summary["values"]:
        summary["findings"].append(["ok", tr("find.ok", lang), None])

    summary["rows"] = build_rows(state, summary, variant, lv, deg, exp, km, delta, tire_rec, lang)

    # Зоны схемы, по которым были данные (остальные — серые «нет данных»)
    covered = set()
    if bricks or full:
        covered.add("battery")
    if v12 is not None or alerts_seen:
        covered.add("front")
    if alerts_seen:
        covered |= {"screen", "connectivity", "tires", "rear"}
    if tires_seen:
        covered.add("tires")
    summary["zones"] = carmap.build_zones(summary["findings"], summary["alerts"], covered, lang)
    return summary


def build_rows(state, summary, variant, lv, deg, exp, km, delta, tire_rec, lang):
    """Строки таблицы: [подпись, значение, норма, статус ok/warn/bad/None]."""
    chem = variant["chem"] if variant else None
    rows = []

    def status(value, lo, hi, warn_lo=None, warn_hi=None):
        if value is None:
            return None
        if lo <= value <= hi:
            return "ok"
        if warn_lo is not None and not warn_lo <= value <= warn_hi:
            return "bad"
        return "warn"

    for name in KEY_SIGNALS:
        if name not in state:
            continue
        value = round(state[name]["last"], 3)
        norm, st = "", None
        if name == "SOCUI292" and chem:
            norm = tr("norm.soc_lfp" if chem == "LFP" else "norm.soc_nmc", lang)
        elif name == "BattVoltage132" and chem and "bricks" in summary:
            n = summary["bricks"]["count"]
            lo, hi = (round(n * x) for x in specs.CELL_RANGE[chem])
            norm, st = tr("norm.pack_v", lang, lo=lo, hi=hi), status(value, lo, hi)
        elif name == "SmoothBattCurrent132":
            norm = tr("norm.current", lang)
        elif name == "BMS_nominalFullPackEnergy" and exp is not None and deg is not None:
            ref = value / (1 - deg / 100)
            min_kwh = ref * (1 - (exp + specs.DEG_WARN_OVER) / 100)
            norm = tr("norm.capacity_now", lang, kwh=f"{min_kwh:.1f}", km=f"{km:,.0f}".replace(",", " "))
            st = "ok" if value >= min_kwh else "warn"
        elif name == "BattBeginningOfLifeEnergy292" and variant:
            lo, hi = variant["kwh"]
            norm, st = tr("norm.capacity_new", lang, lo=lo, hi=hi), status(value, lo - 1, hi + 1)
        elif name in ("BMSminPackTemperature", "BMSmaxPackTemperature"):
            lo, hi = specs.PACK_TEMP_OK
            norm, st = tr("norm.temp", lang, lo=lo, hi=hi), status(value, lo, hi, *specs.PACK_TEMP_WARN)
        elif name in ("BattBrickVoltageMin332", "BattBrickVoltageMax332") and chem:
            lo, hi = specs.CELL_RANGE[chem]
            norm, st = tr("norm.cell_v", lang, lo=lo, hi=hi, chem=chem), status(value, lo, hi)
        elif name == "v12vBattVoltage261":
            r = specs.LV_RANGES[lv]
            norm = tr("norm.v12_" + lv, lang, r0=r["rest"][0], r1=r["rest"][1], a0=r["awake"][0], a1=r["awake"][1])
            st = "ok" if state[name]["min"] >= r["low"] else "warn"
        elif name.startswith("TPMS"):
            if value < 0.5:
                continue
            norm = tr("norm.tire", lang, bar=tire_rec)
            dev = abs(value - tire_rec)
            st = "ok" if dev < specs.TIRE_WARN else "warn" if dev < specs.TIRE_BAD else "bad"
        rows.append([tr("sig." + name, lang), value, norm, st])

    if deg is not None:
        if exp is not None:
            norm = tr("norm.degradation", lang, pct=f"{exp:.0f}", km=f"{km:,.0f}".replace(",", " "))
            over = deg - exp
            st = "ok" if over < specs.DEG_WARN_OVER else "warn" if over < specs.DEG_BAD_OVER else "bad"
        else:
            norm, st = "", None
        rows.append([tr("row.degradation", lang), round(deg, 1), norm, st])
    if delta is not None:
        mv = delta * 1000
        rows.append([tr("row.imbalance", lang), round(mv), tr("norm.imbalance", lang),
                     "ok" if mv < 30 else "warn" if mv < 80 else "bad"])
    return rows


def add_level(summary, value, warn, bad, text, zone, quiet_ok=False):
    level = "bad" if value >= bad else "warn" if value >= warn else "ok"
    if level == "ok" and quiet_ok:
        return
    summary["findings"].append([level, text, zone])


def make_report(log_path, car="", title=None, lang="ru", car_info=None):
    """Строит HTML-отчёт и JSON рядом с ним в reports/. Возвращает (путь к html, summary).

    car — строка для шапки отчёта, car_info — {"model", "year", "variant", "vin"} для норм.
    """
    log_path = Path(log_path)
    summary = analyze(log_path, lang, car_info)
    summary["car"] = car
    summary["title"] = title or tr("rep.title", lang)
    summary["lang"] = lang
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / (log_path.stem + ".html")
    out.write_text(render_html(summary), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return out, summary


def cmd_report(args):
    car_info = {"model": args.model, "year": args.year, "variant": args.variant, "vin": args.vin}
    out, summary = make_report(args.log, args.car, lang=args.lang, car_info=car_info)
    print(json.dumps({k: v for k, v in summary.items() if k != "bricks"}, ensure_ascii=False, indent=2))
    print(f"\nОтчёт для клиента: {out}\nДанные для анализа: {out.with_suffix('.json')}")


def render_html(s):
    e = html.escape
    colors = {"ok": "#1a7f37", "warn": "#b35900", "bad": "#c62828"}
    icons = {"ok": "✔", "warn": "⚠", "bad": "✖"}
    st_color = {"ok": colors["ok"], "warn": colors["warn"], "bad": colors["bad"], None: "inherit"}
    rows = "".join(f'<tr><td>{e(label)}</td><td style="color:{st_color[st]}"><b>{e(str(value))}</b></td>'
                   f'<td class="norm">{e(norm)}</td></tr>' for label, value, norm, st in s.get("rows", []))
    findings = "".join(f'<li style="color:{colors[l]}">{icons[l]} {e(t)}</li>' for l, t, _ in s["findings"])
    lang = s.get("lang", "ru")
    alerts = "".join(f"<li>{e(alert(a, lang))}</li>" for a in s["alerts"]) or f"<li>{tr('rep.none', lang)}</li>"
    v, mv = tr("rep.v", lang), tr("rep.mv", lang)
    info = []
    if s.get("variant"):
        auto = f' <small>({tr("rep.variant_auto", lang)})</small>' if s["variant"]["auto"] else ""
        info.append(e(tr("rep.variant", lang, name=s["variant"]["name"])) + auto)
    else:
        info.append(e(tr("rep.variant_unknown", lang)))
    o = s.get("origin")
    if o:
        if o.get("plant"):
            info.append(e(tr("vin.origin", lang, plant=o["plant"], country=tr("vin.country." + o["country"], lang))))
        info.append(e(tr("vin.market." + o["market"], lang)))
        if o.get("check_ok") is False:
            info.append(f'<span style="color:{colors["warn"]}">{e(tr("vin.check_bad", lang))}</span>')
    info = "<br>".join(info)
    bricks = ""
    if "bricks" in s:
        b = s["bricks"]
        vmin, vmax = b["min"][1], b["max"][1]
        span = max(vmax - vmin, 0.001)
        bars = "".join(
            f'<div title="#{n}: {x:.4f} {v}" style="height:{20 + 80 * (x - vmin) / span:.0f}%;'
            f'background:{"#c62828" if n == b["min"][0] else "#4a7bd0"}"></div>'
            for n, x in ((int(k), x) for k, x in b["all"].items()))
        bricks = (f'<h2>{tr("rep.cells", lang, count=b["count"])}</h2>'
                  f'<p>{tr("rep.min", lang)} {vmin:.4f} {v} (#{b["min"][0]}) · {tr("rep.max", lang)} {vmax:.4f} {v} (#{b["max"][0]}) · '
                  f'{tr("rep.diff", lang)} {b["delta"] * 1000:.0f} {mv}</p><div class="bars">{bars}</div>')
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(s["title"])}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#222}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:6px 8px;border-bottom:1px solid #ddd;text-align:left}}
th{{font-size:13px;color:#777;font-weight:600}}.norm{{color:#555;font-size:14px}}.info{{background:#f4f6f9;border-radius:8px;padding:10px 12px}}
.bars{{display:flex;align-items:flex-end;gap:1px;height:120px;background:#f4f4f4;padding:4px}}
.bars div{{flex:1;min-width:2px}}li{{margin:4px 0}}small{{color:#777}}{carmap.CSS}</style></head><body>
<h1>{e(s["title"])}</h1><p>{e(s.get("car") or "")}<br><small>{dt.date.today():%d.%m.%Y} · {s["messages"]} {tr("rep.can_messages", lang)}</small></p>
<p class="info">{info}</p>
<h2>{tr("rep.summary", lang)}</h2><ul>{findings}</ul>{carmap.render(s["zones"], lang) if "zones" in s else ""}<h2>{tr("rep.values", lang)}</h2><table><tr><th>{tr("rep.param", lang)}</th><th>{tr("rep.value", lang)}</th><th>{tr("rep.norm", lang)}</th></tr>{rows}</table>
<p><small>{tr("rep.norms_note", lang)}</small></p>{bricks}
<h2>{tr("rep.alerts", lang)}</h2><ul>{alerts}</ul>
<p><small>{tr("rep.footer", lang)}</small></p>
</body></html>"""


def cmd_simulate(args):
    LOGS.mkdir(exist_ok=True)
    log_path = LOGS / "simulated.asc"
    write_simulated(log_path)
    print(f"Создан {log_path}. Теперь: python tesla.py report {log_path.relative_to(ROOT)}")


def write_simulated(log_path):
    """Пишет лог, похожий на настоящую Model 3, чтобы проверить отчёт без машины."""
    db = load_db()
    rnd = random.Random(1)
    weak = rnd.randrange(96)
    values = {
        "Odometer3B6": 84213.5, "SOCUI292": 72.4, "SOCave292": 73.0, "SOCmin292": 72.1, "SOCmax292": 73.9,
        "BattBeginningOfLifeEnergy292": 77.8, "BattVoltage132": 382.6, "SmoothBattCurrent132": -1.8,
        "BMS_nominalFullPackEnergy": 68.9, "BMS_nominalEnergyRemaining": 49.9,
        "BMSminPackTemperature": 21.5, "BMSmaxPackTemperature": 24.0,
        "BattBrickVoltageMin332": 3.952, "BattBrickVoltageMinNum332": weak + 1,
        "BattBrickVoltageMax332": 3.998, "BattBrickVoltageMaxNum332": 12,
        "v12vBattVoltage261": 12.05, "TotalChargeKWh3D2": 23140.0, "TotalDischargeKWh3D2": 21980.0,
        "UI_a058_GPSAntennaDisconnected": 1, "UI_a010_MapsMissing": 1,
        "TPMSFLpressure31F": 2.9, "TPMSFRpressure31F": 2.875, "TPMSRLpressure31F": 2.45, "TPMSRRpressure31F": 2.9,
    }
    for i in range(96):
        values[f"Brick{i}"] = 3.952 if i == weak else 3.975 + rnd.uniform(-0.012, 0.012)

    with can.ASCWriter(log_path) as writer:
        t = 0.0
        for _ in range(20):
            for m in db.messages:
                selectors = [None]
                mux = next((s for s in m.signals if s.is_multiplexer), None)
                if mux:
                    selectors = sorted({i for s in m.signals for i in (s.multiplexer_ids or [])})
                for sel in selectors:
                    data = {}
                    for s in m.signals:
                        if s.is_multiplexer:
                            data[s.name] = sel
                        elif s.multiplexer_ids is None or sel in s.multiplexer_ids:
                            data[s.name] = values.get(s.name, min(max(0, s.minimum or 0), s.maximum or 0))
                    try:
                        payload = m.encode(data, strict=False)
                    except Exception:
                        continue
                    t += 0.001
                    writer.on_message_received(can.Message(timestamp=t, arbitration_id=m.frame_id,
                                                           data=payload, is_extended_id=False))


def main():
    p = argparse.ArgumentParser(description="Диагностика Tesla по CAN (только чтение)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("listen", help="записать данные с машины")
    pl.add_argument("--interface", default="pcan", help="pcan | slcan | gs_usb | kvaser ...")
    pl.add_argument("--channel", default="PCAN_USBBUS1", help="PCAN_USBBUS1 или COM3 и т.п.")
    pl.add_argument("--bitrate", type=int, default=500000)
    pl.add_argument("--minutes", type=float, default=3)
    pl.add_argument("--lang", default="ru", choices=["ru", "en", "ka"])
    pl.set_defaults(func=cmd_listen)

    pr = sub.add_parser("report", help="сделать отчёт по записанному логу")
    pr.add_argument("log")
    pr.add_argument("--car", default="", help="модель, год, VIN, имя клиента")
    pr.add_argument("--lang", default="ru", choices=["ru", "en", "ka"])
    pr.add_argument("--model", default="", help="Model 3 / Model Y / Model S / Model X")
    pr.add_argument("--year", default="")
    pr.add_argument("--variant", default="", help="id из specs.py; пусто — определить автоматически")
    pr.add_argument("--vin", default="")
    pr.set_defaults(func=cmd_report)

    ps = sub.add_parser("simulate", help="создать тестовый лог без машины")
    ps.set_defaults(func=cmd_simulate)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
