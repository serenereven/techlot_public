(function () { // Catalog AJAX Controller

    const form = document.getElementById("vehicleFilterForm");
    if (!form) return;

    const resultsWrap    = document.getElementById("vehicleResultsWrap");
    const paginationWrap = document.getElementById("vehiclePaginationWrap");
    const countSpan      = document.getElementById("result-count");
    const ajaxUrl        = form.dataset.ajaxUrl;

    // На главной нет resultsWrap — форма работает как нативный GET-редирект на каталог.
    const isHomepage = !resultsWrap;

    let currentRequest = null;
    let debounceTimer  = null;
    let nextPage       = null;
    let isLoading      = false;


    // Helpers
    function serializeForm(page = 1) {
        const fd = new FormData(form);
        fd.set("page", page);
        return new URLSearchParams(fd).toString();
    }

    function debounce(callback, delay = 400) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(callback, delay);
    }

    function abortPrevious() {
        if (currentRequest) currentRequest.abort();
        currentRequest = new AbortController();
        return currentRequest.signal;
    }

    // Только счётчик (главная)
    function fetchCount() {
        if (!countSpan || !ajaxUrl) return;
        const signal = abortPrevious();
        fetch(`${ajaxUrl}?${serializeForm()}`, { signal })
            .then(r => r.json())
            .then(data => { countSpan.innerText = data.total; })
            .catch(err => { if (err.name !== "AbortError") console.error("Count fetch error:", err); });
    }


    // Infinite scroll
    let sentinel = null;

    if (!isHomepage) {
        // nextPage инициализируется из data-атрибута, который Django рендерит в шаблоне.
        // В vehicle_list.html: <div id="vehicleResultsWrap" data-next-page="{{ page_obj.next_page_number|default:'' }}">
        const initialNext = parseInt(resultsWrap.dataset.nextPage, 10);
        if (!isNaN(initialNext)) nextPage = initialNext;

        sentinel = document.createElement("div");
        sentinel.style.height = "1px";
        resultsWrap.after(sentinel);

        new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && nextPage && !isLoading) loadMore(nextPage);
        }, { rootMargin: "200px" }).observe(sentinel);
    }

    // Loaders
    function loadVehicles(page = 1, pushHistory = true) {
        const params = serializeForm(page);
        const signal = abortPrevious();
        isLoading = true;

        fetch(`${ajaxUrl}?${params}`, { signal })
            .then(r => r.json())
            .then(data => {
                if (resultsWrap)    resultsWrap.innerHTML = data.items_html;
                if (paginationWrap) paginationWrap.innerHTML = "";
                if (countSpan)      countSpan.innerText = data.total;

                nextPage  = data.has_more ? data.next_page : null;
                isLoading = false;

                if (pushHistory) window.history.replaceState({}, "", "?" + params);
            })
            .catch(err => {
                isLoading = false;
                if (err.name !== "AbortError") console.error("Catalog load error:", err);
            });
    }

    function loadMore(page) {
        const params = serializeForm(page);
        isLoading = true;

        fetch(`${ajaxUrl}?${params}`)
            .then(r => r.json())
            .then(data => {
                const grid = document.getElementById("vehicle-grid");
                if (grid) {
                    // Парсим фрагмент, берём карточки из #vehicle-grid и переносим в существующий.
                    const tmp = document.createElement("div");
                    tmp.innerHTML = data.items_html;
                    const newGrid = tmp.querySelector("#vehicle-grid");
                    if (newGrid) grid.append(...newGrid.children);
                }
                nextPage  = data.has_more ? data.next_page : null;
                isLoading = false;
            })
            .catch(err => {
                isLoading = false;
                console.error("Load more error:", err);
            });
    }


    // Events
    form.addEventListener("submit", e => {
        if (isHomepage) return; // нативный GET → /catalog/?...
        e.preventDefault();
        loadVehicles();
    });

    // Делегируем на form — покрывает hidden-инпуты, которые autocomplete.js создаёт динамически,
    // и текстовые поля марки/модели (data-ac-input), которые fireChange диспатчит после выбора.
    form.addEventListener("change", e => {
        const el = e.target;
        const tracked = el.matches(
            "input[type='checkbox'], input[type='number'], input[type='hidden'], select, [data-ac-input]"
        );
        if (!tracked) return;
        isHomepage ? debounce(fetchCount, 300) : loadVehicles();
    });

    // Live search
    const searchInput = form.querySelector("input[name='q']");
    if (searchInput) {
        searchInput.addEventListener("input", () =>
            debounce(() => isHomepage ? fetchCount() : loadVehicles(), 400)
        );
    }

    // Сброс
    const resetBtn = document.getElementById("resetFilters");
    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            const q = form.querySelector("input[name='q']");
            if (q) q.value = "";
            form.querySelectorAll("input[type='number']").forEach(el => el.value = "");
            form.querySelectorAll("select").forEach(sel => sel.selectedIndex = 0);
            form.querySelectorAll("input[type='hidden']").forEach(el => el.value = "");
            form.querySelectorAll("input[data-ac-input]").forEach(el => el.value = "");
            form.querySelectorAll("input[type='checkbox']").forEach(cb => cb.checked = false);

            window.history.replaceState({}, "", window.location.pathname);
            loadVehicles(1, false);
        });
    }

    if (!isHomepage) {
        window.addEventListener("popstate", () => loadVehicles(1, false));
    }

})();