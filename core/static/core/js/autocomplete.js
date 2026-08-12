(() => {
  const form = document.getElementById("vehicleFilterForm");
  if (!form) return;

  const urls = { cities: form.dataset.citiesUrl };

  const debounce = (fn, ms) => {
    let t = null;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  };

  const fireChange = (el) => {
    if (!el) return;
    el.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const fetchOptions = async (url) => {
    try {
      const r = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
      if (!r.ok) return [];
      const data = await r.json();
      return data.results || [];
    } catch (e) {
      console.error("Autocomplete fetch error:", e);
      return [];
    }
  };

  const setupStatic = (key) => {
    const input     = form.querySelector(`[data-ac-input="${key}"]`);
    const list      = form.querySelector(`[data-ac-list="${key}"]`);
    const container = input?.closest("[data-ac-wrap]");

    if (!input || !list) return;

    // Снимаем readonly — теперь поле доступно для набора текста
    input.removeAttribute("readonly");
    input.style.cssText = input.style.cssText
      .replace(/cursor\s*:\s*pointer\s*;?/gi, "")
      .replace(/caret-color\s*:\s*transparent\s*;?/gi, "");

    let selected    = [];
    let activeBrandIds = []; // внешний фильтр по брендам (для поля model)

    // Инициализация из отрендеренных чекбоксов
    list.querySelectorAll("[data-id]").forEach((item) => {
      if (item.querySelector("input[type=checkbox]")?.checked)
        selected.push({ id: String(item.dataset.id), text: item.dataset.text });
    });

    const getIds = () => selected.map((x) => x.id);

    const syncHiddens = () => {
      container?.querySelectorAll(`input[type=hidden][name="${key}"]`).forEach((el) => el.remove());
      selected.forEach((x) => {
        const h = Object.assign(document.createElement("input"), { type: "hidden", name: key, value: x.id });
        (container || input.parentElement).appendChild(h);
      });
    };

    const syncInputText = () => {
      input.value = selected.map((x) => x.text).join(", ");
    };

    const commit = () => { syncHiddens(); syncInputText(); fireChange(input); };

    syncInputText();
    syncHiddens();

    const hide = () => { list.classList.add("uk-hidden"); syncInputText(); };

    // Показывает список, применяя оба фильтра: текстовый и по бренду
    const applyFilters = (query = "") => {
      const q = query.toLowerCase();
      list.querySelectorAll("[data-id]").forEach((item) => {
        const textMatch  = !q || item.dataset.text.toLowerCase().includes(q);
        const brandMatch = !activeBrandIds.length || activeBrandIds.includes(item.dataset.brandId);
        item.style.display = textMatch && brandMatch ? "" : "none";
      });
      list.classList.remove("uk-hidden");
    };

    // Фокус: очищаем отображаемый текст, открываем список
    input.addEventListener("focus", () => {
      input.value = "";
      applyFilters("");
    });

    // Ввод текста: фильтруем список
    input.addEventListener("input", debounce(() => applyFilters(input.value), 150));

    // Клик по полю когда список уже открыт — ничего не делаем;
    // если список скрыт (например, после blur) — открываем
    input.addEventListener("click", () => {
      if (list.classList.contains("uk-hidden")) applyFilters(input.value);
    });

    // Выбор пункта
    list.addEventListener("click", (e) => {
      const item = e.target.closest("[data-id]");
      if (!item) return;

      const id   = String(item.dataset.id);
      const text = item.dataset.text;
      const idx  = selected.findIndex((x) => x.id === id);

      if (idx === -1) selected.push({ id, text });
      else selected.splice(idx, 1);

      const cb = item.querySelector("input[type=checkbox]");
      if (cb) cb.checked = selected.some((x) => x.id === id);

      commit();
      // Оставляем список открытым для множественного выбора
      input.focus();
      applyFilters(input.value);
    });

    // Закрытие по клику вне
    document.addEventListener("click", (e) => {
      const inside =
        e.target.closest(`[data-ac-input="${key}"]`) ||
        e.target.closest(`[data-ac-list="${key}"]`);
      if (!inside) hide();
    });

    input.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });

    // Фильтр по брендам (вызывается извне для поля model)
    const applyBrandFilter = (brandIds) => {
      activeBrandIds = brandIds;
      // Обновляем видимость только если список открыт
      if (!list.classList.contains("uk-hidden")) applyFilters(input.value);
    };

    const reset = () => {
      selected        = [];
      activeBrandIds  = [];
      list.querySelectorAll("input[type=checkbox]").forEach((cb) => (cb.checked = false));
      list.querySelectorAll("[data-id]").forEach((item) => (item.style.display = ""));
      hide();
      commit();
    };

    return { input, hide, reset, getIds, applyBrandFilter };
  };

  // AJAX-автодополнение (город)
  const setupAjax = (key, buildUrl) => {
    const input      = form.querySelector(`[data-ac-input="${key}"]`);
    const list       = form.querySelector(`[data-ac-list="${key}"]`);
    const valueInput = form.querySelector(`[data-ac-value="${key}"]`);

    if (!input || !list) return;

    const hide = () => { list.classList.add("uk-hidden"); list.innerHTML = ""; };

    const show = (items) => {
      if (!items.length) return hide();
      list.innerHTML = items.map((x) =>
        `<div class="uk-padding-small uk-border-bottom ac-item" style="cursor:pointer;"
              data-id="${x.id}" data-text="${String(x.text).replaceAll('"', "&quot;")}">
           ${x.text}
         </div>`
      ).join("");
      list.classList.remove("uk-hidden");
    };

    const doSearch = debounce(async () => {
      const q = (input.value || "").trim();
      // Поле очищено вручную — сбрасываем hidden и триггерим каталог
      if (!q && valueInput && valueInput.value) {
        valueInput.value = "";
        fireChange(valueInput);
        hide();
        return;
      }
      show(await fetchOptions(buildUrl(q)));
    }, 200);

    input.addEventListener("input", doSearch);
    input.addEventListener("focus", doSearch);

    list.addEventListener("click", (e) => {
      const item = e.target.closest("[data-id]");
      if (!item) return;
      input.value = item.dataset.text;
      if (valueInput) valueInput.value = item.dataset.id;
      hide();
      // Диспатчим на hidden, который слушает catalog.js
      fireChange(valueInput || input);
    });

    document.addEventListener("click", (e) => {
      const inside =
        e.target.closest(`[data-ac-input="${key}"]`) ||
        e.target.closest(`[data-ac-list="${key}"]`);
      if (!inside) hide();
    });

    input.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });

    const reset = () => {
      input.value = "";
      if (valueInput) valueInput.value = "";
      hide();
    };

    return { reset };
  };

  // Инициализация
  const brandAC = setupStatic("brand");
  const modelAC = setupStatic("model");

  const cityAC = setupAjax("city", (q) => {
    const base = urls.cities ? String(urls.cities) : "";
    return base ? `${base}?q=${encodeURIComponent(q)}` : "";
  });

  // Смена бренда → фильтруем модели, сбрасываем выбор модели
  const brandInput = form.querySelector(`[data-ac-input="brand"]`);
  if (brandInput) {
    brandInput.addEventListener("change", () => {
      const brandIds = brandAC?.getIds() || [];
      modelAC?.reset();
      modelAC?.applyBrandFilter(brandIds);
    });
  }

  // Кнопка сброса
  const resetBtn = document.getElementById("resetFilters");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      brandAC?.reset();
      modelAC?.reset();
      cityAC?.reset();
    });
  }
})();