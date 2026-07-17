"use strict";

/* ---------- nav: scroll state + mobile menu ---------- */
(function initNav() {
  const nav = document.getElementById("nav");
  const hamburger = document.getElementById("hamburger");
  const navLinks = document.getElementById("navLinks");

  const onScroll = () => {
    nav.classList.toggle("scrolled", window.scrollY > 20);
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  hamburger.addEventListener("click", () => {
    const open = navLinks.classList.toggle("open");
    hamburger.classList.toggle("open", open);
    hamburger.setAttribute("aria-expanded", String(open));
  });

  navLinks.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      navLinks.classList.remove("open");
      hamburger.classList.remove("open");
      hamburger.setAttribute("aria-expanded", "false");
    });
  });
})();

/* ---------- typing effect ---------- */
(function initTyping() {
  const el = document.getElementById("typingText");
  if (!el) return;

  // Types out a single title and stops — no delete/cycle to other roles.
  const WORD = "Data Engineer Sr.";
  const TYPE_SPEED = 80;

  let charIndex = 0;

  function tick() {
    charIndex++;
    el.textContent = WORD.slice(0, charIndex);
    if (charIndex < WORD.length) setTimeout(tick, TYPE_SPEED);
  }

  tick();
})();

/* ---------- scroll reveal ---------- */
(function initReveal() {
  const items = document.querySelectorAll(".reveal");
  if (!items.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
  );

  items.forEach((item) => observer.observe(item));
})();

/* ---------- animated counters ---------- */
(function initCounters() {
  const counters = document.querySelectorAll(".metric-num");
  if (!counters.length) return;

  const DURATION_MS = 1200;

  function animateCounter(el) {
    const target = parseInt(el.dataset.target, 10) || 0;
    const suffix = el.dataset.suffix || "";
    const start = performance.now();

    function frame(now) {
      const progress = Math.min((now - start) / DURATION_MS, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(eased * target);
      el.textContent = value + suffix;
      if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );

  counters.forEach((el) => observer.observe(el));
})();

/* ---------- architecture modal ---------- */
(function initArchModal() {
  const overlay = document.getElementById("archOverlay");
  if (!overlay) return;

  const openButtons = document.querySelectorAll("[data-arch-open]");
  const panels = overlay.querySelectorAll(".arch-panel");

  function openPanel(id) {
    panels.forEach((panel) => panel.classList.toggle("open", panel.id === id));
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeOverlay() {
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }

  openButtons.forEach((btn) => {
    btn.addEventListener("click", () => openPanel(btn.dataset.archOpen));
  });

  overlay.querySelectorAll("[data-arch-close]").forEach((btn) => {
    btn.addEventListener("click", closeOverlay);
  });

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeOverlay();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.classList.contains("open")) closeOverlay();
  });
})();

/* ---------- cursor glow (desktop only) ---------- */
(function initCursorGlow() {
  const glow = document.getElementById("cursorGlow");
  const hero = document.querySelector(".hero");
  if (!glow || !hero) return;

  const isDesktop = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (!isDesktop) return;

  hero.addEventListener("mousemove", (e) => {
    glow.style.opacity = "1";
    glow.style.transform = `translate(${e.clientX}px, ${e.clientY}px) translate(-50%, -50%)`;
  });
  hero.addEventListener("mouseleave", () => {
    glow.style.opacity = "0";
  });
})();
