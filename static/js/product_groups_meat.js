/**
 * Дополнение списка товарных групп для fork (мясо и пищевые).
 *
 * Мясо: productGroupId=25 (баланс True API), code=meat (СУЗ), templateId=74
 */
window.EXTRA_PRODUCT_GROUPS = [
  { id: "25", code: "meat", name: "25 — Мясные изделия" },
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

  // Миграция старого неверного ID 62 → 25
  for (const opt of [...sel.options]) {
    if (opt.value === "62") {
      opt.value = "25";
      opt.textContent = "25 — Мясные изделия";
    }
  }

  const existing = new Set([...sel.options].map((o) => o.value));
  for (const g of window.EXTRA_PRODUCT_GROUPS) {
    if (existing.has(g.id)) continue;
    const opt = document.createElement("option");
    opt.value = g.id;
    opt.textContent = g.name;
    sel.appendChild(opt);
  }

  // Если в settings был 62 — UI уже показывает 25; при сохранении уйдёт 25
  if (sel.value === "62") sel.value = "25";
}

document.addEventListener("DOMContentLoaded", injectExtraProductGroups);
