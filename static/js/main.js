(() => {
  "use strict";

  /* ------------------------------------------------------------------
     Cabeçalho: borda ao rolar e menu no celular
     ------------------------------------------------------------------ */
  const cabecalho = document.querySelector(".site-header");
  if (cabecalho) {
    const atualizar = () => cabecalho.classList.toggle("is-scrolled", window.scrollY > 8);
    atualizar();
    window.addEventListener("scroll", atualizar, { passive: true });
  }

  const botaoMenu = document.getElementById("nav-toggle");
  const menu = document.getElementById("nav");
  if (botaoMenu && menu) {
    const alternar = (abrir) => {
      menu.classList.toggle("is-open", abrir);
      botaoMenu.setAttribute("aria-expanded", String(abrir));
      botaoMenu.querySelector(".sr-only").textContent = abrir ? "Fechar menu" : "Abrir menu";
    };
    botaoMenu.addEventListener("click", () => alternar(botaoMenu.getAttribute("aria-expanded") !== "true"));
    menu.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => alternar(false)));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && menu.classList.contains("is-open")) {
        alternar(false);
        botaoMenu.focus();
      }
    });
    window.matchMedia("(min-width: 921px)").addEventListener("change", (e) => { if (e.matches) alternar(false); });
  }

  /* Carrosséis compactos nos cards: rolagem suave e controles por toque/clique. */
  document.querySelectorAll("[data-carousel]").forEach((carrossel) => {
    const trilha = carrossel.querySelector(".carousel__track");
    const anterior = carrossel.querySelector("[data-carousel-prev]");
    const proximo = carrossel.querySelector("[data-carousel-next]");
    if (!trilha || !anterior || !proximo) return;
    const mover = (direcao) => {
      const cartao = trilha.querySelector(":scope > li, :scope > .operations-card");
      const distancia = cartao ? cartao.getBoundingClientRect().width + 16 : trilha.clientWidth * 0.8;
      trilha.scrollBy({ left: direcao * distancia, behavior: "smooth" });
    };
    anterior.addEventListener("click", () => mover(-1));
    proximo.addEventListener("click", () => mover(1));
  });

  /* ------------------------------------------------------------------
     Barra de contato no celular: aparece depois do hero,
     some quando o formulário está na tela
     ------------------------------------------------------------------ */
  const barra = document.getElementById("cta-bar");
  const hero = document.querySelector(".hero");
  const secaoContato = document.getElementById("conversa");
  if (barra && hero && secaoContato && "IntersectionObserver" in window) {
    let heroVisivel = true;
    let formVisivel = false;
    const atualizarBarra = () => barra.classList.toggle("is-visible", !heroVisivel && !formVisivel);
    new IntersectionObserver(([e]) => { heroVisivel = e.isIntersecting; atualizarBarra(); }, { threshold: 0 }).observe(hero);
    new IntersectionObserver(([e]) => { formVisivel = e.isIntersecting; atualizarBarra(); }, { threshold: 0.1 }).observe(secaoContato);
  }

  /* ------------------------------------------------------------------
     Formulário de cotação
     ------------------------------------------------------------------ */
  const form = document.getElementById("form-cotacao");
  if (form) {
    const status = document.getElementById("form-status");
    const enviar = document.getElementById("form-enviar");
    const campoZap = form.elements["whatsapp"];
    const caixasInteresse = [...form.querySelectorAll('input[name="interesse"]')];

    document.querySelectorAll("[data-interesse]").forEach((link) => {
      link.addEventListener("click", () => {
        const alvo = caixasInteresse.find((caixa) => caixa.value === link.dataset.interesse);
        if (alvo) {
          caixasInteresse.forEach((caixa) => { caixa.checked = caixa === alvo; });
        }
      });
    });

    // "Ainda não sei" é exclusivo
    caixasInteresse.forEach((c) => {
      c.addEventListener("change", () => {
        if (!c.checked) return;
        caixasInteresse.forEach((outra) => {
          if (outra === c) return;
          if (c.value === "indefinido" || outra.value === "indefinido") outra.checked = false;
        });
      });
    });

    // Máscara simples: (62) 91234-5678
    campoZap.addEventListener("input", () => {
      const d = campoZap.value.replace(/\D/g, "").slice(0, 11);
      let t = d;
      if (d.length > 10) t = `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
      else if (d.length > 6) t = `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
      else if (d.length > 2) t = `(${d.slice(0, 2)}) ${d.slice(2)}`;
      else if (d.length > 0) t = `(${d}`;
      campoZap.value = t;
    });

    const limparErros = () => {
      form.querySelectorAll("[data-error-for]").forEach((p) => { p.textContent = ""; });
      form.querySelectorAll("[aria-invalid]").forEach((i) => i.removeAttribute("aria-invalid"));
      status.textContent = "";
      status.className = "form__status";
    };

    const mostrarErros = (erros) => {
      let primeiro = null;
      Object.entries(erros).forEach(([campo, mensagem]) => {
        const alvo = form.querySelector(`[data-error-for="${campo}"]`);
        const entrada = form.elements[campo];
        if (alvo) alvo.textContent = mensagem;
        if (entrada) {
          entrada.setAttribute("aria-invalid", "true");
          if (!primeiro) primeiro = entrada;
        }
      });
      if (primeiro) primeiro.focus();
    };

    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      limparErros();

      const dados = Object.fromEntries(new FormData(form).entries());
      dados.interesse = caixasInteresse.filter((c) => c.checked).map((c) => c.value);
      dados.consentimento = form.elements["consentimento"].checked;

      enviar.disabled = true;
      const rotulo = enviar.textContent;
      enviar.textContent = "Enviando…";

      try {
        const resposta = await fetch("/contato", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(dados),
        });
        const resultado = await resposta.json().catch(() => ({}));

        if (resposta.ok && resultado.ok) {
          if (resultado.whatsapp_link) {
            status.textContent = "Dados registrados. O WhatsApp abrirá com a mensagem pronta; revise e toque em enviar para falar com a Balestra.";
            status.className = "form__status is-ok";
            window.location.assign(resultado.whatsapp_link);
          } else {
            status.textContent = "Dados registrados, mas o WhatsApp ainda não está configurado. Tente novamente mais tarde.";
            status.className = "form__status is-error";
          }
        } else if (resultado.erros) {
          mostrarErros(resultado.erros);
          status.textContent = "Revise os campos destacados e envie de novo.";
          status.className = "form__status is-error";
        } else {
          status.textContent = resultado.erro || "Não foi possível enviar agora. Tente novamente em instantes.";
          status.className = "form__status is-error";
        }
      } catch (e) {
        status.textContent = "Não foi possível enviar agora. Verifique a conexão e tente de novo.";
        status.className = "form__status is-error";
      } finally {
        enviar.disabled = false;
        enviar.textContent = rotulo;
      }
    });
  }
})();
