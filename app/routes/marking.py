"""
API полного цикла маркировки:
- заказ КМ через СУЗ
- отчёт о нанесении (utilisation)
- ввод в оборот через True API /lk/documents/create
"""

from __future__ import annotations

import base64
import json
from datetime import datetime

from flask import Blueprint, request, jsonify

from app.utils import (
    load_settings,
    save_settings,
    get_product_group_code,
    DEFAULT_PRODUCT_GROUP,
)

marking_bp = Blueprint("marking", __name__)


@marking_bp.route("/api/suz/settings", methods=["GET"])
def get_suz_settings():
    s = load_settings()
    return jsonify({
        "suz_api_url": s.get("suz_api_url", "https://suz2.crpt.ru"),
        "suz_oms_id": s.get("suz_oms_id", ""),
        "suz_contact_person": s.get("suz_contact_person", ""),
        "has_suz_client_token": bool(s.get("suz_client_token")),
        "product_group": s.get("product_group", DEFAULT_PRODUCT_GROUP),
        "product_group_code": get_product_group_code(
            s.get("product_group", DEFAULT_PRODUCT_GROUP)
        ),
    })


@marking_bp.route("/api/suz/settings", methods=["POST"])
def set_suz_settings():
    data = request.json or {}
    s = load_settings()
    for key in ("suz_api_url", "suz_oms_id", "suz_client_token", "suz_contact_person"):
        if key in data:
            s[key] = data[key]
    save_settings(s)
    return jsonify({"ok": True})


@marking_bp.route("/api/suz/ping", methods=["POST"])
def suz_ping():
    try:
        from app.suz_api import ping
        return jsonify({"ok": True, **ping()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/suz/order", methods=["POST"])
def suz_create_order():
    """
    Тело (как в 1С для meat):
    {
      "products": [{
        "gtin": "04680958921310",
        "quantity": 10,
        "serialNumberType": "OPERATOR",
        "cisType": "UNIT",
        "templateId": 74
      }],
      "releaseMethodType": "PRODUCTION",
      "createMethodType": "SELF_MADE",
      "productGroup": "meat",
      "contactPerson": "Иванов И.И.",
      "productionOrderId": "uuid-optional"
    }
    """
    data = request.json or {}
    products = data.get("products") or []
    if not products:
        return jsonify({"ok": False, "error": "products обязателен"}), 400
    try:
        from app.suz_api import create_order
        result = create_order(
            products=products,
            release_method=data.get("releaseMethodType", "PRODUCTION"),
            create_method=data.get("createMethodType", "SELF_MADE"),
            product_group=data.get("productGroup"),
            contact_person=data.get("contactPerson"),
            production_order_id=data.get("productionOrderId"),
            extra_attributes=data.get("attributes"),
        )
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/suz/orders", methods=["GET"])
def suz_list_orders():
    try:
        from app.suz_api import list_orders
        return jsonify({"ok": True, "result": list_orders()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/suz/order/<order_id>/status", methods=["GET"])
def suz_order_status(order_id):
    try:
        from app.suz_api import order_status
        return jsonify({"ok": True, "result": order_status(order_id)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/suz/order/<order_id>/codes", methods=["GET"])
def suz_get_codes(order_id):
    try:
        from app.suz_api import get_codes
        return jsonify({"ok": True, "result": get_codes(order_id)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/suz/order/<order_id>/close", methods=["POST"])
def suz_close_order(order_id):
    try:
        from app.suz_api import close_order
        return jsonify({"ok": True, "result": close_order(order_id)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/suz/utilisation", methods=["POST"])
def suz_utilisation():
    """
    Отчёт о нанесении.
    {
      "sntins": ["01046...21...", ...],
      "productGroup": "meat",
      "attributes": {}
    }
    """
    data = request.json or {}
    sntins = data.get("sntins") or []
    if not sntins:
        return jsonify({"ok": False, "error": "sntins обязателен"}), 400
    try:
        from app.suz_api import utilisation_report
        result = utilisation_report(
            sntins=sntins,
            product_group=data.get("productGroup"),
            attributes=data.get("attributes"),
        )
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/suz/report/<report_id>", methods=["GET"])
def suz_report_info(report_id):
    try:
        from app.suz_api import report_info
        return jsonify({"ok": True, "result": report_info(report_id)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/true/introduce", methods=["POST"])
def true_introduce():
    """
    Ввод в оборот через True API POST /lk/documents/create?pg=...

    Тело:
    {
      "document_type": "LP_INTRODUCE_GOODS",
      "document": { ... },
      "product_group": "meat"
    }
    """
    data = request.json or {}
    document = data.get("document")
    if not document:
        return jsonify({"ok": False, "error": "document обязателен"}), 400

    doc_type = data.get("document_type") or "LP_INTRODUCE_GOODS"
    s = load_settings()
    pg = data.get("product_group") or get_product_group_code(
        s.get("product_group", DEFAULT_PRODUCT_GROUP)
    )
    if not pg:
        return jsonify({"ok": False, "error": "Не задана товарная группа"}), 400

    try:
        from app.cz_api import create_document
        result = create_document(
            product_group=pg,
            document_type=doc_type,
            document=document,
        )
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@marking_bp.route("/api/marking/cycle-help", methods=["GET"])
def cycle_help():
    return jsonify({
        "ok": True,
        "steps": [
            {
                "step": 1,
                "name": "Настройки",
                "desc": (
                    "ЭЦП, ИНН, product_group=meat (строковый код для СУЗ). "
                    "OMS ID, URL СУЗ = https://suz2.crpt.ru, contactPerson. "
                    "Числовой ID для баланса сверяйте в ЛК — 62 может быть неверным."
                ),
            },
            {
                "step": 2,
                "name": "Заказ КМ",
                "endpoint": "POST /api/suz/order",
                "body": {
                    "products": [{
                        "gtin": "04680958921310",
                        "quantity": 10,
                        "serialNumberType": "OPERATOR",
                        "cisType": "UNIT",
                        "templateId": 74,
                    }],
                    "productGroup": "meat",
                    "contactPerson": "ФИО",
                    "releaseMethodType": "PRODUCTION",
                    "createMethodType": "SELF_MADE",
                },
            },
            {
                "step": 3,
                "name": "Статус / коды",
                "endpoints": [
                    "GET /api/suz/order/{orderId}/status",
                    "GET /api/suz/order/{orderId}/codes",
                ],
            },
            {
                "step": 4,
                "name": "Отчёт о нанесении",
                "endpoint": "POST /api/suz/utilisation",
                "body": {"sntins": ["01046...21..."], "productGroup": "meat"},
            },
            {
                "step": 5,
                "name": "Ввод в оборот",
                "endpoint": "POST /api/true/introduce",
                "note": "Тип и поля document зависят от ТГ meat — уточняйте в ЛК True API",
            },
        ],
        "product_group_meat": {
            "code": "meat",
            "name": "Мясные изделия",
            "suz_url": "https://suz2.crpt.ru",
            "templateId": 74,
            "note": "Числовой productGroupId для /elk/.../balance смотрите в ЛК ЧЗ",
        },
        "urls": {
            "suz_prod": "https://suz2.crpt.ru",
            "suz_legacy": "https://suzgrid.crpt.ru",
            "suz_sandbox": "https://suz.sandbox.crptech.ru",
            "true_prod": "https://markirovka.crpt.ru/api/v3/true-api",
            "true_sandbox": "https://markirovka.sandbox.crptech.ru/api/v3/true-api",
        },
    })
