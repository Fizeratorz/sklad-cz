# Документация Sklad-CZ (fork Fizeratorz)

Оригинальная документация + расширения для полного цикла маркировки.

## Оглавление

1. [Первичная настройка](01-первичная-настройка.md)
2. [SKU товары](02-sku-tovary.md)
3. [Склады](03-sklady.md)
4. [Сканирование](04-skanirovanie.md)
5. [Импорт CSV](05-import-csv.md)
6. [Отчёт о нанесении (ручной ЛК)](06-otchet-nanesenie.md)
7. [Проверка статуса](07-proverka-statusa.md)
7b. [Оффлайн-валидация](07b-offline-validaciya.md)
8. [Печать этикеток](08-pechat-etiketki.md)
9. [Ввод в оборот (ручной ЛК)](09-vvod-v-oborot.md)
10. [Продажа](10-prodazha.md)
11. [Дубль маркировки](11-dubl-markirovki.md)
12. [Вывод из оборота](12-vyvod-iz-oborota.md)
13. [Возврат](13-vozvrat.md)
14. [Вывод вне продажи](14-vyvod-vne-prodazhi.md)
15. [API Честный Знак](15-api-chestny-znak.md)
16. [Баланс лицевого счёта](16-balans-lico-scheta.md)
17. **[Полный цикл: заказ / нанесение / ввод (мясо)](17-full-cycle-meat.md)** ← NEW

## Быстрый старт для мяса

```bash
git clone https://github.com/Fizeratorz/sklad-cz.git
cd sklad-cz
# Windows: setup.bat && start.bat
# Linux:  ./setup.sh && ./run.sh
```

В `instance/settings.json` (или через API):

```json
{
  "product_group": "62",
  "cz_inn": "...",
  "cz_cert_thumbprint": "...",
  "suz_oms_id": "...",
  "suz_api_url": "https://suzgrid.crpt.ru",
  "cz_api_url": "https://markirovka.crpt.ru/api/v3/true-api"
}
```

Справка по эндпоинтам: `GET /api/marking/cycle-help`
