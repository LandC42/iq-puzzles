"use strict";

// Просмотр задачи крупно: открытие по клику на карточку, листание, показ ответа.
// Без JS карточки остаются обычными ссылками на картинку.
(function () {
  const cards = Array.from(document.querySelectorAll(".card"));
  const dlg = document.getElementById("viewer");
  if (!cards.length || !dlg || typeof dlg.showModal !== "function") return;

  const img = document.getElementById("v-img");
  const title = document.getElementById("v-title");
  const toggle = document.getElementById("v-toggle");
  const answer = document.getElementById("v-answer");
  let index = 0;
  let revealed = false;

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function render() {
    const card = cards[index];
    const n = card.dataset.n;
    img.src = "img/" + pad(n) + (revealed ? "_solution.svg" : "_task.svg");
    img.alt = "Задача " + n + (revealed ? ", решение" : "");
    title.textContent = "Задача " + n;
    toggle.textContent = revealed ? "Скрыть ответ" : "Показать ответ";
    toggle.setAttribute("aria-expanded", String(revealed));

    answer.replaceChildren();
    if (revealed) {
      const strong = document.createElement("strong");
      strong.textContent = "Ответ: " + card.dataset.answer + ". ";
      answer.append(strong, document.createTextNode(card.dataset.expl || ""));
    }
    answer.hidden = !revealed;
    history.replaceState(null, "", "#" + n);
  }

  function show(i) {
    index = (i + cards.length) % cards.length;
    revealed = false;
    render();
  }

  function open(i) {
    show(i);
    if (!dlg.open) dlg.showModal();
  }

  cards.forEach(function (card, i) {
    card.addEventListener("click", function (e) {
      e.preventDefault();
      open(i);
    });
  });

  toggle.addEventListener("click", function () {
    revealed = !revealed;
    render();
  });
  document.getElementById("v-prev").addEventListener("click", function () { show(index - 1); });
  document.getElementById("v-next").addEventListener("click", function () { show(index + 1); });
  document.getElementById("v-close").addEventListener("click", function () { dlg.close(); });

  // клик по затемнению вокруг окна закрывает его
  dlg.addEventListener("click", function (e) {
    if (e.target === dlg) dlg.close();
  });

  dlg.addEventListener("close", function () {
    history.replaceState(null, "", location.pathname + location.search);
    cards[index].focus();
  });

  document.addEventListener("keydown", function (e) {
    if (!dlg.open) return;
    if (e.key === "ArrowLeft") show(index - 1);
    else if (e.key === "ArrowRight") show(index + 1);
  });

  // свайп влево/вправо на телефоне
  let startX = null;
  let startY = null;
  const area = document.querySelector(".viewer-img");
  area.addEventListener("touchstart", function (e) {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
  }, { passive: true });
  area.addEventListener("touchend", function (e) {
    if (startX === null) return;
    const dx = e.changedTouches[0].clientX - startX;
    const dy = e.changedTouches[0].clientY - startY;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) show(index + (dx < 0 ? 1 : -1));
    startX = null;
  }, { passive: true });

  // прямая ссылка на задачу: …/#12
  const m = location.hash.match(/^#(\d{1,3})$/);
  if (m) {
    const i = cards.findIndex(function (c) { return c.dataset.n === m[1]; });
    if (i >= 0) open(i);
  }
})();
