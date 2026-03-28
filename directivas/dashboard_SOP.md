# DIRECTIVA — Dashboard Web de Gestión y Métricas de Agentes

## Objetivo
Construir un dashboard web interno (Flask + HTML/CSS/JS) con dos secciones:
1. **Gestión de Agentes**: onboarding/CRUD de personas analizables (Closers, Soporte, Onboarding).
2. **Métricas de Rendimiento**: visualización con semáforo de rendimiento para que el CEO tome decisiones.

---

## Arquitectura

```
dashboard/
├── app.py              ← Servidor Flask (backend + proxy NocoDB)
├── templates/
│   └── index.html      ← SPA: todo el dashboard en una página
└── static/
    ├── style.css       ← Estilos premium (dark mode, glassmorphism)
    └── app.js          ← Lógica frontend (fetch API, gráficas, semáforos)
```

Ejecución:
```
python dashboard/app.py
```
Acceso: http://localhost:5050

---

## Nueva Tabla en NocoDB: `agentes`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | string | Nombre completo del agente |
| `tipo` | enum | `closer`, `soporte`, `onboarding` |
| `email_fathom` | string | Email asociado en Fathom (opcional) |
| `activo` | boolean | Si se incluye en reportes actualmente |
| `fecha_registro` | date | Cuándo se dio de alta |

---

## Reglas de Semáforo (Lógica de Rendimiento)

Se calcula el promedio de `calificacion_total` de las últimas N llamadas del agente.

| Nivel | Condición | Color | Icono |
|-------|-----------|-------|-------|
| Excelente | promedio >= 8.0 | 🟢 Verde | ✅ |
| Regular | 6.0 <= promedio < 8.0 | 🟡 Amarillo | ⚠️ |
| Crítico | promedio < 6.0 | 🔴 Rojo | 🚨 |
| Sin datos | sin calificaciones | ⚪ Gris | — |

---

## Rutas del Backend Flask

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Sirve el HTML del dashboard |
| GET | `/api/agentes` | Lista todos los agentes |
| POST | `/api/agentes` | Crea un nuevo agente |
| PUT | `/api/agentes/<id>` | Actualiza un agente |
| DELETE | `/api/agentes/<id>` | Desactiva/elimina un agente |
| GET | `/api/metricas` | Devuelve métricas consolidadas por agente con semáforo |

---

## Lógica de `/api/metricas`

Para cada agente activo:
1. Leer su `tipo`
2. Según tipo, consultar la tabla correcta en NocoDB:
   - `closer` → `calificaciones_closers` filtrando por `nombre_closer`
   - `soporte` → usar `calificaciones_closers` con flag soporte (o tabla general)
   - `onboarding` → `calificaciones_onboarding` filtrando por `nombre_coach`
3. Si hay registros: calcular promedio, tendencia (últimos 5), mejor/peor llamada
4. Asignar nivel semáforo

---

## Restricciones / Casos Borde

- El backend Flask actúa como **proxy** de NocoDB. Nunca exponer el `NOCODB_API_TOKEN` al frontend.
- Si NocoDB no está configurado, el backend retorna datos de demo para desarrollo.
- La tabla `agentes` puede no existir aún → el backend debe manejar el error gracefully.
- Los nombres en `calificaciones_closers.nombre_closer` deben coincidir exactamente con `agentes.nombre`. Ser case-insensitive al filtrar.
- Flask corre en puerto 5050 (no 5000 para evitar conflicto con AirPlay en Mac, aunque aquí es Windows).
