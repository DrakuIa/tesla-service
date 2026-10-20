"""Схема машины (вид сверху) с зонами, окрашенными по найденным проблемам."""
import html

from i18n import alert, t as tr

ZONES = ["front", "cameras", "screen", "connectivity", "battery", "tires", "rear", "charge"]
LEVELS = ["nodata", "ok", "warn", "bad"]

# Предупреждение машины -> зона на схеме
ALERT_ZONES = {
    "UI_a007_SoftPackConfigMismatch": "battery",
    "UI_a008_TouchScreenError": "screen",
    "UI_a009_SquashfsError": "screen",
    "UI_a010_MapsMissing": "screen",
    "UI_a011_IncorrectMap": "screen",
    "UI_a043_InvalidMapDataOverride": "screen",
    "UI_a052_KernelPanicReported": "screen",
    "UI_a053_QtCarExitError": "screen",
    "UI_a013_TPMSHardWarning": "tires",
    "UI_a014_TPMSSoftWarning": "tires",
    "UI_a015_TPMSOverPressureWarning": "tires",
    "UI_a016_TPMSTemperatureWarning": "tires",
    "UI_a017_TPMSSystemFault": "tires",
    "UI_a019_ParkBrakeFault": "rear",
    "UI_a046_BackupCameraStreamError": "rear",
    "UI_a050_BackupCameraIPUTimeout": "rear",
    "UI_a051_BackupCameraFrameTimeout": "rear",
    "UI_a031_BrakeFluidLow": "front",
    "UI_a034_WakeupProblem": "front",
    "UI_a027_AutoSteerMIA": "cameras",
    "UI_a023_CellInternetCheckFailed": "connectivity",
    "UI_a024_WifiInternetCheckFailed": "connectivity",
    "UI_a025_WifiOnlineCheckFailed": "connectivity",
    "UI_a026_ModemResetLoopDetected": "connectivity",
    "UI_a029_ModemMIA": "connectivity",
    "UI_a030_ModemVMCrash": "connectivity",
    "UI_a032_CellModemRecoveryResets": "connectivity",
    "UI_a045_ECallNeedsService": "connectivity",
    "UI_a047_CellRoamingDisallowed": "connectivity",
    "UI_a057_CellAntennaDisconnected": "connectivity",
    "UI_a058_GPSAntennaDisconnected": "connectivity",
    "UI_a061_SIMTestFailed": "connectivity",
    "UI_a063_CellularTestFailed": "connectivity",
    "UI_a064_ModemFirmwareTestFailed": "connectivity",
}
BAD_ALERTS = {"UI_a031_BrakeFluidLow", "UI_a019_ParkBrakeFault", "UI_a013_TPMSHardWarning", "UI_a007_SoftPackConfigMismatch"}
# Двери/багажник открыты и т.п. — не неисправности, на схему не выносим
IGNORED_ALERTS = {"UI_a001_DriverDoorOpen", "UI_a002_DoorOpen", "UI_a003_TrunkOpen", "UI_a004_FrunkOpen",
                  "UI_a005_HeadlightsOnDoorOpen", "UI_a021_RearSeatbeltUnbuckled", "UI_a040_HomelinkTransmit"}


def build_zones(findings, alerts, covered, lang):
    """findings: [level, text, zone]; covered: зоны, по которым были данные."""
    zones = {z: {"level": "ok" if z in covered else "nodata", "items": []} for z in ZONES}

    def add(zone, level, text):
        z = zones[zone]
        z["items"].append([level, text])
        if LEVELS.index(level) > LEVELS.index(z["level"]):
            z["level"] = level

    for level, text, zone in findings:
        if zone in zones and level != "ok":
            add(zone, level, text)
    for code in alerts:
        if code in ALERT_ZONES:
            add(ALERT_ZONES[code], "bad" if code in BAD_ALERTS else "warn", alert(code, lang))
    return zones


FILL = {"nodata": "#eef0f3", "ok": "#d7f5df", "warn": "#fde9b8", "bad": "#fbd0d0"}
STROKE = {"nodata": "#9ca3af", "ok": "#1a7f37", "warn": "#b35900", "bad": "#c62828"}
ICON = {"nodata": "–", "ok": "✔", "warn": "⚠", "bad": "✖"}

# Фигуры зон на схеме 300×560 (перед машины сверху) и точка для номера
SHAPES = {
    "front": (['<rect x="78" y="52" width="144" height="88" rx="38"/>'], (150, 96)),
    "cameras": (['<path d="M84 160 H216 L204 206 H96 Z"/>'], (150, 183)),
    "screen": (['<rect x="122" y="216" width="56" height="26" rx="5"/>'], (150, 229)),
    "battery": (['<rect x="86" y="256" width="128" height="170" rx="10" stroke-dasharray="6 4"/>'], (150, 341)),
    "connectivity": (['<rect x="106" y="436" width="88" height="24" rx="8"/>'], (150, 448)),
    "rear": (['<rect x="78" y="470" width="144" height="50" rx="26"/>'], (150, 495)),
    "charge": (['<rect x="40" y="446" width="14" height="30" rx="4"/>'], (47, 461)),
    "tires": ([f'<rect x="{x}" y="{y}" width="24" height="66" rx="7"/>'
               for x, y in ((30, 98), (246, 98), (30, 380), (246, 380))], (42, 131)),
}


def render(zones, lang):
    """HTML-блок: SVG-схема + список зон."""
    e = html.escape
    shapes, legend = [], []
    for i, zone in enumerate(ZONES, 1):
        z = zones[zone]
        level = z["level"]
        name = tr("zone." + zone, lang)
        parts, (cx, cy) = SHAPES[zone]
        title = f"<title>{i}. {e(name)} — {tr('level.' + level, lang)}</title>"
        shapes.append(f'<g class="zone" data-zone="{zone}" fill="{FILL[level]}" stroke="{STROKE[level]}" stroke-width="2">'
                      f'{title}{"".join(parts)}'
                      f'<circle cx="{cx}" cy="{cy}" r="11" fill="{STROKE[level]}" stroke="#fff"/>'
                      f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" fill="#fff" stroke="none" '
                      f'font-size="12" font-weight="700">{i}</text></g>')
        items = "".join(f'<div style="color:{STROKE[l]}">{ICON[l]} {e(text)}</div>' for l, text in z["items"])
        legend.append(f'<li data-zone="{zone}" class="lv-{level}"><b style="background:{STROKE[level]}">{i}</b>'
                      f'<span><strong>{e(name)}</strong> <em style="color:{STROKE[level]}">{tr("level." + level, lang)}</em>'
                      f'{items}</span></li>')
    svg = f'''<svg viewBox="0 0 300 560" class="car" role="img" aria-label="{e(tr('rep.carmap', lang))}">
<text x="150" y="20" text-anchor="middle" font-size="12" fill="#6b7280" letter-spacing="2">▲ {e(tr('rep.car_front', lang))}</text>
<path d="M150 34 C 82 34 56 60 54 130 L 54 450 C 56 515 90 532 150 532 C 210 532 244 515 246 450 L 246 130 C 244 60 218 34 150 34 Z"
 fill="#fafafa" stroke="#374151" stroke-width="2.5"/>
<path d="M66 250 L 54 250 M 234 250 L 246 250" stroke="#374151" stroke-width="2"/>
{"".join(shapes)}
<text x="150" y="552" text-anchor="middle" font-size="12" fill="#6b7280" letter-spacing="2">{e(tr('rep.car_rear', lang))} ▼</text>
</svg>'''
    return f'''<h2>{e(tr('rep.carmap', lang))}</h2>
<div class="carmap">{svg}<ol class="zones">{"".join(legend)}</ol></div>
<script>
document.querySelectorAll(".carmap [data-zone]").forEach(el => el.addEventListener("click", () => {{
  const z = el.dataset.zone;
  document.querySelectorAll(".carmap [data-zone]").forEach(x => x.classList.toggle("active", x.dataset.zone === z));
  const li = document.querySelector('.zones [data-zone="' + z + '"]');
  if (el.tagName !== "LI") li.scrollIntoView({{block: "nearest", behavior: "smooth"}});
}}));
</script>'''


CSS = """
.carmap{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}
.car{width:260px;max-width:100%;flex:none}
.zone{cursor:pointer}.zone:hover,.zone.active{filter:brightness(.93)}.zone.active rect,.zone.active path{stroke-width:4}
.zones{list-style:none;padding:0;margin:0;flex:1;min-width:240px}
.zones li{display:flex;gap:10px;padding:8px;border-radius:8px;cursor:pointer;margin:0}
.zones li.active{background:#f1f5f9}
.zones li b{flex:none;width:22px;height:22px;border-radius:50%;color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center}
.zones em{font-style:normal;font-size:13px;margin-left:4px}
.zones li div{font-size:14px;margin-top:2px}
.zones li.lv-nodata{opacity:.65}
"""
