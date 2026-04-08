/* ═══════════════════════════════════════════════════════════
   CALL ANALYSIS DASHBOARD — Frontend Logic v2
   ═══════════════════════════════════════════════════════════ */

const API = "";  // mismo origen, Flask sirve todo

// Estado global
let _todosAgentes = [];
let _todasLlamadas = { closers: [], setters: [] };
let _filtroActual = "todos";
let _filtroLlamadas = "todos";
let _filtroFechaLlamadas = null;
let _detalleChart = null;

// ─── INICIALIZACIÓN ──────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    verificarConexion();
    cargarMetricas();
});

async function verificarConexion() {
    const dot = document.getElementById("conexionDot");
    const label = document.getElementById("conexionLabel");
    try {
        const r = await fetch(`${API}/api/metricas`);
        const data = await r.json();
        if (data.demo) {
            dot.className = "status-dot demo";
            label.textContent = "Modo Demo";
            document.getElementById("demoBadge").style.display = "flex";
        } else {
            dot.className = "status-dot ok";
            label.textContent = "NocoDB OK";
        }
    } catch {
        dot.className = "status-dot";
        label.textContent = "Sin conexión";
    }
}

async function refreshData() {
    const btn = document.querySelector(".btn-refresh");
    btn.style.transform = "rotate(360deg)";
    btn.style.transition = "transform 0.5s ease";
    await cargarMetricas();
    if (_filtroLlamadas !== null) await cargarLlamadas();
    setTimeout(() => { btn.style.transform = ""; btn.style.transition = ""; }, 600);
}

// ─── TAB SWITCHING ────────────────────────────────────────────

function switchTab(tab, el) {
    document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    document.getElementById(`tab-${tab}`).classList.add("active");
    el.classList.add("active");

    const titles = {
        metricas: ["Rendimiento del Equipo", "Setters & Closers · Semáforo de calidad"],
        llamadas: ["Llamadas Recientes", "KPIs por llamada · Detalle de desempeño"],
    };
    document.getElementById("pageTitle").textContent = titles[tab][0];
    document.getElementById("pageSub").textContent  = titles[tab][1];

    if (tab === "llamadas") cargarLlamadas();
}

// ─── MÓDULO: MÉTRICAS ─────────────────────────────────────────

async function cargarMetricas() {
    try {
        const r = await fetch(`${API}/api/metricas`);
        const data = await r.json();
        _todosAgentes = data.datos || [];
        renderizarKpis(_todosAgentes);
        renderizarAgentes(_todosAgentes, _filtroActual);
    } catch (e) {
        document.getElementById("agentsGrid").innerHTML =
            `<p style="color:var(--red);grid-column:1/-1;text-align:center;padding:32px">
        Error cargando métricas: ${e.message}</p>`;
    }
}

function renderizarKpis(agentes) {
    const n = (nivel) => agentes.filter(a => a.semaforo.nivel === nivel).length;
    const totalLlamadas = agentes.reduce((s, a) => s + (a.total_llamadas || 0), 0);
    document.getElementById("kpiExcelente").textContent = n("excelente");
    document.getElementById("kpiRegular").textContent = n("regular");
    document.getElementById("kpiCritico").textContent = n("critico");
    document.getElementById("kpiTotalLlamadas").textContent = totalLlamadas;
    document.querySelectorAll(".kpi-card").forEach(c => c.classList.remove("loading-pulse"));
}

function renderizarAgentes(agentes, filtro = "todos") {
    const grid = document.getElementById("agentsGrid");
    const filtrados = filtro === "todos" ? agentes : agentes.filter(a => a.tipo === filtro);

    if (!filtrados.length) {
        grid.innerHTML = `<p style="color:var(--text-muted);grid-column:1/-1;text-align:center;padding:48px">
      No hay datos para <b>${filtro === 'setter' ? 'Setters' : (filtro === 'closer' ? 'Closers' : 'agentes')}</b> en este periodo.</p>`;
        return;
    }

    grid.innerHTML = filtrados.map(a => tarjetaAgente(a)).join("");
}

function tarjetaAgente(a) {
    const nivel = a.semaforo?.nivel || "sin_datos";
    const color = a.semaforo?.color || "var(--gray)";
    const scoreVal = a.promedio !== null ? a.promedio.toFixed(1) : "—";
    const scoreWidth = a.promedio !== null ? (a.promedio / 10 * 100) : 0;
    const avatarClass = `avatar-${a.tipo}`;
    const iniciales = (a.nombre || "??").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
    const tipoLabel = { closer: "Closer (Cierre)", setter: "Setter (Agendamiento)" };
    const tendenciaIcon = { subiendo: "↑ Subiendo", bajando: "↓ Bajando", estable: "→ Estable" };
    const tendenciaClass = `tendencia-${a.tendencia || "estable"}`;

    // Métricas extra según tipo
    let metricaExtra = "";
    if (a.tipo === "closer") {
        const tasa = a.tasa_cierre !== undefined ? `${a.tasa_cierre}%` : "—";
        metricaExtra = `<div class="agent-kpi-extra"><span>🏆 Cierre</span><strong>${tasa}</strong></div>`;
    } else if (a.tipo === "setter") {
        const tasa = a.tasa_agendamiento !== undefined ? `${a.tasa_agendamiento}%` : "—";
        metricaExtra = `<div class="agent-kpi-extra"><span>📅 Agenda</span><strong>${tasa}</strong></div>`;
    }

    return `
    <div class="agent-card nivel-${nivel}" onclick="verDetalle('${a.nombre}')" title="Ver detalle">
      <div class="agent-card-header">
        <div class="agent-avatar ${avatarClass}">${iniciales}</div>
        <div>
          <div class="agent-name">${a.nombre}</div>
          <div class="agent-tipo-badge">${tipoLabel[a.tipo] || a.tipo}</div>
        </div>
        <div class="semaforo-badge semaforo-${nivel}">
          ${a.semaforo?.emoji || "❔"} ${a.semaforo?.label || "Sin Datos"}
        </div>
      </div>

      <div class="agent-score-row">
        <div class="agent-score">
          <span class="score-val">${scoreVal}</span>
          <span class="score-max">/10</span>
          <span class="score-label">score</span>
        </div>
        ${metricaExtra}
      </div>

      <div class="score-bar">
        <div class="score-fill" style="width:${scoreWidth}%;background:${color}"></div>
      </div>

      <div class="agent-meta">
        <span>📞 ${a.total_llamadas} llamadas</span>
        <span class="${tendenciaClass}">${tendenciaIcon[a.tendencia] || "—"}</span>
      </div>
    </div>
  `;
}

function filtrarAgentes(filtro, btn) {
    _filtroActual = filtro;
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    renderizarAgentes(_todosAgentes, filtro);
}

// ─── MÓDULO: DETALLE AGENTE ────────────────────────────────────

function verDetalle(nombre) {
    const agente = _todosAgentes.find(a => a.nombre === nombre);
    if (!agente) return;

    const emoji = agente.semaforo?.emoji || "";
    const label = agente.semaforo?.label || "Sin datos";
    document.getElementById("detalleNombre").innerHTML = `
        <span style="color:var(--text-muted); font-size:14px; display:block; text-transform:uppercase;">Detalle de Rendimiento</span>
        ${agente.nombre} <small style="font-size:13px; font-weight:normal; margin-left:10px;">· ${emoji} ${label}</small>
    `;
    document.getElementById("detalleContent").innerHTML = renderizarDetalle(agente);
    document.getElementById("detalleOverlay").classList.add("open");

    if (agente.historial && agente.historial.length > 1) {
        setTimeout(() => renderizarMiniChart(agente), 100);
    }
}

function renderizarDetalle(a) {
    const mejor = a.mejor !== null ? a.mejor : "—";
    const peor = a.peor !== null ? a.peor : "—";
    const prom = a.promedio !== null ? a.promedio.toFixed(1) : "—";

    const desglose = Object.entries(a.desglose || {}).map(([label, val]) => `
    <div class="desglose-item" style="margin-bottom:15px">
      <div style="display:flex; justify-content:space-between; margin-bottom:5px">
        <span style="font-size:12px; font-weight:600; color:var(--text-dim)">${label}</span>
        <span style="font-size:12px; font-weight:bold">${val}/10</span>
      </div>
      <div style="height:6px; background:rgba(255,255,255,0.05); border-radius:10px; overflow:hidden">
        <div style="height:100%; width:${val * 10}%; background:var(--accent); border-radius:10px"></div>
      </div>
    </div>
  `).join("");

    // Métricas adicionales por tipo
    let kpisExtra = "";
    if (a.tipo === "closer") {
        kpisExtra = `
        <div class="kpi-card" style="padding:15px">
          <div class="kpi-val" style="font-size:24px;color:#8b5cf6">${a.tasa_cierre ?? "—"}%</div>
          <div class="kpi-label" style="font-size:10px">Tasa de Cierre</div>
        </div>`;
    } else if (a.tipo === "setter") {
        kpisExtra = `
        <div class="kpi-card" style="padding:15px">
          <div class="kpi-val" style="font-size:24px;color:#10b981">${a.tasa_agendamiento ?? "—"}%</div>
          <div class="kpi-label" style="font-size:10px">Tasa de Agendamiento</div>
        </div>`;
    }

    return `
    <div class="detalle-body">
      <div class="kpi-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom:30px">
        <div class="kpi-card" style="padding:15px">
          <div class="kpi-val" style="font-size:24px">${prom}</div>
          <div class="kpi-label" style="font-size:10px">Promedio</div>
        </div>
        <div class="kpi-card" style="padding:15px">
          <div class="kpi-val" style="font-size:24px; color:var(--green)">${mejor}</div>
          <div class="kpi-label" style="font-size:10px">Mejor llamada</div>
        </div>
        <div class="kpi-card" style="padding:15px">
          <div class="kpi-val" style="font-size:24px; color:var(--red)">${peor}</div>
          <div class="kpi-label" style="font-size:10px">Llamada más baja</div>
        </div>
        ${kpisExtra}
      </div>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:40px">
        <div>
          <h4 style="font-size:13px; text-transform:uppercase; color:var(--text-muted); margin-bottom:20px; letter-spacing:1px">Desglose por área</h4>
          ${desglose || "<p>Sin desglose disponible</p>"}
        </div>
        <div id="miniChartContainer">
           <h4 style="font-size:13px; text-transform:uppercase; color:var(--text-muted); margin-bottom:20px; letter-spacing:1px">Tendencia de calidad</h4>
           <canvas id="detalleChart" height="200"></canvas>
        </div>
      </div>
    </div>
  `;
}

function renderizarMiniChart(agente) {
    const ctx = document.getElementById("detalleChart");
    if (!ctx) return;
    if (_detalleChart) _detalleChart.destroy();

    const color = agente.semaforo?.color || "#8b5cf6";
    const labels = agente.historial.map((h, i) => i + 1);
    const data = agente.historial.map(h => h.calificacion);

    _detalleChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [{
                data,
                borderColor: color,
                backgroundColor: color + "20",
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: color,
            }]
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                y: { min: 0, max: 10, ticks: { color: "#64748b", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.05)" } },
                x: { ticks: { color: "#64748b", font: { size: 10 } }, grid: { display: false } }
            }
        }
    });
}

function cerrarDetalle(e) {
    if (e && e.target !== document.getElementById("detalleOverlay")) return;
    document.getElementById("detalleOverlay").classList.remove("open");
}

// ─── MÓDULO: LLAMADAS ─────────────────────────────────────────

async function cargarLlamadas() {
    const container = document.getElementById("llamadasContainer");
    container.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:48px">Cargando llamadas...</p>`;
    try {
        const r = await fetch(`${API}/api/llamadas`);
        const data = await r.json();
        _todasLlamadas = data.datos || { closers: [], setters: [] };
        renderizarLlamadas(_filtroLlamadas);
    } catch (e) {
        container.innerHTML = `<p style="color:var(--red);text-align:center;padding:48px">Error: ${e.message}</p>`;
    }
}

function filtrarLlamadas(filtro, btn) {
    _filtroLlamadas = filtro;
    document.querySelectorAll("#tab-llamadas .filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    renderizarLlamadas(filtro);
}

function filtrarPorFecha(fecha) {
    _filtroFechaLlamadas = fecha; // "YYYY-MM-DD" o vacío
    renderizarLlamadas(_filtroLlamadas);
}

function quitarFiltroFecha() {
    _filtroFechaLlamadas = null;
    document.getElementById("fechaLlamadas").value = "";
    renderizarLlamadas(_filtroLlamadas);
}

function renderizarLlamadas(filtro) {
    const container = document.getElementById("llamadasContainer");
    let lista = [];

    if (filtro === "todos" || filtro === "closer") {
        (_todasLlamadas.closers || []).forEach(c => {
             const f = c["Fecha Llamada"] || (c["CreatedAt"] ? c["CreatedAt"].split(" ")[0] : "");
             lista.push({ ...c, _tipo: "closer", "Fecha Llamada": f });
        });
    }
    if (filtro === "todos" || filtro === "setter") {
        (_todasLlamadas.setters || []).forEach(s => {
             const f = s["Fecha Llamada"] || (s["CreatedAt"] ? s["CreatedAt"].split(" ")[0] : "");
             lista.push({ ...s, _tipo: "setter", "Fecha Llamada": f });
        });
    }

    // Filtrar por fecha exacta si hay una seleccionada
    if (_filtroFechaLlamadas) {
        lista = lista.filter(c => {
            const f = c["Fecha Llamada"] || "";
            return f.startsWith(_filtroFechaLlamadas);
        });
    }

    // Ordenar por fecha desc
    lista.sort((a, b) => (b["Fecha Llamada"] || "").localeCompare(a["Fecha Llamada"] || ""));

    if (!lista.length) {
        container.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:48px">No hay llamadas analizadas en este período.</p>`;
        return;
    }

    container.innerHTML = `<div class="calls-list">${lista.map(c => tarjetaLlamada(c)).join("")}</div>`;
}

function tarjetaLlamada(c) {
    const tipo = c._tipo;
    const nombre = tipo === "closer"
        ? (c["Closer"] || c.nombre_closer || "—")
        : (c["Setter"] || c.nombre_setter || "—");
    const nota = parseFloat(c["Nota Total"] || 0).toFixed(1);
    const fecha = formatFecha(c["Fecha Llamada"]);
    const mesAnio = c["Mes-Año"] || "—";

    // Resultado
    const resultado = tipo === "closer"
        ? (c["Resultado"] || "—")
        : (c["Agendó?"] || "—");

    // Indicador de resultado
    const resultadoOk = resultado.toLowerCase().includes("vend") || resultado.toLowerCase() === "sí" || resultado.toLowerCase() === "si";
    const resultadoBadge = resultado !== "—"
        ? `<span class="resultado-badge ${resultadoOk ? 'resultado-ok' : 'resultado-no'}">${resultado}</span>`
        : "";

    // Color de nota
    const notaNum = parseFloat(nota);
    const notaColor = notaNum >= 8 ? "#22c55e" : notaNum >= 6 ? "#f59e0b" : "#ef4444";

    // Desglose mini
    let dims = [];
    if (tipo === "closer") {
        dims = [
            { label: "Rapport", val: c["Rapport"] },
            { label: "Desc.", val: c["Descubrimiento"] },
            { label: "Present.", val: c["Presentación"] },
            { label: "Objecc.", val: c["Objeciones"] },
            { label: "Cierre", val: c["Cierre"] },
        ];
    } else {
        dims = [
            { label: "Rapport", val: c["Rapport"] },
            { label: "Dolor", val: c["Identificación Dolor"] },
            { label: "V. Cita", val: c["Venta Cita"] },
            { label: "Objecc.", val: c["Objeciones"] },
        ];
    }

    const dimsHtml = dims.map(d => {
        const v = parseFloat(d.val || 0);
        const col = v >= 8 ? "#22c55e" : v >= 6 ? "#f59e0b" : "#ef4444";
        return `<div class="dim-pill">
      <span class="dim-label">${d.label}</span>
      <span class="dim-val" style="color:${col}">${v.toFixed(1)}</span>
    </div>`;
    }).join("");

    const avatarClass = tipo === "closer" ? "avatar-closer" : "avatar-setter";
    const iniciales = nombre.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
    const tipoLabel = tipo === "closer" ? "Closer" : "Setter";
    const tipoColor = tipo === "closer" ? "#8b5cf6" : "#10b981";

    return `
  <div class="call-card" onclick="verDetalleLlamada(${JSON.stringify(c).replace(/"/g, '&quot;')})">
    <div class="call-card-left">
      <div class="agent-avatar ${avatarClass}" style="width:42px;height:42px;font-size:14px">${iniciales}</div>
    </div>
    <div class="call-card-body">
      <div class="call-card-top">
        <div>
          <span class="call-nombre">${nombre}</span>
          <span class="call-tipo-pill" style="background:${tipoColor}20;color:${tipoColor}">${tipoLabel}</span>
          ${resultadoBadge}
        </div>
        <div class="call-nota" style="color:${notaColor}">${nota}<span style="font-size:12px;opacity:.6">/10</span></div>
      </div>
      <div class="call-dims">${dimsHtml}</div>
      <div class="call-meta">
        <span>📅 ${fecha}</span>
        <span>📆 ${mesAnio}</span>
        <span>🆔 ${c["ID Llamada"] || "—"}</span>
      </div>
    </div>
  </div>`;
}

function verDetalleLlamada(c) {
    const tipo = c._tipo;
    const nombre = tipo === "closer"
        ? (c["Closer"] || c.nombre_closer || "—")
        : (c["Setter"] || c.nombre_setter || "—");

    document.getElementById("llamadaTitulo").textContent = `📞 ${nombre} — ${formatFecha(c["Fecha Llamada"])}`;

    let camposExtra = "";
    if (tipo === "closer") {
        camposExtra = `
      <div class="detalle-kpi-row">
        <div class="detalle-kpi"><span>Rapport</span><strong>${c["Rapport"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Descubrimiento</span><strong>${c["Descubrimiento"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Presentación</span><strong>${c["Presentación"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Objeciones</span><strong>${c["Objeciones"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Cierre</span><strong>${c["Cierre"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Resultado</span><strong>${c["Resultado"] || "—"}</strong></div>
      </div>`;
    } else {
        camposExtra = `
      <div class="detalle-kpi-row">
        <div class="detalle-kpi"><span>Rapport</span><strong>${c["Rapport"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Identif. Dolor</span><strong>${c["Identificación Dolor"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Venta Cita</span><strong>${c["Venta Cita"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Objeciones</span><strong>${c["Objeciones"] || "—"}</strong></div>
        <div class="detalle-kpi"><span>Agendó?</span><strong>${c["Agendó?"] || "—"}</strong></div>
      </div>`;
    }

    document.getElementById("llamadaContent").innerHTML = `
    <div style="display:flex; flex-direction:column; gap:24px;">
      <div class="kpi-grid" style="grid-template-columns: repeat(3,1fr)">
        <div class="kpi-card" style="padding:16px">
          <div class="kpi-val" style="font-size:28px">${parseFloat(c["Nota Total"] || 0).toFixed(1)}</div>
          <div class="kpi-label">Nota Total</div>
        </div>
        <div class="kpi-card" style="padding:16px">
          <div class="kpi-val" style="font-size:18px">${formatFecha(c["Fecha Llamada"])}</div>
          <div class="kpi-label">Fecha</div>
        </div>
        <div class="kpi-card" style="padding:16px">
          <div class="kpi-val" style="font-size:18px">${c["Mes-Año"] || "—"}</div>
          <div class="kpi-label">Período</div>
        </div>
      </div>
      <div>
        <h4 style="font-size:12px;text-transform:uppercase;color:var(--text-muted);letter-spacing:1px;margin-bottom:16px">Desglose de Métricas</h4>
        ${camposExtra}
      </div>
    </div>`;

    document.getElementById("llamadaOverlay").classList.add("open");
}

function cerrarLlamada(e) {
    if (e && e.target !== document.getElementById("llamadaOverlay")) return;
    document.getElementById("llamadaOverlay").classList.remove("open");
}

// ─── HELPERS ──────────────────────────────────────────────────

function formatFecha(f) {
    if (!f) return "—";
    try {
        return new Date(f + "T00:00:00").toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
    } catch { return f; }
}

function mostrarToast(msg, tipo = "success") {
    const t = document.createElement("div");
    t.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:9999;
    background:${tipo === "error" ? "#ef4444" : "#22c55e"};
    color:white; padding:12px 20px; border-radius:10px;
    font-family:Inter,sans-serif; font-size:13.5px; font-weight:600;
    box-shadow:0 8px 24px rgba(0,0,0,0.4);
  `;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}
