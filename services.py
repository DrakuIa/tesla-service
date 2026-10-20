"""Каталог услуг для программы app.py. Тексты на трёх языках: L(русский, английский, грузинский).

mode:
    auto    — программа сама снимает данные с машины и делает отчёт
    guided  — пошаговый чек-лист; данные снимаются «до» и «после», в акте видно, какие ошибки ушли
    partner — работа отдаётся партнёру, программа только записывает заказ
"""
from i18n import L, norm

TOOLBOX_STEPS = [
    L("Снять данные «до» — зафиксировать ошибки до работы",
      "Read data “before” — record the errors before the work",
      "მონაცემების აღება „მანამდე“ — დააფიქსირეთ შეცდომები სამუშაომდე"),
    L("Открыть Toolbox, подключиться к машине",
      "Open Toolbox and connect to the car",
      "გახსენით Toolbox და დაუკავშირდით მანქანას"),
    L("Найти процедуру «{proc}» и выполнить её по инструкции Toolbox",
      "Find the “{proc}” procedure and run it following Toolbox instructions",
      "იპოვეთ პროცედურა „{proc}“ და შეასრულეთ Toolbox-ის ინსტრუქციით"),
    L("Сохранить скриншот результата Toolbox",
      "Save a screenshot of the Toolbox result",
      "შეინახეთ Toolbox-ის შედეგის სქრინშოტი"),
    L("Снять данные «после» — проверить, что ошибки ушли",
      "Read data “after” — check that the errors are gone",
      "მონაცემების აღება „შემდეგ“ — შეამოწმეთ, რომ შეცდომები გაქრა"),
]

GROUPS = ["diag", "setup", "toolbox", "partner"]

SERVICES = [
    # --- Диагностика: полностью автоматически ---
    {"id": "precheck", "group": "diag", "mode": "auto", "minutes": 3,
     "name": L("Проверка перед покупкой", "Pre-purchase inspection", "შემოწმება ყიდვამდე"),
     "prep": L("Машина проснулась (открыть дверь, включить экран). Не ехать во время записи.",
               "Car is awake (open a door, turn on the screen). Do not drive while recording.",
               "მანქანა გაღვიძებულია (გააღეთ კარი, ჩართეთ ეკრანი). ჩაწერისას არ იმოძრაოთ.")},
    {"id": "battery", "group": "diag", "mode": "auto", "minutes": 2,
     "name": L("Отчёт о батарее для продажи", "Battery report for sale", "ბატარეის ანგარიში გაყიდვისთვის"),
     "prep": L("Машина проснулась, не на зарядке.", "Car is awake and not charging.",
               "მანქანა გაღვიძებულია და არ იტენება.")},
    {"id": "errors", "group": "diag", "mode": "auto", "minutes": 1,
     "name": L("Чтение и расшифровка ошибок", "Read and explain errors", "შეცდომების წაკითხვა და განმარტება"),
     "prep": L("Машина проснулась. Сфотографируйте ошибки на экране машины — пригодится для сравнения.",
               "Car is awake. Take a photo of the errors on the car screen — useful for comparison.",
               "მანქანა გაღვიძებულია. გადაუღეთ ფოტო ეკრანზე არსებულ შეცდომებს — შედარებისთვის გამოგადგებათ.")},
    {"id": "12v", "group": "diag", "mode": "auto", "minutes": 2,
     "name": L("Проверка 12V аккумулятора", "12V battery check", "12V აკუმულატორის შემოწმება"),
     "prep": L("Машина проснулась. Включите климат, чтобы дать нагрузку на 12V.",
               "Car is awake. Turn on climate control to load the 12V system.",
               "მანქანა გაღვიძებულია. ჩართეთ კლიმატი, რომ 12V სისტემას დატვირთვა მიეცეს.")},
    {"id": "charging", "group": "diag", "mode": "auto", "minutes": 3,
     "name": L("Диагностика зарядки", "Charging diagnostics", "დატენვის დიაგნოსტიკა"),
     "prep": L("Подключите машину к зарядке и дождитесь, пока зарядка начнётся, потом запускайте.",
               "Plug the car in, wait until charging starts, then start.",
               "შეაერთეთ მანქანა დამტენთან, დაელოდეთ დატენვის დაწყებას და შემდეგ დაიწყეთ.")},
    {"id": "yearly", "group": "diag", "mode": "auto", "minutes": 3,
     "name": L("Плановая проверка", "Scheduled check-up", "გეგმიური შემოწმება"),
     "prep": L("Машина проснулась. Заодно проверьте давление в шинах и уровень жидкостей на экране машины.",
               "Car is awake. Also check tire pressure and fluid levels on the car screen.",
               "მანქანა გაღვიძებულია. ასევე შეამოწმეთ საბურავების წნევა და სითხეების დონე მანქანის ეკრანზე.")},

    # --- Настройка: по шагам на экране машины ---
    {"id": "language", "group": "setup", "mode": "guided", "capture": False,
     "name": L("Язык и единицы измерения", "Language and units", "ენა და საზომი ერთეულები"),
     "steps": [
         L("На экране машины: Управление → Дисплей → Язык — выбрать язык",
           "On the car screen: Controls → Display → Language — choose the language",
           "მანქანის ეკრანზე: Controls → Display → Language — აირჩიეთ ენა"),
         L("Там же: единицы расстояния (км), температуры (°C), давления шин (bar)",
           "Same place: distance (km), temperature (°C), tire pressure (bar) units",
           "იქვე: მანძილის (კმ), ტემპერატურის (°C) და საბურავის წნევის (bar) ერთეულები"),
         L("Показать клиенту результат", "Show the result to the client", "აჩვენეთ კლიენტს შედეგი")]},
    {"id": "connectivity", "group": "setup", "mode": "guided", "capture": True,
     "name": L("Связь: SIM, LTE, приложение", "Connectivity: SIM, LTE, app", "კავშირი: SIM, LTE, აპლიკაცია"),
     "steps": [
         L("Снять данные «до» — программа покажет ошибки модема/SIM/антенн",
           "Read data “before” — the program shows modem/SIM/antenna errors",
           "მონაცემების აღება „მანამდე“ — პროგრამა აჩვენებს მოდემის/SIM-ის/ანტენების შეცდომებს"),
         L("Проверить, что в машине стоит SIM местного оператора с интернетом и разрешённым роумингом",
           "Check the car has a local SIM with internet and roaming allowed",
           "შეამოწმეთ, რომ მანქანაში დგას ადგილობრივი ოპერატორის SIM ინტერნეტით და დაშვებული როუმინგით"),
         L("Подключить машину к Wi-Fi и проверить, появился ли интернет",
           "Connect the car to Wi-Fi and check internet works",
           "დააკავშირეთ მანქანა Wi-Fi-ს და შეამოწმეთ, გაჩნდა თუ არა ინტერნეტი"),
         L("Привязать телефон клиента в приложении Tesla как ключ",
           "Pair the client's phone as a key in the Tesla app",
           "მიაბით კლიენტის ტელეფონი Tesla-ს აპლიკაციაში გასაღებად"),
         L("Снять данные «после» — ошибки связи должны уйти",
           "Read data “after” — connectivity errors should be gone",
           "მონაცემების აღება „შემდეგ“ — კავშირის შეცდომები უნდა გაქრეს")]},
    {"id": "firmware", "group": "setup", "mode": "guided", "capture": False,
     "name": L("Обновление прошивки", "Software update", "პროგრამის განახლება"),
     "steps": [
         L("Подключить машину к Wi-Fi (хотспот телефона подойдёт)",
           "Connect the car to Wi-Fi (a phone hotspot works)",
           "დააკავშირეთ მანქანა Wi-Fi-ს (ტელეფონის ჰოტსპოტიც გამოდგება)"),
         L("Управление → ПО — проверить наличие обновления",
           "Controls → Software — check for an update",
           "Controls → Software — შეამოწმეთ, არის თუ არა განახლება"),
         L("Зарядить машину выше 20%, 12V должен быть исправен",
           "Charge above 20%, the 12V battery must be healthy",
           "დატენეთ მანქანა 20%-ზე მეტად, 12V უნდა იყოს გამართული"),
         L("Запустить установку, машина не должна ехать ~30–60 мин",
           "Start the install, the car must not be driven for ~30–60 min",
           "დაიწყეთ ინსტალაცია, მანქანა არ უნდა იმოძრაოს ~30–60 წთ"),
         L("Записать новую версию прошивки в комментарий",
           "Write the new software version in the comment",
           "ჩაწერეთ პროგრამის ახალი ვერსია კომენტარში")]},
    {"id": "account", "group": "setup", "mode": "guided", "capture": False,
     "name": L("Перенос на аккаунт нового владельца", "Transfer to new owner's account",
               "ახალი მფლობელის ანგარიშზე გადატანა"),
     "steps": [
         L("Клиент создаёт аккаунт Tesla, если его нет",
           "Client creates a Tesla account if they don't have one",
           "კლიენტი ქმნის Tesla-ს ანგარიშს, თუ არ აქვს"),
         L("В аккаунте клиента: добавить машину по VIN, загрузить документы о покупке",
           "In the client's account: add the car by VIN, upload purchase documents",
           "კლიენტის ანგარიშში: დაამატეთ მანქანა VIN-ით, ატვირთეთ ყიდვის დოკუმენტები"),
         L("Дождаться подтверждения от Tesla (может занять дни)",
           "Wait for Tesla's confirmation (may take days)",
           "დაელოდეთ Tesla-ს დადასტურებას (შეიძლება რამდენიმე დღე დასჭირდეს)"),
         L("После подтверждения привязать телефон как ключ",
           "After confirmation, pair the phone as a key",
           "დადასტურების შემდეგ მიაბით ტელეფონი გასაღებად")]},

    # --- Toolbox: после ремонта у партнёров-кузовщиков ---
    {"id": "cameras", "group": "toolbox", "mode": "guided", "capture": True,
     "name": L("Калибровка камер Autopilot", "Autopilot camera calibration", "Autopilot-ის კამერების კალიბრაცია"),
     "proc": L("калибровка камер", "camera calibration", "კამერების კალიბრაცია")},
    {"id": "provision", "group": "toolbox", "mode": "guided", "capture": True,
     "name": L("Прописка нового блока", "New module setup", "ახალი ბლოკის რეგისტრაცია"),
     "proc": L("прописка/настройка заменённого блока", "setup of the replaced module",
               "შეცვლილი ბლოკის რეგისტრაცია/კონფიგურაცია")},
    {"id": "airbag", "group": "toolbox", "mode": "guided", "capture": True,
     "name": L("Сброс аварийных данных подушек", "Clear airbag crash data", "უსაფრთხოების ბალიშების ავარიული მონაცემების წაშლა"),
     "proc": L("очистка аварийных данных", "clear crash data", "ავარიული მონაცემების წაშლა")},
    {"id": "keys", "group": "toolbox", "mode": "guided", "capture": True,
     "name": L("Привязка ключей", "Key pairing", "გასაღებების მიბმა"),
     "proc": L("добавление ключей", "add keys", "გასაღებების დამატება")},
    {"id": "suspension", "group": "toolbox", "mode": "guided", "capture": True,
     "name": L("Калибровка подвески (S/X)", "Suspension calibration (S/X)", "საკიდრის კალიბრაცია (S/X)"),
     "proc": L("калибровка высоты подвески", "ride height calibration", "საკიდრის სიმაღლის კალიბრაცია")},
    {"id": "nostart", "group": "toolbox", "mode": "guided", "capture": True,
     "name": L("Не заводится после ремонта", "Won't start after repair", "არ იქოქება შეკეთების შემდეგ"),
     "steps": [
         L("Снять данные «до» — посмотреть ошибки и 12V", "Read data “before” — check errors and 12V",
           "მონაცემების აღება „მანამდე“ — ნახეთ შეცდომები და 12V"),
         L("В Toolbox прочитать все ошибки по блокам", "Read all module errors in Toolbox",
           "Toolbox-ში წაიკითხეთ ყველა ბლოკის შეცდომები"),
         L("Показать ошибки Claude — он подскажет причину и что проверить мастеру",
           "Show the errors to Claude — it will suggest the cause and what the mechanic should check",
           "აჩვენეთ შეცდომები Claude-ს — ის მიგითითებთ მიზეზს და რა უნდა შეამოწმოს ხელოსანმა"),
         L("Передать мастеру список, что исправить", "Give the mechanic the list of fixes",
           "გადაეცით ხელოსანს გასასწორებელი სია"),
         L("После исправления снять данные «после»", "After the fix, read data “after”",
           "გასწორების შემდეგ აიღეთ მონაცემები „შემდეგ“")]},

    # --- Партнёр ---
    {"id": "maps", "group": "partner", "mode": "partner", "capture": True,
     "name": L("Карты Европы / смена региона", "Europe maps / region change", "ევროპის რუკები / რეგიონის შეცვლა"),
     "steps": [
         L("Записать VIN, модель, год, версию прошивки", "Write down VIN, model, year, software version",
           "ჩაწერეთ VIN, მოდელი, წელი, პროგრამის ვერსია"),
         L("Передать машину или данные партнёру", "Hand the car or data to the partner",
           "გადაეცით მანქანა ან მონაცემები პარტნიორს"),
         L("После работы снять данные — проверить, что карты появились",
           "After the work, read data — check the maps are there",
           "სამუშაოს შემდეგ აიღეთ მონაცემები — შეამოწმეთ, რომ რუკები გამოჩნდა")]},
    {"id": "hardware", "group": "partner", "mode": "partner",
     "name": L("Ремонт железа (MCU, модем, батарея)", "Hardware repair (MCU, modem, battery)",
               "აპარატურის შეკეთება (MCU, მოდემი, ბატარეა)"),
     "steps": [
         L("Сделать диагностику (услуга «Чтение ошибок»)", "Run diagnostics (the “Read errors” service)",
           "ჩაატარეთ დიაგნოსტიკა (მომსახურება „შეცდომების წაკითხვა“)"),
         L("Передать отчёт партнёру", "Send the report to the partner", "გადაეცით ანგარიში პარტნიორს"),
         L("После ремонта — прописка/калибровка в Toolbox", "After the repair — setup/calibration in Toolbox",
           "შეკეთების შემდეგ — რეგისტრაცია/კალიბრაცია Toolbox-ში")]},
]

for s in SERVICES:
    if "proc" in s and "steps" not in s:
        s["steps"] = [{lang: step[lang].format(proc=s["proc"][lang]) for lang in step} for step in TOOLBOX_STEPS]

BY_ID = {s["id"]: s for s in SERVICES}


def localized(service, lang):
    """Услуга с текстами на одном языке."""
    lang = norm(lang)
    out = dict(service)
    for key in ("name", "prep", "proc"):
        if key in service:
            out[key] = service[key][lang]
    if "steps" in service:
        out["steps"] = [step[lang] for step in service["steps"]]
    return out
