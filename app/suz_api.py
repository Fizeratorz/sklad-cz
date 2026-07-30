"""
Клиент СУЗ (Станция управления заказами) Честный Знак.

Поддерживает:
- авторизацию (clientToken через True API / omsConnection)
- создание заказа на эмиссию КМ (POST /api/v3/order)
- статус заказа, список заказов, получение кодов
- отчёт о нанесении / utilisation (POST /api/v3/utilisation)
- закрытие заказа

Подпись заказов — откреплённая CAdES-BES в заголовке X-Signature.
"""

from __future__ import annotations

import base64
import json
import sys
from typing import Any

import requests

from app.utils import load_settings, get_product_group_code
from app.cz_api import _sign_data, get_uuid_token, reset_token

_platform = sys.platform
_suz_token: str | None = None

# Продакшн / песочница СУЗ
SUZ_PROD = "https://suzgrid.crpt.ru"
SUZ_SANDBOX = "https://suz.sandbox.crptech.ru"


def _is_windows() -> bool:
    return _platform == "win32"


def _get_suz_base() -> str:
    s = load_settings()
    return (s.get("suz_api_url") or SUZ_PROD).rstrip("/")


def _get_oms_id() -> str:
    s = load_settings()
    oms = (s.get("suz_oms_id") or "").strip()
    if not oms:
        raise Exception(
            "OMS ID не задан. Укажите в Настройки → Честный Знак → OMS ID "
            "(ЛК ЧЗ → Управление заказами → Устройства)."
        )
    return oms


def _get_product_group_str() -> str:
    s = load_settings()
    pg = s.get("product_group", "27")
    code = get_product_group_code(pg)
    if not code:
        # если уже передали строковый код
        if isinstance(pg, str) and not pg.isdigit():
            return pg
        raise Exception(f"Неизвестная товарная группа: {pg}")
    return code


def _sign_detached(data: str, thumbprint: str | None = None) -> str:
    """Откреплённая подпись CAdES-BES для заголовка X-Signature (СУЗ)."""
    s = load_settings()
    if not thumbprint:
        thumbprint = s.get("cz_cert_thumbprint", "")
    if not thumbprint:
        raise Exception("Отпечаток сертификата не задан")

    if _is_windows():
        import win32com.client
        import pythoncom

        try:
            pythoncom.CoInitialize()
        except Exception:
            pass
        try:
            target = thumbprint.upper()
            cert = None
            for loc in (2, 1):  # LOCAL_MACHINE, CURRENT_USER
                try:
                    store = win32com.client.Dispatch("CAdESCOM.Store")
                    store.Open(loc, "My", 0)
                    for i in range(1, store.Certificates.Count + 1):
                        c = store.Certificates.Item(i)
                        if c.Thumbprint.upper() == target:
                            cert = c
                            break
                    store.Close()
                    if cert:
                        break
                except Exception:
                    continue
            if not cert:
                raise Exception(f"Сертификат {thumbprint} не найден")

            signer = win32com.client.Dispatch("CAdESCOM.CPSigner")
            signer.Certificate = cert
            signer.CheckCertificate = True

            sd = win32com.client.Dispatch("CAdESCOM.CadesSignedData")
            sd.ContentEncoding = 1  # base64
            sd.Content = base64.b64encode(data.encode("utf-8")).decode("ascii")
            # CADES_BES=1, detached=True, CAPICOM_ENCODE_BASE64=0
            sig = sd.SignCades(signer, 1, True, 0)
            return sig.replace("\r", "").replace("\n", "")
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
    else:
        import pycades

        store = pycades.Store()
        store.Open(
            pycades.CADESCOM_CURRENT_USER_STORE,
            pycades.CAPICOM_MY_STORE,
            pycades.CAPICOM_STORE_OPEN_READ_ONLY,
        )
        certs = store.Certificates.Find(
            pycades.CAPICOM_CERTIFICATE_FIND_SHA1_HASH, thumbprint
        )
        if certs.Count == 0:
            raise Exception(f"Сертификат {thumbprint} не найден")
        cert = certs.Item(1)
        signer = pycades.Signer()
        signer.Certificate = cert
        signer.CheckCertificate = True
        signed = pycades.SignedData()
        signed.Content = data
        sig = signed.SignCades(signer, pycades.CADESCOM_CADES_BES, True)
        return sig.replace("\r", "").replace("\n", "")


def get_suz_token(force: bool = False) -> str:
    """
    Получить clientToken для СУЗ.
    Используем united JWT из True API (unitedToken=True при simpleSignIn).
    При необходимости можно хранить отдельный suz_client_token в настройках.
    """
    global _suz_token
    if _suz_token and not force:
        return _suz_token

    s = load_settings()
    manual = (s.get("suz_client_token") or "").strip()
    if manual and not force:
        _suz_token = manual
        return _suz_token

    # Пробуем JWT True API — многие интеграции используют его как clientToken
    try:
        token = get_uuid_token()
        _suz_token = token
        return token
    except Exception as e:
        raise Exception(
            f"Не удалось получить токен для СУЗ: {e}. "
            f"Проверьте ЭЦП или задайте suz_client_token вручную."
        )


def reset_suz_token():
    global _suz_token
    _suz_token = None


def _suz_headers(json_body: str | None = None, signed: bool = False) -> dict:
    token = get_suz_token()
    headers = {
        "clientToken": token,
        "Accept": "application/json",
        "Content-Type": "application/json;charset=UTF-8",
    }
    if signed and json_body is not None:
        headers["X-Signature"] = _sign_detached(json_body)
    return headers


def create_order(
    products: list[dict],
    release_method: str = "PRODUCTION",
    create_method: str = "SELF_MADE",
    product_group: str | None = None,
) -> dict:
    """
    Создать заказ на эмиссию кодов маркировки.

    products: список вида
      [{"gtin": "0460...", "quantity": 10, "serialNumberType": "OPERATOR"}]
      serialNumberType: OPERATOR (серийники генерит СУЗ) | SELF_MADE

    Возвращает ответ СУЗ (orderId, status и т.д.).
    """
    oms_id = _get_oms_id()
    pg = product_group or _get_product_group_str()

    body = {
        "productGroup": pg,
        "products": products,
        "attributes": {
            "releaseMethodType": release_method,
            "createMethodType": create_method,
        },
    }
    # JSON без пробелов — иначе подпись не сойдётся
    json_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))

    url = f"{_get_suz_base()}/api/v3/order"
    headers = _suz_headers(json_str, signed=True)
    r = requests.post(
        url,
        params={"omsId": oms_id},
        headers=headers,
        data=json_str.encode("utf-8"),
        timeout=60,
    )
    if r.status_code == 401:
        reset_suz_token()
        headers = _suz_headers(json_str, signed=True)
        r = requests.post(
            url,
            params={"omsId": oms_id},
            headers=headers,
            data=json_str.encode("utf-8"),
            timeout=60,
        )
    if r.status_code >= 400:
        raise Exception(f"СУЗ order HTTP {r.status_code}: {r.text[:500]}")
    return r.json() if r.text else {"ok": True, "status_code": r.status_code}


def list_orders() -> Any:
    oms_id = _get_oms_id()
    url = f"{_get_suz_base()}/api/v3/order/list"
    r = requests.get(
        url,
        params={"omsId": oms_id},
        headers=_suz_headers(),
        timeout=30,
    )
    if r.status_code >= 400:
        raise Exception(f"СУЗ order/list HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


def order_status(order_id: str) -> Any:
    url = f"{_get_suz_base()}/api/v3/order/status"
    r = requests.get(
        url,
        params={"orderId": order_id},
        headers=_suz_headers(),
        timeout=30,
    )
    if r.status_code >= 400:
        raise Exception(f"СУЗ order/status HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


def get_codes(order_id: str) -> Any:
    """Скачать выпущенные коды по заказу."""
    url = f"{_get_suz_base()}/api/v3/codes"
    r = requests.get(
        url,
        params={"orderId": order_id},
        headers=_suz_headers(),
        timeout=120,
    )
    if r.status_code >= 400:
        raise Exception(f"СУЗ codes HTTP {r.status_code}: {r.text[:500]}")
    try:
        return r.json()
    except Exception:
        return {"raw": r.text}


def close_order(order_id: str) -> Any:
    oms_id = _get_oms_id()
    body = {"orderId": order_id}
    json_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    url = f"{_get_suz_base()}/api/v3/order/close"
    r = requests.post(
        url,
        params={"omsId": oms_id},
        headers=_suz_headers(json_str, signed=True),
        data=json_str.encode("utf-8"),
        timeout=30,
    )
    if r.status_code >= 400:
        raise Exception(f"СУЗ order/close HTTP {r.status_code}: {r.text[:500]}")
    return r.json() if r.text else {"ok": True}


def utilisation_report(
    sntins: list[str],
    product_group: str | None = None,
    attributes: dict | None = None,
) -> dict:
    """
    Отчёт о нанесении (utilisation) через СУЗ.

    sntins — список КМ (обычно без криптохвоста или полные — зависит от ТГ).
    Для ряда товарных групп структура attributes отличается;
    для мяса уточняйте актуальный формат в документации СУЗ ЛК.
    """
    oms_id = _get_oms_id()
    pg = product_group or _get_product_group_str()

    body: dict[str, Any] = {
        "productGroup": pg,
        "sntins": sntins,
    }
    if attributes:
        body["attributes"] = attributes

    json_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    url = f"{_get_suz_base()}/api/v3/utilisation"
    r = requests.post(
        url,
        params={"omsId": oms_id},
        headers=_suz_headers(json_str, signed=True),
        data=json_str.encode("utf-8"),
        timeout=120,
    )
    if r.status_code >= 400:
        raise Exception(f"СУЗ utilisation HTTP {r.status_code}: {r.text[:500]}")
    return r.json() if r.text else {"ok": True, "status_code": r.status_code}


def report_info(report_id: str) -> Any:
    url = f"{_get_suz_base()}/api/v3/report/info"
    r = requests.get(
        url,
        params={"reportId": report_id},
        headers=_suz_headers(),
        timeout=30,
    )
    if r.status_code >= 400:
        raise Exception(f"СУЗ report/info HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


def ping() -> Any:
    oms_id = _get_oms_id()
    url = f"{_get_suz_base()}/api/v3/ping"
    r = requests.get(
        url,
        params={"omsId": oms_id},
        headers=_suz_headers(),
        timeout=15,
    )
    return {"status_code": r.status_code, "body": r.text[:300]}
