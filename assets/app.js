"use strict";

// Головоломки: просмотр задачи крупно, отметки «Решено», фильтр и согласие на cookie.
// Без JS карточки остаются обычными ссылками на картинку.
(function () {
  const cards = Array.from(document.querySelectorAll(".card"));
  if (!cards.length) return;
  const byN = new Map(cards.map(function (c) { return [c.dataset.n, c]; }));

  // ---------------------------------------------------------------- cookie
  // Храним только номера решённых задач и сам выбор про cookie. Cookie живёт
  // в папке сайта (на GitHub Pages — /<репозиторий>/), год, SameSite=Lax.
  const COOKIE_PATH = location.pathname.replace(/[^/]*$/, "") || "/";
  const YEAR = 60 * 60 * 24 * 365;

  function readCookie(name) {
    const parts = document.cookie ? document.cookie.split("; ") : [];
    for (const part of parts) {
      const eq = part.indexOf("=");
      if (part.slice(0, eq) === name) return decodeURIComponent(part.slice(eq + 1));
    }
    return null;
  }

  function writeCookie(name, value, maxAge) {
    let c = name + "=" + encodeURIComponent(value) + "; Max-Age=" + maxAge +
      "; Path=" + COOKIE_PATH + "; SameSite=Lax";
    if (location.protocol === "https:") c += "; Secure";
    document.cookie = c;
  }

  function consent() {
    return readCookie("iqp_consent"); // "yes" | "no" | null
  }

  const solved = new Set();
  if (consent() === "yes") {
    (readCookie("iqp_solved") || "").split("-").forEach(function (n) {
      if (/^\d{1,3}$/.test(n) && byN.has(n)) solved.add(n);
    });
  }

  function saveSolved() {
    if (consent() !== "yes") return;
    const list = Array.from(solved).sort(function (a, b) { return a - b; }).join("-");
    writeCookie("iqp_solved", list, YEAR);
  }

  // ---------------------------------------------------------------- баннер
  const banner = document.getElementById("consent");

  function showBanner(show) {
    banner.hidden = !show;
    document.body.classList.toggle("has-consent", show);
  }

  document.getElementById("c-accept").addEventListener("click", function () {
    writeCookie("iqp_consent", "yes", YEAR);
    saveSolved();
    showBanner(false);
  });
  document.getElementById("c-decline").addEventListener("click", function () {
    writeCookie("iqp_consent", "no", YEAR);
    writeCookie("iqp_solved", "", 0);
    showBanner(false);
  });
  document.getElementById("c-settings").addEventListener("click", function () {
    showBanner(true);
  });
  showBanner(consent() === null);

  // ---------------------------------------------------------------- фильтр
  let filter = "all";
  const chips = Array.from(document.querySelectorAll(".chip"));
  const empty = document.getElementById("empty");

  function matches(card) {
    const s = solved.has(card.dataset.n);
    return filter === "all" || (filter === "solved" ? s : !s);
  }

  function refresh() {
    let shown = 0;
    cards.forEach(function (card) {
      const s = solved.has(card.dataset.n);
      card.classList.toggle("is-solved", s);
      const btn = card.querySelector(".solved-btn");
      btn.setAttribute("aria-pressed", String(s));
      btn.textContent = s ? "✓ Решено" : "Решено";
      card.hidden = !matches(card);
      if (!card.hidden) shown++;
    });
    empty.hidden = shown > 0;
    const counts = { all: cards.length, solved: solved.size, unsolved: cards.length - solved.size };
    document.querySelectorAll("[data-count]").forEach(function (el) {
      el.textContent = counts[el.dataset.count];
    });
    chips.forEach(function (chip) {
      chip.setAttribute("aria-pressed", String(chip.dataset.filter === filter));
    });
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      filter = chip.dataset.filter;
      refresh();
    });
  });

  function toggleSolved(n) {
    if (solved.has(n)) solved.delete(n);
    else solved.add(n);
    saveSolved();
    refresh();
  }

  cards.forEach(function (card) {
    card.querySelector(".solved-btn").addEventListener("click", function () {
      toggleSolved(card.dataset.n);
    });
  });

  // ---------------------------------------------------------------- просмотр
  const dlg = document.getElementById("viewer");
  const canDialog = dlg && typeof dlg.showModal === "function";
  const img = document.getElementById("v-img");
  const title = document.getElementById("v-title");
  const toggle = document.getElementById("v-toggle");
  const answer = document.getElementById("v-answer");
  const vSolved = document.getElementById("v-solved");
  let current = null;
  let revealed = false;

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function render() {
    const n = current.dataset.n;
    img.src = "img/" + pad(n) + (revealed ? "_solution.svg" : "_task.svg");
    img.alt = "Задача " + n + (revealed ? ", решение" : "");
    title.textContent = "Задача " + n;
    toggle.textContent = revealed ? "Скрыть ответ" : "Показать ответ";
    toggle.setAttribute("aria-expanded", String(revealed));
    const s = solved.has(n);
    vSolved.setAttribute("aria-pressed", String(s));
    vSolved.textContent = s ? "✓ Решено" : "Решено";

    answer.replaceChildren();
    if (revealed) {
      const strong = document.createElement("strong");
      strong.textContent = "Ответ: " + current.dataset.answer + ". ";
      answer.append(strong, document.createTextNode(current.dataset.expl || ""));
    }
    answer.hidden = !revealed;
    history.replaceState(null, "", "#" + n);
  }

  function show(card) {
    current = card;
    revealed = false;
    render();
  }

  function step(delta) {
    // листаем только задачи, видимые при текущем фильтре (и текущую, если её скрыли)
    const list = cards.filter(function (c) { return !c.hidden || c === current; });
    const i = list.indexOf(current);
    show(list[(i + delta + list.length) % list.length]);
  }

  function open(card) {
    show(card);
    if (!dlg.open) dlg.showModal();
  }

  if (canDialog) {
    cards.forEach(function (card) {
      card.querySelector(".card-link").addEventListener("click", function (e) {
        e.preventDefault();
        open(card);
      });
    });

    toggle.addEventListener("click", function () {
      revealed = !revealed;
      render();
    });
    vSolved.addEventListener("click", function () {
      toggleSolved(current.dataset.n);
      render();
    });
    document.getElementById("v-prev").addEventListener("click", function () { step(-1); });
    document.getElementById("v-next").addEventListener("click", function () { step(1); });
    document.getElementById("v-close").addEventListener("click", function () { dlg.close(); });

    // клик по затемнению вокруг окна закрывает его
    dlg.addEventListener("click", function (e) {
      if (e.target === dlg) dlg.close();
    });

    dlg.addEventListener("close", function () {
      history.replaceState(null, "", location.pathname + location.search);
      if (current && !current.hidden) current.querySelector(".card-link").focus();
    });

    document.addEventListener("keydown", function (e) {
      if (!dlg.open) return;
      if (e.key === "ArrowLeft") step(-1);
      else if (e.key === "ArrowRight") step(1);
    });

    // свайп влево/вправо на телефоне
    let startX = null;
    let startY = null;
    const area = document.querySelector(".viewer-img");
    area.addEventListener("touchstart", function (e) {
      if (e.touches.length !== 1) { startX = null; return; }
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    }, { passive: true });
    area.addEventListener("touchend", function (e) {
      if (startX === null) return;
      const dx = e.changedTouches[0].clientX - startX;
      const dy = e.changedTouches[0].clientY - startY;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) step(dx < 0 ? 1 : -1);
      startX = null;
    }, { passive: true });
  }

  refresh();

  // прямая ссылка на задачу: …/#12
  const m = location.hash.match(/^#(\d{1,3})$/);
  if (canDialog && m && byN.has(m[1])) open(byN.get(m[1]));
})();
