"""База характеристик Tesla по моделям и годам + нормы для отчёта.

Цифры — ориентиры из открытых источников (Tesla их официально не публикует):
ёмкость батарей — fiches-auto.fr, shop4tesla, electrive; литиевый 12V (~15.5–16 В) вместо свинцового —
примерно с конца 2021 у Model 3/Y и у обновлённых S/X 2021+. Точный тип 12V виден на экране машины:
Управление → ПО → Дополнительная информация.

Поля варианта:
    years   — (с, по) включительно
    kwh     — ёмкость новой батареи, кВт·ч (от, до)
    chem    — NCA / NMC / LFP
    lv      — lead (свинцовый 12V) / li (литиевый ~16V) / mixed (в этих годах встречаются оба)
    tire    — рекомендуемое давление на холодную, bar (точное — на наклейке в проёме водительской двери)
"""
import datetime as dt

CURRENT_YEAR = dt.date.today().year

VARIANTS = [
    # --- Model 3 ---
    {"id": "m3_sr_2017", "model": "Model 3", "years": (2017, 2020), "name": "Standard Range / SR+ · NCA",
     "kwh": (50, 55), "chem": "NCA", "lv": "lead", "tire": 2.9},
    {"id": "m3_lr_2017", "model": "Model 3", "years": (2017, 2020), "name": "Long Range / Performance · NCA",
     "kwh": (75, 78), "chem": "NCA", "lv": "lead", "tire": 2.9},
    {"id": "m3_sr_lfp_2021", "model": "Model 3", "years": (2021, 2023), "name": "Standard Range+ / RWD · LFP",
     "kwh": (55, 62), "chem": "LFP", "lv": "mixed", "tire": 2.9},
    {"id": "m3_lr_2021", "model": "Model 3", "years": (2021, 2023), "name": "Long Range / Performance · NCA/NMC",
     "kwh": (78, 82), "chem": "NMC", "lv": "mixed", "tire": 2.9},
    {"id": "m3_rwd_2024", "model": "Model 3", "years": (2024, CURRENT_YEAR), "name": "RWD (Highland) · LFP",
     "kwh": (60, 62.5), "chem": "LFP", "lv": "li", "tire": 2.9},
    {"id": "m3_lr_2024", "model": "Model 3", "years": (2024, CURRENT_YEAR), "name": "Long Range / Performance (Highland) · NMC",
     "kwh": (79, 84), "chem": "NMC", "lv": "li", "tire": 2.9},
    # --- Model Y ---
    {"id": "my_lr_2020", "model": "Model Y", "years": (2020, 2021), "name": "Long Range / Performance · NCA",
     "kwh": (75, 78), "chem": "NCA", "lv": "mixed", "tire": 2.9},
    {"id": "my_sr_lfp_2021", "model": "Model Y", "years": (2021, 2024), "name": "Standard / RWD · LFP",
     "kwh": (60, 62), "chem": "LFP", "lv": "li", "tire": 2.9},
    {"id": "my_lr_2022", "model": "Model Y", "years": (2022, 2024), "name": "Long Range / Performance · NCA/NMC",
     "kwh": (75, 82), "chem": "NMC", "lv": "li", "tire": 2.9},
    {"id": "my_rwd_2025", "model": "Model Y", "years": (2025, CURRENT_YEAR), "name": "RWD (Juniper) · LFP",
     "kwh": (60, 62.5), "chem": "LFP", "lv": "li", "tire": 2.9},
    {"id": "my_lr_2025", "model": "Model Y", "years": (2025, CURRENT_YEAR), "name": "Long Range / Performance (Juniper) · NMC",
     "kwh": (75, 84), "chem": "NMC", "lv": "li", "tire": 2.9},
    # --- Model S / X (программа пока читает данные только Model 3/Y — нормы для справки) ---
    {"id": "ms_75_2016", "model": "Model S", "years": (2016, 2020), "name": "75 / 75D · NCA",
     "kwh": (72, 75), "chem": "NCA", "lv": "lead", "tire": 2.9},
    {"id": "ms_100_2016", "model": "Model S", "years": (2016, 2020), "name": "90D / 100D / Long Range · NCA",
     "kwh": (81, 100), "chem": "NCA", "lv": "lead", "tire": 2.9},
    {"id": "ms_2021", "model": "Model S", "years": (2021, CURRENT_YEAR), "name": "Long Range / Plaid · NCA",
     "kwh": (95, 100), "chem": "NCA", "lv": "li", "tire": 2.9},
    {"id": "mx_75_2016", "model": "Model X", "years": (2016, 2020), "name": "75D · NCA",
     "kwh": (72, 75), "chem": "NCA", "lv": "lead", "tire": 2.9},
    {"id": "mx_100_2016", "model": "Model X", "years": (2016, 2020), "name": "90D / 100D / Long Range · NCA",
     "kwh": (81, 100), "chem": "NCA", "lv": "lead", "tire": 2.9},
    {"id": "mx_2021", "model": "Model X", "years": (2021, CURRENT_YEAR), "name": "Long Range / Plaid · NCA",
     "kwh": (95, 100), "chem": "NCA", "lv": "li", "tire": 2.9},
]
BY_ID = {v["id"]: v for v in VARIANTS}

# Рабочий диапазон напряжения ячейки по химии, В
CELL_RANGE = {"NCA": (3.0, 4.2), "NMC": (3.0, 4.2), "LFP": (2.5, 3.65)}

# Типичная потеря ёмкости от пробега (км -> %), по данным владельцев и отчётам Tesla. Ориентир.
DEGRADATION_CURVE = [(0, 0), (30_000, 4), (80_000, 7), (160_000, 10), (320_000, 13), (500_000, 16)]

DEG_WARN_OVER, DEG_BAD_OVER = 3, 8  # насколько % деградация может превышать типичную
PACK_TEMP_OK = (15, 35)  # °C, обычная температура батареи на стоянке
PACK_TEMP_WARN = (0, 45)
LV_RANGES = {"lead": {"rest": (12.4, 12.8), "awake": (13.5, 14.8), "low": 12.2},
             "li": {"rest": (15.0, 16.0), "awake": (15.0, 16.0), "low": 14.0}}
TIRE_WARN, TIRE_BAD = 0.3, 0.5  # bar отклонения от рекомендованного


def for_car(model, year):
    """Варианты для модели и года (для выпадающего списка)."""
    try:
        year = int(year)
    except (TypeError, ValueError):
        return [v for v in VARIANTS if v["model"] == model]
    return [v for v in VARIANTS if v["model"] == model and v["years"][0] <= year <= v["years"][1]]


def guess(model, year, bol_kwh):
    """Определяет вариант по модели, году и ёмкости новой батареи, которую сообщает машина."""
    options = for_car(model, year) or [v for v in VARIANTS if v["model"] == model]
    if not options:
        return None
    if bol_kwh:
        return min(options, key=lambda v: 0 if v["kwh"][0] <= bol_kwh <= v["kwh"][1]
                   else min(abs(bol_kwh - v["kwh"][0]), abs(bol_kwh - v["kwh"][1])))
    return options[0] if len(options) == 1 else None


def expected_degradation(km):
    pts = DEGRADATION_CURVE
    if km >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= km <= x1:
            return y0 + (y1 - y0) * (km - x0) / (x1 - x0)
    return 0


def lv_type(variant, v12_max):
    """Тип 12V: по напряжению, если машина проснулась (литиевый держит >15 В), иначе по варианту."""
    if v12_max is not None and v12_max >= 15.0:
        return "li"
    if variant and variant["lv"] in ("lead", "li"):
        return variant["lv"]
    return "lead"
