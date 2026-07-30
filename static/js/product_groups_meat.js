/**
 * Дополнение списка товарных групп для fork (мясо и пищевые).
 * Подключается опционально или встраивается в app.js.
 *
 * Числовые ID для баланса сверяйте в ЛК ЧЗ.
 * Код productGroup для СУЗ/True API: meat, milk, water, ...
 */
window.EXTRA_PRODUCT_GROUPS = [
  { id: "62", code: "meat", name: "62 — Мясные изделия" },
  { id: "8", code: "milk", name: "8 — Молочная продукция" },
  { id: "13", code: "water", name: "13 — Упакованная вода" },
  { id: "16", code: "conserve", name: "16 — Консервированная продукция" },
  { id: "15", code: "softdrinks", name: "15 — Безалкогольные напитки" },
  { id: "14", code: "beer", name: "14 — Пиво" },
  { id: "12", code: "seafood", name: "12 — Морепродукты" },
  { id: "17", code: "petfood", name: "17 — Корма для животных" },
];

function injectExtraProductGroups() {
  const sel = document.getElementById("product-group");
  if (!sel || !window.EXTRA_PRODUCT_GROUPS) return;
  const existing = new Set([...sel.options].map((o) => o.value));
  for (const g of window.EXTRA_PRODUCT_GROUPS) {
    if (existing.has(g.id)) continue;
    const opt = document.createElement("option");
    opt.value = g.id;
    opt.textContent = g.name;
    sel.appendChild(opt);
  }
}

document.addEventListener("DOMContentLoaded", injectExtraProductGroups);
