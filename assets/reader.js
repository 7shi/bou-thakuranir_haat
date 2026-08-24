document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".lang-tab");
    const panels = document.querySelectorAll(".text-panel");
    if (tabs.length === 0 || panels.length === 0) return;

    const storageKey = "bthaat.lang";
    let saved = null;
    try {
        saved = localStorage.getItem(storageKey);
    } catch (e) {
        // localStorage unavailable (private mode, etc.) — ignore.
    }

    const keys = Array.from(tabs).map((t) => t.dataset.key);
    const initial = keys.includes(saved) ? saved : keys[0];

    function activate(key) {
        tabs.forEach((t) => t.classList.toggle("active", t.dataset.key === key));
        panels.forEach((p) => p.classList.toggle("active", p.dataset.key === key));
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            activate(tab.dataset.key);
            try {
                localStorage.setItem(storageKey, tab.dataset.key);
            } catch (e) {
                // ignore
            }
        });
    });

    activate(initial);
});
