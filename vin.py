"""Расшифровка VIN Tesla: модель, год, завод, страна, вероятный рынок, проверка контрольной цифры."""

# Позиции 1–3: производитель (WMI)
WMI = {"5YJ": "us", "7SA": "us", "7G2": "us", "LRW": "cn", "XP7": "de"}
# Позиция 4: модель
MODELS = {"S": "Model S", "3": "Model 3", "X": "Model X", "Y": "Model Y", "C": "Cybertruck"}
# Позиция 10: модельный год
YEARS = {"F": 2015, "G": 2016, "H": 2017, "J": 2018, "K": 2019, "L": 2020, "M": 2021, "N": 2022,
         "P": 2023, "R": 2024, "S": 2025, "T": 2026, "V": 2027, "W": 2028}
# Позиция 11: завод
PLANTS = {"F": ("Fremont", "us"), "A": ("Austin", "us"), "C": ("Shanghai", "cn"), "B": ("Berlin", "de")}

_TRANSLIT = dict(zip("ABCDEFGHJKLMNPRSTUVWXYZ", [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 5, 7, 9, 2, 3, 4, 5, 6, 7, 8, 9]))
_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def check_digit_ok(vin):
    total = 0
    for ch, w in zip(vin, _WEIGHTS):
        total += (int(ch) if ch.isdigit() else _TRANSLIT.get(ch, 0)) * w
    expected = total % 11
    return vin[8] == ("X" if expected == 10 else str(expected))


def decode(vin):
    """Возвращает словарь или None, если это не похоже на VIN Tesla."""
    vin = (vin or "").strip().upper()
    if len(vin) != 17 or any(c in "IOQ" for c in vin):
        return None
    wmi = vin[:3]
    if wmi not in WMI:
        return {"vin": vin, "tesla": False}
    plant, country = PLANTS.get(vin[10], (None, WMI[wmi]))
    # Машины с североамериканским WMI делаются для рынка США/Канады (нужна локализация).
    # Шанхай отгружает и в Китай, и в Азию/Европу — регион нужно смотреть на экране.
    market = {"us": "na", "de": "eu", "cn": "cn_asia_eu"}[WMI[wmi]]
    return {
        "vin": vin, "tesla": True,
        "model": MODELS.get(vin[3]),
        "year": YEARS.get(vin[9]),
        "plant": plant, "country": country, "market": market,
        # Контрольная цифра обязательна в Северной Америке и Китае; у европейских VIN может не совпадать
        "check_ok": check_digit_ok(vin) if WMI[wmi] in ("us", "cn") else None,
    }
