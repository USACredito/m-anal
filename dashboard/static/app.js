/* ═══════════════════════════════════════════════════════════
   CALL ANALYSIS DASHBOARD — Frontend Logic
   ═══════════════════════════════════════════════════════════ */

const API = "";  // mismo origen, Flask sirve todo

// Estado global
let _todosAgentes = [];
let _filtroActual = "todos";
let _evolucionChart = null;
let _detalleChart = null;

// ─── INICIALIZACIÓN ──────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    verificarConexion();
    cargarMetricas();
    cargarTablaAgentes();
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
    await cargarTablaAgentes();
    setTimeout(() => { btn.style.transform = ""; btn.style.transition = ""; }, 600);
}

// ─── TAB SWITCHING ────────────────────────────────────────────

function switchTab(tab, el) {
    document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    document.getElementById(`tab-${tab}`).classList.add("active");
    el.classList.add("active");

    const titles = {
        metricas: ["Rendimiento de Ventas", "Setters & Closers · Semáforo de calidad"],
        agentes: ["Gestión del Equipo", "Alta y edición de Setters y Closers"],
        evolucion: ["Evolución de Calidad", "Histórico de desempeño mensual"],
    };
    document.getElementById("pageTitle").textContent = titles[tab][0];
    document.getElementById("pageSub").textContent = titles[tab][1];

    if (tab === "evolucion") cargarEvolucion();
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
    document.getElementById("kpiExcelente").textContent = n("excelente");
    document.getElementById("kpiRegular").textContent = n("regular");
    document.getElementById("kpiCritico").textContent = n("critico");
    document.getElementById("kpiTotal").textContent = agentes.length;

    // Quitar pulso de carga
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
    const tendenciaIcon = { subiendo: "↑ Subiendo", bajando: "↓ Bajando", estable: "→ Estable", null: "—" };
    const tendenciaClass = `tendencia-${a.tendencia || "estable"}`;

    return `
    <div class="agent-card nivel-${nivel}" onclick="verDetalle(${a.id})" title="Ver detalle">
      <div class="agent-card-header">
        <div class="agent-avatar ${avatarClass}">${iniciales}</div>
        <div class="agent-name">${a.nombre}</div>
        <div class="semaforo-badge semaforo-${nivel}">
          ${a.semaforo?.emoji || "❔"} ${a.semaforo?.label || "Sin Datos"}
        </div>
      </div>

      <div class="agent-tipo-badge">${tipoLabel[a.tipo] || a.tipo}</div>

      <div class="agent-score">
        <span class="score-val">${scoreVal}</span>
        <span class="score-max">/10</span>
        <span class="score-label">score</span>
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

async function verDetalle(id) {
    const agente = _todosAgentes.find(a => a.id === id);
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

    return `
    <div class="detalle-body">
      <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom:30px">
        <div class="kpi-card" style="padding:15px">
          <div class="kpi-val" style="font-size:24px">${prom}</div>
          <div class="kpi-label" style="font-size:10px">Promedio</div>
        </div>
        <div class="kpi-card" style="padding:15px">
          <div class="kpi-val" style="font-size:24px; color:var(--green)">${mejor}</div>
          <div class="kpi-label" style="font-size:10px">Máximo</div>
        </div>
        <div class="kpi-card" style="padding:15px">
          <div class="kpi-val" style="font-size:24px; color:var(--red)">${peor}</div>
          <div class="kpi-label" style="font-size:10px">Mínimo</div>
        </div>
      </div>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:40px">
        <div>
          <h4 style="font-size:13px; text-transform:uppercase; color:var(--text-muted); margin-bottom:20px; letter-spacing:1px">Desglose por área</h4>
          ${desglose || "<p>Sin desglose disponible</p>"}
        </div>
        <div id="miniChartContainer">
           <h4 style="font-size:13px; text-transform:uppercase; color:var(--text-muted); margin-bottom:20px; letter-spacing:1px">Tendencia</h4>
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

// ─── MÓDULO: TABLA DE AGENTES ─────────────────────────────────

async function cargarTablaAgentes() {
    try {
        const r = await fetch(`${API}/api/agentes`);
        const data = await r.json();
        const agentes = data.datos || data;
        renderizarTabla(Array.isArray(agentes) ? agentes : []);
    } catch (e) {
        document.getElementById("agentesTableBody").innerHTML =
            `<tr><td colspan="6" class="loading-cell" style="color:var(--red)">Error: ${e.message}</td></tr>`;
    }
}

function renderizarTabla(agentes) {
    const tbody = document.getElementById("agentesTableBody");
    if (!agentes.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No hay agentes. Agregue el primero ↑</td></tr>`;
        return;
    }

    const tipoLabel = { closer: "Closer (Vendedor)", setter: "Setter (Agendador)" };

    tbody.innerHTML = agentes.map(a => `
    <tr>
      <td style="color:var(--text-primary);font-weight:600">${a.nombre}</td>
      <td><span class="tipo-pill ${a.tipo === 'closer' ? 'tipo-closer' : 'tipo-onboarding'}">${tipoLabel[a.tipo] || a.tipo}</span></td>
      <td>${a.email_fathom || "—"}</td>
      <td class="${a.activo ? 'estado-activo' : 'estado-inactivo'}">${a.activo ? "Activo" : "Inactivo"}</td>
      <td>${formatFecha(a.fecha_registro)}</td>
      <td>
        <div class="action-btns">
          <button class="btn-action" onclick="editarAgente(${a.Id})">✏️</button>
          <button class="btn-action danger" onclick="toggleAgente(${a.Id}, ${a.activo})">${a.activo ? "⏸" : "▶️"}</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function formatFecha(f) {
    if (!f) return "—";
    try {
        return new Date(f + "T00:00:00").toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
    } catch { return f; }
}

// ─── MÓDULO: CRUD AGENTES ─────────────────────────────────────

let _agentesDB = [];

async function abrirModal(id = null) {
    document.getElementById("modalTitle").textContent = id ? "Editar Agente" : "Nuevo Agente";
    document.getElementById("agenteId").value = id || "";
    document.getElementById("btnGuardar").textContent = id ? "Guardar Cambios" : "Guardar Agente";

    if (id) {
        // Obtener datos actuales del agente
        const r = await fetch(`${API}/api/agentes`);
        const data = await r.json();
        const agentes = data.datos || data;
        const agente = (Array.isArray(agentes) ? agentes : []).find(a => a.Id === id);
        if (agente) {
            document.getElementById("fNombre").value = agente.nombre || "";
            document.getElementById("fTipo").value = agente.tipo || "closer";
            document.getElementById("fEmail").value = agente.email_fathom || "";
            document.getElementById("fActivo").checked = agente.activo !== false;
        }
    } else {
        document.getElementById("agenteForm").reset();
        document.getElementById("fActivo").checked = true;
    }

    document.getElementById("modalOverlay").classList.add("open");
    document.getElementById("fNombre").focus();
}

function cerrarModal(e) {
    if (e && e.target !== document.getElementById("modalOverlay")) return;
    document.getElementById("modalOverlay").classList.remove("open");
}

async function guardarAgente(e) {
    e.preventDefault();
    const id = document.getElementById("agenteId").value;
    const btn = document.getElementById("btnGuardar");

    const payload = {
        nombre: document.getElementById("fNombre").value.trim(),
        tipo: document.getElementById("fTipo").value,
        email_fathom: document.getElementById("fEmail").value.trim(),
        activo: document.getElementById("fActivo").checked,
    };

    btn.textContent = "Guardando...";
    btn.disabled = true;

    try {
        const url = id ? `${API}/api/agentes/${id}` : `${API}/api/agentes`;
        const method = id ? "PUT" : "POST";
        const r = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!r.ok) throw new Error(`Error ${r.status}`);

        cerrarModal();
        await Promise.all([cargarTablaAgentes(), cargarMetricas()]);
        mostrarToast(`Agente ${id ? "actualizado" : "creado"} correctamente ✅`);
    } catch (err) {
        mostrarToast(`Error: ${err.message}`, "error");
    } finally {
        btn.textContent = id ? "Guardar Cambios" : "Guardar Agente";
        btn.disabled = false;
    }
}

async function editarAgente(id) {
    await abrirModal(id);
}

async function toggleAgente(id, activo) {
    const accion = activo ? "pausar" : "activar";
    if (!confirm(`¿${activo ? "Desactivar" : "Activar"} este agente?`)) return;

    try {
        const url = activo
            ? `${API}/api/agentes/${id}`
            : `${API}/api/agentes/${id}`;
        const method = activo ? "DELETE" : "PUT";
        const body = activo ? undefined : JSON.stringify({ activo: true });

        const r = await fetch(url, {
            method,
            headers: body ? { "Content-Type": "application/json" } : {},
            body,
        });
        if (!r.ok) throw new Error(`Error ${r.status}`);

        await cargarTablaAgentes();
        mostrarToast(`Agente ${activo ? "desactivado" : "activado"} ✅`);
    } catch (err) {
        mostrarToast(`Error: ${err.message}`, "error");
    }
}

// ─── MÓDULO: EVOLUCIÓN ────────────────────────────────────────

async function cargarEvolucion() {
    try {
        const r = await fetch(`${API}/api/resumen_mensual`);
        const data = await r.json();
        const registros = data.datos || [];
        renderizarEvolucion(registros);
    } catch (e) {
        console.error("Error cargando evolución:", e);
    }
}

function renderizarEvolucion(registros) {
    const ctx = document.getElementById("evolucionChart");
    if (!ctx) return;
    if (_evolucionChart) _evolucionChart.destroy();

    const labels = registros.map(r => r["mes_año"]);
    const closers = registros.map(r => r.promedio_calidad_closers);
    const setters = registros.map(r => r.promedio_calidad_setters);
    const leads = registros.map(r => r.promedio_calidad_leads);

    _evolucionChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                { label: "Closers", data: closers, borderColor: "#8b5cf6", backgroundColor: "#8b5cf620", fill: true, tension: 0.4 },
                { label: "Setters", data: setters, borderColor: "#10b981", backgroundColor: "#10b98120", fill: true, tension: 0.4 },
                { label: "Leads", data: leads, borderColor: "#f59e0b", backgroundColor: "#f59e0b20", fill: true, tension: 0.4 },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { min: 0, max: 10, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#64748b" } },
                x: { grid: { display: false }, ticks: { color: "#64748b" } }
            }
        }
    });
}

// ─── TOAST ────────────────────────────────────────────────────

function mostrarToast(msg, tipo = "success") {
    const t = document.createElement("div");
    t.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:9999;
    background:${tipo === "error" ? "#ef4444" : "#22c55e"};
    color:white; padding:12px 20px; border-radius:10px;
    font-family:Inter,sans-serif; font-size:13.5px; font-weight:600;
    box-shadow:0 8px 24px rgba(0,0,0,0.4);
    animation: slideIn 0.3s ease;
  `;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}
