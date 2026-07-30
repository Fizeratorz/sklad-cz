# Полный цикл маркировки (мясо / Мясные изделия)

Расширение fork `Fizeratorz/sklad-cz`: заказ КМ, отчёт о нанесении, ввод в оборот.

## Товарная группа

| Поле | Значение |
|------|----------|
| Название | Мясные изделия |
| Код (СУЗ / True API `pg`) | `meat` |
| Числовой ID в настройках | `62` (проверьте в ЛК ЧЗ для баланса) |
| Контакт ЦРПТ | meat@crpt.ru |
| Telegram | @markirovka_meat |

Сроки (ориентир 2026):
- с 1 августа — готовые мясные изделия / деликатесы (ТН ВЭД 1602)
- с 1 октября — колбасные изделия (ТН ВЭД 1601)

## Настройки

В **Настройки → Честный Знак**:

1. Товарная группа → **Мясные изделия**
2. ИНН, отпечаток ЭЦП, PIN
3. **OMS ID** (ЛК → Управление заказами → Устройства)
4. URL СУЗ:
   - прод: `https://suzgrid.crpt.ru`
   - песочница: `https://suz.sandbox.crptech.ru`

API настроек СУЗ:

```http
GET  /api/suz/settings
POST /api/suz/settings
{"suz_api_url": "https://suzgrid.crpt.ru", "suz_oms_id": "...", "suz_client_token": ""}
```

## 1. Заказ кодов (СУЗ)

```http
POST /api/suz/order
Content-Type: application/json

{
  "products": [
    {
      "gtin": "04601234567890",
      "quantity": 100,
      "serialNumberType": "OPERATOR"
    }
  ],
  "releaseMethodType": "PRODUCTION",
  "createMethodType": "SELF_MADE",
  "productGroup": "meat"
}
```

- Подпись: откреплённая CAdES-BES → заголовок `X-Signature`
- Тело JSON **без пробелов** (`separators=(',', ':')`)
- `serialNumberType`: `OPERATOR` — серийники генерит СУЗ; `SELF_MADE` — свои

Статус / коды:

```http
GET /api/suz/order/{orderId}/status
GET /api/suz/order/{orderId}/codes
POST /api/suz/order/{orderId}/close
GET /api/suz/orders
```

## 2. Отчёт о нанесении (СУЗ utilisation)

```http
POST /api/suz/utilisation

{
  "sntins": [
    "010460123456789021XXXXXXXXXXXXX"
  ],
  "productGroup": "meat",
  "attributes": {}
}
```

Точный состав `attributes` и формат `sntins` для meat сверяйте с документацией СУЗ в ЛК (раздел «Помощь»).

Статус отчёта:

```http
GET /api/suz/report/{reportId}
```

## 3. Ввод в оборот (True API)

```http
POST /api/true/introduce

{
  "document_type": "LP_INTRODUCE_GOODS",
  "product_group": "meat",
  "document": {
    "participant_inn": "7700000000",
    "production_date": "2026-08-01",
    "products": [
      {"uit_code": "01046...", "tnved_code": "1602..."}
    ]
  }
}
```

Реализация:
- `POST {true-api}/lk/documents/create?pg=meat`
- `productDocument` = base64(JSON document)
- `signature` = CAdES-BES от содержимого

**Важно:** тип документа и схема JSON для «Мясные изделия» могут отличаться от `LP_INTRODUCE_GOODS` (лёгпром). Актуальную схему берите из документации True API в ЛК ЧЗ.

## Модули кода

| Файл | Назначение |
|------|------------|
| `app/suz_api.py` | Клиент СУЗ: order, codes, utilisation, close |
| `app/cz_api.py` | + `create_document()` для True API |
| `app/routes/marking.py` | HTTP API цикла |
| `app/utils.py` | PRODUCT_GROUPS + meat |

## Подсказки

```http
GET /api/marking/cycle-help
POST /api/suz/ping
```

## Ограничения

1. Без зарегистрированного OMS ID и ЭЦП в ЛК вызовы СУЗ не пройдут.
2. Песочница и прод — разные OMS/сертификаты.
3. Для весового мяса могут быть отдельные поля (переменный вес) — уточняйте в доке ТГ meat.
4. Пересечение с ФГИС «Меркурий» для сырого мяса этим модулем не закрывается.
5. UI пока использует API; вкладка «Заказы КМ» в интерфейсе может быть доработана отдельно.

## Чеклист первого запуска

- [ ] КриптоПро + сертификат
- [ ] Товарная группа meat в профиле ЛК ЧЗ
- [ ] OMS ID устройства
- [ ] Пополнен лицевой счёт ТГ
- [ ] GTIN в Национальном каталоге
- [ ] `POST /api/suz/ping` → OK
- [ ] Тестовый заказ 1–2 кода на sandbox
"}]