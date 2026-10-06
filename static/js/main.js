(() => {
  "use strict";

  const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

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

  /* ------------------------------------------------------------------
     Barra de cotação no celular: aparece depois do hero,
     some quando o formulário está na tela
     ------------------------------------------------------------------ */
  const barra = document.getElementById("cta-bar");
  const hero = document.querySelector(".hero");
  const secaoCotacao = document.getElementById("cotacao");
  if (barra && hero && secaoCotacao && "IntersectionObserver" in window) {
    let heroVisivel = true;
    let formVisivel = false;
    const atualizarBarra = () => barra.classList.toggle("is-visible", !heroVisivel && !formVisivel);
    new IntersectionObserver(([e]) => { heroVisivel = e.isIntersecting; atualizarBarra(); }, { threshold: 0 }).observe(hero);
    new IntersectionObserver(([e]) => { formVisivel = e.isIntersecting; atualizarBarra(); }, { threshold: 0.1 }).observe(secaoCotacao);
  }

  /* ------------------------------------------------------------------
     Mesa de conferência (demo do hero)
     Roda sozinha uma vez quando aparece na tela e pode ser refeita.
     ------------------------------------------------------------------ */
  const mesa = document.getElementById("desk");
  if (mesa) {
    const linhas = [...mesa.querySelectorAll(".guia")];
    const botao = document.getElementById("desk-run");
    const totalOk = document.getElementById("total-ok");
    const totalRisco = document.getElementById("total-risk");
    const barraProgresso = document.getElementById("desk-bar");
    const esperar = (ms) => new Promise((r) => setTimeout(r, reduzirMovimento ? 0 : ms));
    let rodando = false;

    const textos = {
      pending: "Aguardando conferência",
      checking: "Conferindo…",
      ok: "Conferida",
      erro: "Corrigir antes de enviar",
    };

    const definirEstado = (linha, estado) => {
      linha.dataset.state = estado;
      linha.querySelector("[data-status]").textContent = textos[estado];
    };

    const atualizarTotais = (ok, risco, feitas) => {
      totalOk.textContent = brl.format(ok);
      totalRisco.textContent = brl.format(risco);
      barraProgresso.style.width = `${(feitas / linhas.length) * 100}%`;
    };

    const zerar = () => {
      linhas.forEach((l) => {
        definirEstado(l, "pending");
        l.querySelector("[data-motivo-texto]").textContent = "";
      });
      atualizarTotais(0, 0, 0);
    };

    async function rodar() {
      if (rodando) return;
      rodando = true;
      botao.disabled = true;
      zerar();
      await esperar(300);

      let ok = 0;
      let risco = 0;
      for (let i = 0; i < linhas.length; i++) {
        const linha = linhas[i];
        definirEstado(linha, "checking");
        await esperar(650);

        const valor = parseFloat(linha.dataset.valor);
        if (linha.dataset.resultado === "erro") {
          risco += valor;
          linha.querySelector("[data-motivo-texto]").textContent = linha.dataset.motivo;
          definirEstado(linha, "erro");
        } else {
          ok += valor;
          definirEstado(linha, "ok");
        }
        atualizarTotais(ok, risco, i + 1);
      }

      botao.textContent = "Refazer simulação";
      botao.disabled = false;
      rodando = false;
    }

    botao.addEventListener("click", rodar);

    if ("IntersectionObserver" in window) {
      const observador = new IntersectionObserver((entradas) => {
        if (entradas.some((e) => e.isIntersecting)) {
          observador.disconnect();
          setTimeout(rodar, reduzirMovimento ? 0 : 500);
        }
      }, { threshold: 0.35 });
      observador.observe(mesa);
    }
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
          status.textContent = "Recebemos seu pedido de cotação. Entraremos em contato em breve.";
          status.className = "form__status is-ok";
          form.reset();
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
