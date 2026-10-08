/*
 * Front-end da grade horária (Equipe 02).
 *
 * Toda a grade vem do grafo em memória no back-end (/api/grade):
 *   - cada sessão de aula é um vértice; a "cor" do vértice são as faixas que ele ocupa;
 *   - /api/grade?passo=k devolve só os k primeiros vértices coloridos
 *     (sem cor = grade vazia, parcial, completa);
 *   - mover uma aula na tela chama /api/grade/mover: o vértice troca de cor no grafo
 *     e os conflitos com os vizinhos voltam recalculados.
 */
(function () {
  "use strict";

  const LETRAS = "ABCDEFGHIJKL";
  const PALETA = ["#B5654A", "#5B7553", "#8A6D2F", "#3E6A8A", "#7B5EA7", "#A2486B",
                  "#2F7B7A", "#9C5B2E", "#4F5B93", "#6B7A2F", "#8C4A4A", "#3F6B46"];
  const SIGLAS = new Set(["TIC", "DCEXT", "II", "I", "IHC", "2", "1"]);
  const MINUSCULAS = new Set(["de", "da", "do", "das", "dos", "e", "a", "o", "para", "em"]);
  const MOTIVOS = {
    perfil_pleno: "mesmo período",
    professor: "mesmo professor",
    professor_e_perfil_pleno: "mesmo professor e período",
    mesma_aula: "mesma disciplina",
  };

  const st = {
    dados: null,
    grade: null,          // estado completo da grade em memória
    passos: null,         // estado parcial (aba Gerar grade)
    passo: 0,
    tocando: null,
    visao: "periodo",
    periodo: 5,
    professor: null,
    selecionada: null,
    recente: null,
    recorte: "periodo",
    periodoGrafo: 5,
    professorGrafo: null,
    grafo: null,
    relatorio: null,
  };

  const $ = (sel, raiz) => (raiz || document).querySelector(sel);
  const $$ = (sel, raiz) => Array.from((raiz || document).querySelectorAll(sel));

  // ------------------------------------------------------------ utilidades --
  async function api(caminho, opcoes) {
    const r = await fetch("/api" + caminho, Object.assign({ headers: { "Content-Type": "application/json" } }, opcoes));
    const corpo = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(corpo.detail || `Erro ${r.status} em ${caminho}`);
    return corpo;
  }
  const post = (caminho, corpo) => api(caminho, { method: "POST", body: JSON.stringify(corpo || {}) });

  function el(tag, attrs, ...filhos) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") e.className = v;
      else if (k === "style") e.setAttribute("style", v);
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (k === "html") e.innerHTML = v;
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const f of filhos.flat()) if (f !== null && f !== undefined && f !== false) e.append(f.nodeType ? f : document.createTextNode(f));
    return e;
  }

  function titulo(texto) {
    return String(texto || "").toLowerCase().split(/(\s+|-)/).map((p, i) => {
      const cima = p.toUpperCase();
      if (SIGLAS.has(cima)) return cima;
      if (i > 0 && MINUSCULAS.has(p)) return p;
      return p.charAt(0).toUpperCase() + p.slice(1);
    }).join("");
  }

  function nomeCurto(nome) {
    const partes = titulo(nome).split(" ").filter(p => !MINUSCULAS.has(p.toLowerCase()));
    return partes.length > 1 ? `${partes[0]} ${partes[partes.length - 1]}` : partes[0] || "";
  }

  function rgba(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
  }

  function avisar(msg, erro) {
    const a = $("#aviso");
    a.textContent = msg;
    a.className = "aviso" + (erro ? " erro" : "");
    a.hidden = false;
    clearTimeout(avisar.t);
    avisar.t = setTimeout(() => { a.hidden = true; }, erro ? 6000 : 3800);
  }

  const nomeDia = d => (st.dados.dias.find(x => x.dia === d) || {}).nome || d;
  const faixa = l => st.dados.faixas.find(f => f.faixa === l);

  function intervaloTexto(rotulos) {
    if (!rotulos.length) return "sem horário";
    const dia = +rotulos[0][0], ini = faixa(rotulos[0][1]), fim = faixa(rotulos[rotulos.length - 1][1]);
    return `${nomeDia(dia)} ${ini.inicio}–${fim.fim} (${rotulos.join(" ")})`;
  }

  // ------------------------------------------------------------- filtros --
  function sessoesFiltradas(estado, visao, valor) {
    if (!estado) return [];
    return estado.sessoes.filter(s => (visao === "periodo" ? s.periodo === valor : s.pro_id === valor));
  }

  function coresPorDisciplina(sessoes) {
    const codigos = Array.from(new Set(sessoes.map(s => s.codigo))).sort();
    return new Map(codigos.map((c, i) => [c, PALETA[i % PALETA.length]]));
  }

  // ---------------------------------------------------- desenho da grade --
  function desenharGrade(alvo, sessoes, opcoes) {
    const { cores, visao, editavel } = opcoes;
    alvo.innerHTML = "";
    alvo.append(el("div", { class: "cab" }, "Horário"));
    for (const d of st.dados.dias) alvo.append(el("div", { class: "cab" }, d.nome));

    const horas = el("div", { class: "horas" });
    for (const f of st.dados.faixas) {
      horas.append(el("div", { class: "hora" + (f.faixa === "G" ? " almoco" : "") }, el("b", {}, f.faixa), `${f.inicio}–${f.fim}`));
    }
    alvo.append(horas);

    for (const d of st.dados.dias) {
      const coluna = el("div", { class: "dia", "data-dia": d.dia });
      for (const f of st.dados.faixas) coluna.append(el("div", { class: "celula" + (f.faixa === "G" ? " almoco" : ""), "data-faixa": f.faixa }));

      const doDia = sessoes.filter(s => s.colorida && +s.rotulos[0][0] === d.dia)
        .map(s => ({ s, ini: LETRAS.indexOf(s.rotulos[0][1]), fim: LETRAS.indexOf(s.rotulos[s.rotulos.length - 1][1]) + 1 }))
        .sort((a, b) => a.ini - b.ini || b.fim - a.fim);

      // Faixas paralelas: aulas que se sobrepõem no mesmo dia ficam lado a lado
      // (coloração gulosa de um grafo de intervalos).
      const fimFaixa = [];
      for (const x of doDia) {
        let faixaLivre = fimFaixa.findIndex(f => f <= x.ini);
        if (faixaLivre < 0) { faixaLivre = fimFaixa.length; fimFaixa.push(0); }
        fimFaixa[faixaLivre] = x.fim;
        x.raia = faixaLivre;
      }
      for (const x of doDia) {
        const sobrepostas = doDia.filter(y => y.ini < x.fim && x.ini < y.fim);
        x.raias = Math.max(...sobrepostas.map(y => y.raia)) + 1;
      }

      for (const x of doDia) {
        const s = x.s, cor = cores.get(s.codigo) || PALETA[0];
        const conflito = s.conflito_com.length > 0;
        const largura = 100 / x.raias;
        const bloco = el("button", {
          class: "aula" + (conflito ? " conflito" : "") + (st.selecionada === s.id ? " selecionada" : "") + (st.recente === s.id ? " recente" : ""),
          type: "button",
          draggable: editavel ? "true" : null,
          "data-sessao": s.id,
          title: `${titulo(s.disciplina)} · ${intervaloTexto(s.rotulos)}`,
          style: `--cor:${cor};--fundo:${rgba(cor, .1)};top:calc(${x.ini} * var(--altura-faixa) + 2px);` +
                 `height:calc(${x.fim - x.ini} * var(--altura-faixa) - 4px);left:calc(${x.raia * largura}% + 3px);width:calc(${largura}% - 6px);`,
          onclick: () => abrirDetalhe(s.id),
        },
        el("span", { class: "nome" }, titulo(s.disciplina)),
        el("span", { class: "meta" }, `${s.codigo} · ${s.rotulos[0]}–${s.rotulos[s.rotulos.length - 1]}`),
        el("span", { class: "meta" }, visao === "periodo" ? nomeCurto(s.professor) : `${s.periodo}º período${s.eletiva ? " · eletiva" : ""}`));
        if (editavel) {
          bloco.addEventListener("dragstart", ev => { ev.dataTransfer.setData("text/plain", s.id); bloco.classList.add("arrastando"); });
          bloco.addEventListener("dragend", () => bloco.classList.remove("arrastando"));
        }
        coluna.append(bloco);
      }

      if (editavel) {
        const faixaSob = ev => {
          const r = coluna.getBoundingClientRect();
          const i = Math.floor((ev.clientY - r.top) / (r.height / LETRAS.length));
          return LETRAS[Math.max(0, Math.min(LETRAS.length - 1, i))];
        };
        coluna.addEventListener("dragover", ev => {
          ev.preventDefault();
          coluna.classList.add("alvo");
          const f = faixaSob(ev);
          $$(".celula", coluna).forEach(c => c.classList.toggle("sobre", c.dataset.faixa === f));
        });
        coluna.addEventListener("dragleave", () => { coluna.classList.remove("alvo"); $$(".celula", coluna).forEach(c => c.classList.remove("sobre")); });
        coluna.addEventListener("drop", ev => {
          ev.preventDefault();
          coluna.classList.remove("alvo");
          $$(".celula", coluna).forEach(c => c.classList.remove("sobre"));
          moverSessao(ev.dataTransfer.getData("text/plain"), d.dia, faixaSob(ev));
        });
      }
      alvo.append(coluna);
    }
  }

  function desenharLegenda(alvo, cores, sessoes) {
    alvo.innerHTML = "";
    const nomes = new Map(sessoes.map(s => [s.codigo, s.disciplina]));
    for (const [codigo, cor] of cores) {
      alvo.append(el("span", { class: "chip" }, el("i", { style: `background:${cor}` }), titulo(nomes.get(codigo))));
    }
  }

  function desenharFaixaStatus(alvo, sessoes, rotuloVazio) {
    const coloridas = sessoes.filter(s => s.colorida);
    const emConflito = coloridas.filter(s => s.conflito_com.length);
    if (!coloridas.length) {
      alvo.className = "faixa-status vazio";
      alvo.textContent = rotuloVazio;
    } else if (emConflito.length) {
      alvo.className = "faixa-status conflito";
      alvo.textContent = `${emConflito.length} aula${emConflito.length > 1 ? "s" : ""} com conflito de horário`;
    } else {
      alvo.className = "faixa-status sucesso";
      alvo.textContent = "Sem conflitos nesta grade";
    }
  }

  // ------------------------------------------------------------ aba grade --
  function valorFiltro() { return st.visao === "periodo" ? st.periodo : st.professor; }

  function renderGrade() {
    const sessoes = sessoesFiltradas(st.grade, st.visao, valorFiltro());
    const cores = coresPorDisciplina(sessoes);
    desenharLegenda($("#legenda"), cores, sessoes);
    const quem = st.visao === "periodo" ? "este período" : "este professor";
    desenharFaixaStatus($("#faixa-status"), sessoes, `Nenhuma aula alocada para ${quem} — grade em aberto.`);
    desenharGrade($("#grade"), sessoes, { cores, visao: st.visao, editavel: true });
    renderOrigem();
  }

  function renderOrigem() {
    if (!st.grade) return;
    $("#origem-texto").textContent = st.grade.origem;
    $("#origem-editada").hidden = !st.grade.editada;
  }

  function trocarVisao(visao) {
    st.visao = visao;
    $$("[data-visao]").forEach(b => b.classList.toggle("ativo", b.dataset.visao === visao));
    $("#sel-periodo").closest(".campo").hidden = visao !== "periodo";
    $("#sel-professor").closest(".campo").hidden = visao !== "professor";
    fecharDetalhe();
    renderGrade();
  }

  // --------------------------------------------------------- detalhe aula --
  function abrirDetalhe(id) {
    const s = st.grade.sessoes.find(x => x.id === id);
    if (!s) return;
    st.selecionada = id;
    $$(".aula").forEach(b => b.classList.toggle("selecionada", b.dataset.sessao === id));
    const conflito = s.conflito_com.length > 0;
    const tag = $("#detalhe-estado");
    tag.className = "tag " + (conflito ? "tag-conflito" : "tag-sucesso");
    tag.textContent = conflito ? "Conflito de horário" : "Aula alocada";

    const porId = new Map(st.grade.sessoes.map(x => [x.id, x]));
    const conflitos = st.grade.conflitos.filter(c => c.a === id || c.b === id).map(c => {
      const outra = porId.get(c.a === id ? c.b : c.a);
      return el("li", {}, `${outra.codigo} ${titulo(outra.disciplina)} (${MOTIVOS[c.motivo] || c.motivo}) em ${c.horarios.join(", ")}`);
    });

    const selDia = el("select", { "aria-label": "Dia" }, st.dados.dias.map(d => el("option", { value: d.dia, selected: d.dia === +s.rotulos[0][0] }, d.nome)));
    const selFaixa = el("select", { "aria-label": "Faixa inicial" }, st.dados.faixas.map(f => el("option", { value: f.faixa, selected: f.faixa === s.rotulos[0][1] }, `${f.faixa} · ${f.inicio}`)));

    $("#detalhe-corpo").replaceChildren(...[
      el("h3", {}, titulo(s.disciplina)),
      el("div", { class: "subtitulo" }, `${s.codigo} · ${s.periodo}º período${s.eletiva ? " · eletiva" : ""}`),
      el("dl", {},
        el("dt", {}, "Professor"), el("dd", {}, titulo(s.professor)),
        el("dt", {}, "Horário"), el("dd", {}, intervaloTexto(s.rotulos)),
        el("dt", {}, "Vértice"), el("dd", {}, `sessão ${s.id} · ${s.faixas} faixas`),
        el("dt", {}, "Coloração"), el("dd", {}, `${s.passo}º vértice colorido`)),
      conflito ? el("div", {}, el("b", {}, "Choques com vizinhos no grafo:"), el("ul", { class: "conflitos" }, conflitos)) : null,
      el("div", { class: "mover" },
        el("label", { class: "campo campo-largo" }, el("span", {}, "Mover para"), selDia),
        el("label", { class: "campo campo-largo" }, el("span", {}, "a partir da faixa"), selFaixa),
        el("button", { class: "botao botao-primario", onclick: () => moverSessao(id, +selDia.value, selFaixa.value) }, "Mover")),
    ].filter(Boolean));
    $("#detalhe").hidden = false;
  }

  function fecharDetalhe() {
    st.selecionada = null;
    $("#detalhe").hidden = true;
    $$(".aula.selecionada").forEach(b => b.classList.remove("selecionada"));
  }

  async function moverSessao(id, dia, letra) {
    if (!id) return;
    try {
      const r = await post("/grade/mover", { sessao: id, dia, faixa: letra });
      st.grade = r;
      st.recente = id;
      const s = r.sessoes.find(x => x.id === id);
      const n = r.conflitos_da_sessao.length;
      avisar(`Vértice ${id} trocou de cor: agora ${s.rotulos.join(" ")}. ` +
             (n ? `${n} conflito${n > 1 ? "s" : ""} com vizinhos.` : "Sem conflitos com os vizinhos."), n > 0);
      renderGrade();
      if (st.selecionada === id) abrirDetalhe(id);
      st.recente = null;
      atualizarGerar(true);
    } catch (e) {
      avisar(e.message, true);
    }
  }

  // ------------------------------------------------------------ aba gerar --
  function metricas(alvo, itens) {
    alvo.replaceChildren(...itens.map(([valor, rotulo]) => el("div", { class: "metrica" }, el("b", {}, String(valor)), el("span", {}, rotulo))));
  }

  async function gerar() {
    const botao = $("#btn-gerar");
    botao.disabled = true;
    try {
      parar();
      st.grade = await post("/grade/gerar", { ordem: $("#sel-ordem").value });
      fecharDetalhe();
      renderGrade();
      await atualizarGerar(false);
      await irParaPasso(0);
      avisar(`Grade gerada: ${st.grade.resumo.sessoes} vértices coloridos, ${st.grade.resumo.conflitos} conflitos. Use ▶ para ver a coloração passo a passo.`);
    } catch (e) {
      avisar(e.message, true);
    } finally {
      botao.disabled = false;
    }
  }

  async function atualizarGerar(manterPasso) {
    const g = st.grade;
    metricas($("#metricas"), [
      [g.resumo.sessoes, "vértices (sessões)"], [g.resumo.arestas, "arestas (conflitos possíveis)"],
      [g.resumo.cores_usadas, "cores (blocos) usadas"], [g.resumo.conflitos, "choques na grade"],
    ]);
    const rng = $("#rng-passo");
    rng.max = g.total_passos;
    if (!manterPasso) st.passo = g.total_passos;
    rng.value = st.passo;
    try {
      const [a, s] = await Promise.all([api("/grafo/coloracao?nivel=alocacoes"), api("/grafo/coloracao?nivel=sessoes")]);
      $("#otimalidade").innerHTML =
        `<b>Coloração pura com o DSATUR da equipe.</b> Grafo de alocações: ${a.numero_de_cores} cores para ${a.vertices} vértices; ` +
        `grafo de sessões: ${s.numero_de_cores} cores. A maior clique tem ${s.maior_clique} vértices (todos precisam de cores diferentes), ` +
        `então ${s.otima ? "a coloração é <b>ótima</b>: usa o número cromático χ(G)." : "a coloração está acima do limite inferior."}`;
    } catch (e) { /* métrica opcional */ }
    if (manterPasso) await irParaPasso(st.passo);
  }

  async function irParaPasso(k) {
    if (!st.grade) return;
    st.passo = Math.max(0, Math.min(k, st.grade.total_passos));
    $("#rng-passo").value = st.passo;
    st.passos = await api(`/grade?passo=${st.passo}`);
    renderPassos();
  }

  function renderPassos() {
    const e = st.passos, total = e.total_passos;
    const periodo = +$("#sel-periodo-passos").value;
    const sessoes = sessoesFiltradas(e, "periodo", periodo);
    const cores = coresPorDisciplina(sessoesFiltradas(st.grade, "periodo", periodo));
    const ultimo = e.sessoes.find(s => s.passo === e.passo && s.colorida);
    $("#passo-rotulo").textContent = `Passo ${e.passo} de ${total}` +
      (ultimo ? ` · último vértice colorido: ${ultimo.codigo} (${ultimo.id}) → ${ultimo.rotulos.join(" ")}` : "");

    $("#progresso-periodos").replaceChildren(...st.dados.periodos.map(p => {
      const doPeriodo = e.sessoes.filter(s => s.periodo === p);
      const feitas = doPeriodo.filter(s => s.colorida).length;
      return el("button", {
        class: p === periodo ? "ativo" : null, type: "button", title: `${p}º período: ${feitas} de ${doPeriodo.length} sessões coloridas`,
        onclick: () => { $("#sel-periodo-passos").value = p; renderPassos(); },
      }, `${p}º · ${feitas}/${doPeriodo.length}`, el("span", { class: "barra-prog" }, el("i", { style: `width:${doPeriodo.length ? (100 * feitas / doPeriodo.length) : 0}%` })));
    }));

    const faixa = $("#faixa-passos");
    if (e.situacao === "vazia") {
      faixa.className = "faixa-status vazio";
      faixa.textContent = "Grafo sem cor: nenhum vértice tem horário, então a grade está vazia.";
    } else if (e.situacao === "parcial") {
      faixa.className = "faixa-status parcial";
      faixa.textContent = `Grafo parcialmente colorido (${e.resumo.coloridas} de ${total} vértices): grade parcial. ` +
        `${sessoes.filter(s => s.colorida).length} de ${sessoes.length} sessões do ${periodo}º período já têm horário.`;
    } else if (e.resumo.conflitos) {
      faixa.className = "faixa-status conflito";
      faixa.textContent = `Grafo totalmente colorido, mas com ${e.resumo.conflitos} aresta(s) em conflito.`;
    } else {
      faixa.className = "faixa-status sucesso";
      faixa.textContent = "Grafo totalmente colorido: grade completa e sem conflitos.";
    }
    desenharGrade($("#grade-passos"), sessoes, { cores, visao: "periodo", editavel: false });
  }

  function tocar() {
    if (st.tocando) return parar();
    if (st.passo >= st.grade.total_passos) st.passo = 0;
    $("#btn-tocar").textContent = "⏸";
    st.tocando = setInterval(async () => {
      if (st.passo >= st.grade.total_passos) return parar();
      await irParaPasso(st.passo + 1);
    }, 260);
  }

  function parar() {
    clearInterval(st.tocando);
    st.tocando = null;
    $("#btn-tocar").textContent = "▶";
  }

  async function salvar() {
    const semestre = $("#inp-semestre").value.trim();
    if (!semestre) return avisar("Informe o semestre.", true);
    const jaExiste = st.dados.semestres.some(s => s.semestre === semestre);
    if (jaExiste && !confirm(`Já existe uma grade gravada para ${semestre}. Substituir?`)) return;
    try {
      const r = await post("/grade/salvar", { semestre });
      st.dados.semestres = r.semestres;
      st.grade.origem = `Banco: grade ${semestre}`;
      st.grade.editada = false;
      renderOrigem();
      renderSemestres();
      const msg = $("#msg-salvar");
      msg.hidden = false;
      msg.textContent = `${r.linhas} linhas gravadas em GRA_GRADE_HORARIA (semestre ${r.semestre}), ${r.conflitos} conflitos.`;
      avisar(`Grade salva no banco: ${semestre}.`);
    } catch (e) {
      avisar(e.message, true);
    }
  }

  function renderSemestres() {
    const lista = $("#lista-semestres");
    lista.replaceChildren(...st.dados.semestres.map(s => el("li", {},
      el("span", {}, el("b", {}, s.semestre), " ", el("small", {}, `${s.linhas} linhas${s.semestre === "2026.2" ? " · grade atual (carga)" : ""}`)),
      el("button", { class: "botao", onclick: () => carregar(s.semestre) }, "Carregar"))));
  }

  async function carregar(semestre) {
    try {
      parar();
      st.grade = await post("/grade/carregar", { semestre });
      fecharDetalhe();
      renderGrade();
      await atualizarGerar(false);
      await irParaPasso(st.grade.total_passos);
      avisar(`Grafo instanciado a partir da grade ${semestre} do banco.`);
    } catch (e) {
      avisar(e.message, true);
    }
  }

  // ------------------------------------------------------------ aba grafo --
  async function renderGrafo() {
    st.grafo = await api("/grafo");
    const g = st.grafo;
    const porId = new Map(g.vertices.map(v => [v.id, v]));
    const sessoes = new Map(st.grade.sessoes.map(s => [s.id, s]));
    const dentro = new Set(g.vertices.filter(v => {
      const s = sessoes.get(v.id);
      return st.recorte === "periodo" ? v.periodo === st.periodoGrafo : s && s.pro_id === st.professorGrafo;
    }).map(v => v.id));
    const vizinhos = new Map();
    for (const a of g.arestas) {
      for (const [x, y] of [[a.origem, a.destino], [a.destino, a.origem]]) {
        if (dentro.has(x) && !dentro.has(y)) vizinhos.set(y, vizinhos.get(y) || x);
      }
    }

    const W = 640, H = 520, cx = W / 2, cy = H / 2 - 4;
    const internos = Array.from(dentro).sort();
    const pos = new Map();
    const rInterno = internos.length > 1 ? Math.min(170, 40 + internos.length * 9) : 0;
    internos.forEach((id, i) => {
      const ang = -Math.PI / 2 + (2 * Math.PI * i) / Math.max(1, internos.length);
      pos.set(id, [cx + rInterno * Math.cos(ang), cy + rInterno * Math.sin(ang)]);
    });
    const externos = Array.from(vizinhos.keys()).sort((a, b) => {
      const pa = pos.get(vizinhos.get(a)), pb = pos.get(vizinhos.get(b));
      return Math.atan2(pa[1] - cy, pa[0] - cx) - Math.atan2(pb[1] - cy, pb[0] - cx);
    });
    externos.forEach((id, i) => {
      const ang = -Math.PI / 2 + (2 * Math.PI * (i + 0.5)) / Math.max(1, externos.length);
      pos.set(id, [cx + 228 * Math.cos(ang), cy + 228 * Math.sin(ang)]);
    });

    const coresBloco = new Map();
    internos.forEach(id => {
      const c = porId.get(id).cor;
      if (!coresBloco.has(c)) coresBloco.set(c, PALETA[coresBloco.size % PALETA.length]);
    });

    const svg = $("#svg-grafo");
    const ns = "http://www.w3.org/2000/svg";
    const s = (tag, attrs, texto) => {
      const e = document.createElementNS(ns, tag);
      for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
      if (texto) e.textContent = texto;
      return e;
    };
    svg.replaceChildren();
    const grupoArestas = s("g", {});
    let arestasInternas = 0, emConflito = 0;
    for (const a of g.arestas) {
      if (!pos.has(a.origem) || !pos.has(a.destino)) continue;
      const interna = dentro.has(a.origem) && dentro.has(a.destino);
      if (!interna && !dentro.has(a.origem) && !dentro.has(a.destino)) continue;
      const choque = porId.get(a.origem).cor && porId.get(a.origem).cor.split(" ").some(h => porId.get(a.destino).cor.split(" ").includes(h));
      if (interna) arestasInternas++;
      if (choque) emConflito++;
      const [x1, y1] = pos.get(a.origem), [x2, y2] = pos.get(a.destino);
      grupoArestas.append(s("line", { x1, y1, x2, y2, class: `${a.motivo}${interna ? "" : " fraca"}${choque ? " conflito" : ""}` },));
    }
    svg.append(grupoArestas);

    for (const id of [...externos, ...internos]) {
      const v = porId.get(id), [x, y] = pos.get(id), interno = dentro.has(id);
      const no = s("g", { class: "no" + (interno ? "" : " fora"), tabindex: 0, role: "button" });
      no.append(s("circle", { cx: x, cy: y, r: interno ? 15 : 9, fill: interno ? coresBloco.get(v.cor) : "#E3E6EA" }));
      no.append(s("title", {}, `${v.codigo} · sessão ${v.id} · ${v.cor || "sem cor"}`));
      no.append(s("text", { x, y: y + (interno ? 27 : 19), "text-anchor": "middle" }, interno ? v.codigo.slice(-4) : v.codigo.slice(-4)));
      no.addEventListener("click", () => detalheVertice(id));
      no.addEventListener("keydown", ev => { if (ev.key === "Enter") detalheVertice(id); });
      svg.append(no);
    }

    metricas($("#grafo-resumo"), [
      [internos.length, "vértices no recorte"], [arestasInternas, "arestas internas"],
      [coresBloco.size, "cores (blocos) distintas"], [emConflito, "arestas em conflito"],
    ]);
    $("#grafo-detalhe").innerHTML = `Maior clique do grafo inteiro: <b>${g.maior_clique}</b> vértices. ` +
      `Clique um vértice para ver vizinhos e cor. Rótulo = final do código da disciplina.`;
  }

  function detalheVertice(id) {
    const v = st.grafo.vertices.find(x => x.id === id);
    const s = st.grade.sessoes.find(x => x.id === id);
    const viz = st.grafo.arestas.filter(a => a.origem === id || a.destino === id)
      .map(a => `${(st.grafo.vertices.find(x => x.id === (a.origem === id ? a.destino : a.origem)) || {}).codigo} (${MOTIVOS[a.motivo] || a.motivo})`);
    $$("#svg-grafo .no").forEach(n => n.classList.remove("ativo"));
    $("#grafo-detalhe").innerHTML = `<b>${v.codigo} · ${titulo(s ? s.disciplina : "")}</b><br>` +
      `Sessão ${id} · cor (faixas): <b>${v.cor || "sem cor"}</b> · ${titulo(v.professor)}<br>` +
      `${viz.length} vizinhos: ${viz.slice(0, 18).join(", ")}${viz.length > 18 ? "…" : ""}`;
  }

  function trocarRecorte(recorte) {
    st.recorte = recorte;
    $$("[data-recorte]").forEach(b => b.classList.toggle("ativo", b.dataset.recorte === recorte));
    $("#sel-periodo-grafo").closest(".campo").hidden = recorte !== "periodo";
    $("#sel-professor-grafo").closest(".campo").hidden = recorte !== "professor";
    renderGrafo().catch(e => avisar(e.message, true));
  }

  // ------------------------------------------------------------ aba dados --
  async function renderDados() {
    if (!st.relatorio) st.relatorio = await api("/carga/relatorio");
    const r = st.relatorio;
    metricas($("#carga-totais"), [
      [r.totais.PRO_PROFESSOR, "professores"], [r.totais.DIS_DISCIPLINA, "disciplinas"], [r.totais.HOR_HORARIO, "faixas de horário"],
      [r.totais.ALO_ALOCACAO, "alocações"], [r.totais.GRA_GRADE_HORARIA, "linhas da grade atual"], [r.linhas_ignoradas.length, "linhas ignoradas"],
    ]);
    const tabela = (cab, linhas) => el("div", { class: "tabela-rolagem" }, el("table", { class: "tabela" },
      el("thead", {}, el("tr", {}, cab.map(c => el("th", {}, c)))),
      el("tbody", {}, linhas.map(l => el("tr", {}, l.map(c => el("td", {}, String(c))))))));
    const blocos = [
      el("div", { class: "relatorio-bloco" }, el("h3", {}, `Linhas ignoradas (${r.linhas_ignoradas.length})`),
        r.linhas_ignoradas.length
          ? tabela(["Arquivo", "Linha", "Motivo", "Conteúdo"], r.linhas_ignoradas.map(i => [i.arquivo, i.linha, i.motivo, i.conteudo]))
          : el("p", { class: "texto" }, "Nenhuma linha ignorada: todas as linhas das fontes eram válidas. Horários fora do padrão dia (2–6) + faixa (A–L) também seriam listados aqui.")),
      el("div", { class: "relatorio-bloco" }, el("h3", {}, `Disciplinas com horário modificado (${r.horarios_modificados.length}), carregadas com o horário atual`),
        tabela(["Código", "Disciplina", "Original", "Atual"], r.horarios_modificados.map(m => [m.codigo, titulo(m.disciplina), m.original, m.atual]))),
      el("div", { class: "relatorio-bloco" }, el("h3", {}, `Divergências entre o CP21 e a oferta (${r.divergencias_cp21.length})`),
        tabela(["Código", "Disciplina", "Campo", "CP21", "Oferta", "Decisão"], r.divergencias_cp21.map(d => [d.codigo, titulo(d.disciplina), d.campo, d.cp21, d.oferta, d.decisao]))),
      el("div", { class: "relatorio-bloco" }, el("h3", {}, "Avisos"), el("ul", { class: "texto" }, r.avisos.map(a => el("li", {}, a)))),
    ];
    $("#carga-relatorio").replaceChildren(...blocos);

    const profsPorDis = new Map();
    const nomePro = new Map(st.dados.professores.map(p => [p.PRO_ID, p.PRO_NOME]));
    for (const a of st.dados.alocacoes) {
      profsPorDis.set(a.DIS_ID, [...(profsPorDis.get(a.DIS_ID) || []), nomeCurto(nomePro.get(a.PRO_ID))]);
    }
    const disc = [...st.dados.disciplinas].sort((a, b) => a.DIS_PERIODO - b.DIS_PERIODO || a.DIS_CODIGO.localeCompare(b.DIS_CODIGO));
    $("#tabela-disciplinas").replaceChildren(
      el("thead", {}, el("tr", {}, ["Código", "Disciplina", "Período", "Carga", "Faixas/semana", "Tipo", "Professor"].map(c => el("th", {}, c)))),
      el("tbody", {}, disc.map(d => el("tr", {},
        el("td", {}, d.DIS_CODIGO), el("td", {}, titulo(d.DIS_DESCRICAO)), el("td", { class: "num" }, `${d.DIS_PERIODO}º`),
        el("td", { class: "num" }, `${d.DIS_CARGA_HORARIA}h`), el("td", { class: "num" }, d.DIS_CARGA_HORARIA / 15),
        el("td", {}, d.DIS_ELETIVA ? "Eletiva" : "Obrigatória"), el("td", {}, (profsPorDis.get(d.DIS_ID) || []).join(", "))))));
  }

  // ----------------------------------------------------------------- abas --
  function trocarAba(nome) {
    $$(".aba").forEach(b => { const ativa = b.dataset.aba === nome; b.classList.toggle("ativa", ativa); b.setAttribute("aria-selected", ativa); });
    $$(".painel-aba").forEach(p => { p.hidden = p.id !== `aba-${nome}`; });
    if (nome !== "grade") fecharDetalhe();
    if (nome === "gerar") irParaPasso(st.passo).catch(e => avisar(e.message, true));
    if (nome === "grafo") renderGrafo().catch(e => avisar(e.message, true));
    if (nome === "dados") renderDados().catch(e => avisar(e.message, true));
    history.replaceState(null, "", `#${nome}`);
  }

  // --------------------------------------------------------------- início --
  function preencherSelects() {
    const periodos = st.dados.periodos.map(p => el("option", { value: p }, `${p}º período`));
    for (const id of ["#sel-periodo", "#sel-periodo-passos", "#sel-periodo-grafo"]) {
      $(id).replaceChildren(...periodos.map(o => o.cloneNode(true)));
      $(id).value = st.periodo;
    }
    const profs = [...st.dados.professores].sort((a, b) => a.PRO_NOME.localeCompare(b.PRO_NOME))
      .map(p => el("option", { value: p.PRO_ID }, titulo(p.PRO_NOME)));
    for (const id of ["#sel-professor", "#sel-professor-grafo"]) $(id).replaceChildren(...profs.map(o => o.cloneNode(true)));
    const eliane = st.dados.professores.find(p => /ELIANE/.test(p.PRO_NOME)) || st.dados.professores[0];
    st.professor = st.professorGrafo = eliane.PRO_ID;
    $("#sel-professor").value = $("#sel-professor-grafo").value = eliane.PRO_ID;
    $("#sel-ordem").replaceChildren(...st.dados.ordens.map(o => el("option", { value: o.valor }, o.nome)));
    $("#sel-ordem").value = "dsatur";
  }

  function ligarEventos() {
    $$(".aba").forEach(b => b.addEventListener("click", () => trocarAba(b.dataset.aba)));
    $$("[data-visao]").forEach(b => b.addEventListener("click", () => trocarVisao(b.dataset.visao)));
    $$("[data-recorte]").forEach(b => b.addEventListener("click", () => trocarRecorte(b.dataset.recorte)));
    $("#sel-periodo").addEventListener("change", e => { st.periodo = +e.target.value; fecharDetalhe(); renderGrade(); });
    $("#sel-professor").addEventListener("change", e => { st.professor = +e.target.value; fecharDetalhe(); renderGrade(); });
    $("#sel-periodo-grafo").addEventListener("change", e => { st.periodoGrafo = +e.target.value; renderGrafo(); });
    $("#sel-professor-grafo").addEventListener("change", e => { st.professorGrafo = +e.target.value; renderGrafo(); });
    $("#sel-periodo-passos").addEventListener("change", renderPassos);
    $("#detalhe-fechar").addEventListener("click", fecharDetalhe);
    document.addEventListener("keydown", e => { if (e.key === "Escape") fecharDetalhe(); });
    $("#btn-gerar").addEventListener("click", gerar);
    $("#btn-salvar").addEventListener("click", salvar);
    $("#btn-tocar").addEventListener("click", tocar);
    $("#btn-passo-inicio").addEventListener("click", () => { parar(); irParaPasso(0); });
    $("#btn-passo-fim").addEventListener("click", () => { parar(); irParaPasso(st.grade.total_passos); });
    $("#btn-passo-menos").addEventListener("click", () => { parar(); irParaPasso(st.passo - 1); });
    $("#btn-passo-mais").addEventListener("click", () => { parar(); irParaPasso(st.passo + 1); });
    $("#rng-passo").addEventListener("input", e => { parar(); irParaPasso(+e.target.value); });
  }

  async function iniciar() {
    try {
      [st.dados, st.grade] = await Promise.all([api("/dados"), api("/grade")]);
    } catch (e) {
      $("#origem-texto").textContent = "API indisponível";
      avisar("Não foi possível falar com a API. Rode `uvicorn main:app` dentro de back-end e abra http://localhost:8000.", true);
      return;
    }
    preencherSelects();
    ligarEventos();
    renderGrade();
    renderSemestres();
    await atualizarGerar(false);
    const aba = location.hash.slice(1);
    if (["grade", "gerar", "grafo", "dados"].includes(aba)) trocarAba(aba);
  }

  iniciar();
})();
