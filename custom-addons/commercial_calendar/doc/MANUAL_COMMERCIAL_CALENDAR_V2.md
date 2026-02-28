# Calendario Comercial v2 — Manual de Usuario

## Índice

1. [Resumen](#resumen)
2. [Conceptos Clave](#conceptos-clave)
3. [Configuración Inicial](#configuración-inicial)
4. [Mis Clientes (Portfolio)](#mis-clientes-portfolio)
5. [Ficha Comercial del Contacto](#ficha-comercial-del-contacto)
6. [Registro Rápido de Actividad](#registro-rápido-de-actividad)
7. [Cadenas de Seguimiento Automáticas](#cadenas-de-seguimiento-automáticas)
8. [Planificador Inteligente de Visitas](#planificador-inteligente-de-visitas)
9. [Puntuación Comercial](#puntuación-comercial)
10. [Alertas Automáticas](#alertas-automáticas)
11. [Crons y Automatizaciones](#crons-y-automatizaciones)
12. [Referencia Técnica](#referencia-técnica)

---

## Resumen

El módulo **Calendario Comercial v2** es un ecosistema comercial completo para equipos de visitadores médicos. Resuelve cuatro problemas fundamentales:

| Problema | Solución |
|----------|----------|
| No saben a quién visitar | **Planificador Inteligente** con algoritmo de priorización |
| No registran actividad | **Registro Rápido** en 1 click (individual y por lotes) |
| No hay seguimiento post-visita | **Cadenas de Seguimiento** automáticas al completar actividad |
| Falta visión global del cliente | **Ficha Comercial** con KPIs, alertas y acciones rápidas |

### Versión y Dependencias

- **Versión:** 19.0.2.0.0
- **Depende de:** `calendar`, `contacts`, `sale`, `partner_activity_tags`, `partner_volume_tags`, `partner_trend_tags`, `partner_crosssell_tags`, `partner_frequency_tags`

---

## Conceptos Clave

### Comercial Asignado
Cada contacto (empresa) puede tener un **comercial asignado** (`commercial_user_id`). Este campo determina:
- Quién ve al cliente en "Mis Clientes"
- Quién recibe alertas de clientes sin visitar
- El filtro por defecto en el Planificador de Visitas

### Puntuación Comercial (Score)
Número de 0 a 100 que indica la importancia/urgencia de atender a un cliente. Se calcula combinando volumen de compra, tendencia, recencia, frecuencia, oportunidades cross-sell y frescura de última visita.

### Tipos de Actividad Comercial
El módulo define 6 tipos de actividad:
- **Visita Comercial** — Visita presencial al cliente
- **Demo** — Demostración de producto
- **Formación** — Formación al cliente
- **Llamada Comercial** — Llamada telefónica
- **Seguimiento** — Seguimiento post-actividad
- **Presentación** — Presentación comercial

---

## Configuración Inicial

### 1. Asignar Comercial a Contactos

1. Ir a **Contactos** → abrir una empresa
2. En el formulario, buscar el campo **"Comercial asignado"** (debajo de "Vendedor")
3. Seleccionar el usuario comercial responsable

### 2. Definir Objetivo de Visitas

1. Abrir el contacto → pestaña **"Ficha Comercial"**
2. En "Información Comercial", establecer **"Objetivo visitas/año"** (ej: 12 = 1 visita/mes)

### 3. Configurar Reglas de Seguimiento (Solo Managers)

1. Ir a **Ventas → Configuración Comercial → Reglas de Seguimiento**
2. Las reglas por defecto ya están creadas:

| Al completar... | Se programa... | En X días |
|-----------------|----------------|-----------|
| Visita Comercial | Seguimiento | 7 |
| Demo | Seguimiento | 3 |
| Demo | Llamada Comercial | 14 |
| Formación | Seguimiento | 30 |
| Llamada Comercial | Seguimiento | 7 |
| Presentación | Seguimiento | 7 |

3. Puedes añadir, modificar o desactivar reglas desde la lista editable.

---

## Mis Clientes (Portfolio)

**Acceso:** Ventas → Mis Clientes

Vista de todos los clientes asignados al comercial actual. Disponible en dos modos:

### Vista Kanban (por defecto)
Cada tarjeta muestra:
- **Nombre** y ciudad
- **Puntuación** (badge azul)
- **Días sin visita** y **visitas YTD vs objetivo**
- **Alertas** (badges de color):
  - Rojo: "Sin visitar" (>60 días)
  - Naranja: "En declive"
  - Verde: "Cross-sell"
- **Botones rápidos**: "Visita" / "Llamada"

### Vista Lista
Columnas: Nombre, Ciudad, Puntuación, Días sin visita, Volumen, Tendencia, Cross-sell, Próxima Actividad, Visitas YTD.

### Filtros disponibles
- **Mis Clientes** (activo por defecto)
- **Visitas Vencidas** — clientes sin visitar > 60 días
- **En Declive** — tendencia de compra en declive
- **Oportunidad Cross-sell** — potencial de venta cruzada

### Agrupaciones
- Por Comercial
- Por Ciudad

---

## Ficha Comercial del Contacto

Al abrir cualquier contacto con comercial asignado, la pestaña **"Ficha Comercial"** muestra:

### KPIs (tarjetas superiores)
1. **Puntuación** — Score comercial (0-100)
2. **Días sin visita** — Con código de color:
   - Verde: < 30 días
   - Amarillo: 30-60 días
   - Rojo: > 60 días
3. **Visitas este año** — Formato "X / Y" (realizadas / objetivo)

### Alertas
Badges visibles solo cuando aplican:
- **Sin visitar** (rojo) — > 60 días sin visita
- **En declive** (naranja) — tendencia de compra en declive/inactivo
- **Oportunidad cross-sell** (verde) — tiene tags de oportunidad

### Acciones Rápidas (botones)
- **Registrar Visita** (primario) — abre wizard de registro rápido con tipo=Visita
- **Registrar Llamada** — abre wizard con tipo=Llamada
- **Programar Actividad** — abre formulario de evento calendario
- **Ver Calendario** — abre calendario filtrado por este contacto

### Información Comercial
- Comercial asignado
- Objetivo de visitas/año
- Próxima actividad (fecha y tipo)
- Última actividad completada

### Historial
Lista de todos los eventos comerciales con:
- Nombre, Tipo, Fecha, Estado (badge de color), Responsable, Feedback
- Decoración de filas por estado (rojo=vencida, amarillo=hoy, verde=realizada, azul=planificada)

### Stat Button
Botón **"Act. Comerciales"** en la cabecera del contacto que abre el calendario filtrado.

---

## Registro Rápido de Actividad

**Acceso:** Ventas → Registro Rápido (o desde botones en Ficha Comercial / Kanban de Mis Clientes)

### Modo Individual
1. Seleccionar **Cliente**
2. Seleccionar **Tipo de actividad** (Visita, Llamada, Demo, etc.)
3. **Fecha** (por defecto: ahora)
4. **Notas** (opcional, texto libre)
5. Click en **"Registrar"**

**¿Qué ocurre al registrar?**
- Se crea un evento en el calendario marcado como **completado**
- Se disparan las **cadenas de seguimiento** automáticamente
- Se actualiza la fecha de última actividad en el contacto

### Modo Lote (fin de día)
1. Cambiar a modo **"Lote"**
2. Añadir filas: Cliente | Tipo | Fecha | Notas
3. Click en **"Registrar Todo"**

Ideal para comerciales que registran todas las visitas del día de golpe.

---

## Cadenas de Seguimiento Automáticas

Las cadenas de seguimiento crean actividades automáticamente cuando se completa una actividad comercial.

### Ejemplo práctico
1. Comercial realiza una **Demo** al cliente "Clínica ABC"
2. Registra la demo (por registro rápido o marcándola como hecha)
3. **Automáticamente** se crean:
   - **Seguimiento** programado en 3 días (evento en calendario)
   - **Llamada Comercial** programada en 14 días (evento en calendario)

### Configuración
Ir a **Ventas → Configuración Comercial → Reglas de Seguimiento**

Cada regla define:
- **Cuando se completa:** Tipo de actividad disparadora
- **Programar actividad:** Tipo de seguimiento a crear
- **Días después:** Plazo para la nueva actividad
- **Crear evento en calendario:** Si crear también el evento (recomendado)
- **Resumen:** Plantilla del nombre (usar `{partner}` para el nombre del cliente)

---

## Planificador Inteligente de Visitas

**Acceso:** Ventas → Planificador de Visitas

Wizard que analiza todos tus clientes y sugiere a quién visitar primero, ordenados por prioridad.

### Filtros
- **Comercial** (por defecto: usuario actual)
- **Puntuación mínima** — solo clientes con score >= X
- **Solo vencidas** — solo clientes sin visitar > 60 días
- **Solo en declive** — solo clientes con tendencia en declive
- **Solo con oportunidad** — solo clientes con cross-sell potencial
- **Máximo resultados** (por defecto: 20)

### Algoritmo de Priorización (0-100 puntos)

| Factor | Puntos |
|--------|--------|
| Sin visita > 6 meses | +30 |
| Sin visita > 3 meses | +25 |
| Sin visita > 2 meses | +15 |
| Sin visita > 1 mes | +10 |
| Tier Platinum | +25 |
| Tier Gold | +20 |
| Tier Silver | +15 |
| Tier Bronze | +10 |
| Tendencia en declive | +20 |
| Tendencia inactivo | +15 |
| Oportunidad cross-sell | +15 |
| Recencia compra degradada | +5 a +10 |

### Resultados
Lista con: Selección, Cliente, Prioridad, Motivo, Score, Días sin visita.
- Los de alta prioridad (>= 50) se auto-seleccionan
- Decoración roja para prioridad >= 70, naranja para >= 40

### Acción
Click en **"Programar Visitas Seleccionadas"** → crea eventos de tipo "Visita Comercial" en el calendario, uno por día a partir de mañana.

---

## Puntuación Comercial

La puntuación comercial (0-100) se recalcula diariamente por un cron automático. Se compone de:

| Componente | Peso | Fuente |
|-----------|------|--------|
| **Volumen de compra** | 25 pts | Tag de volumen (Platinum=25, Gold=20, Silver=15, Bronze=10, Starter=5) |
| **Tendencia** | 20 pts | Tag de tendencia (Crecimiento=20, Nuevo=18, Recuperado=15, Estable=12, Declive=5, Inactivo=0) |
| **Recencia de compra** | 20 pts | Tag de actividad (0-3m=20, 3-6m=15, 6-12m=10, 12-24m=5, +24m=0) |
| **Frecuencia** | 15 pts | Tag de frecuencia (Recurrente=15, Regular=10, Ocasional=5, Compra única=2) |
| **Cross-sell** | 10 pts | Tags de cross-sell (5 pts por tag, máx 10) |
| **Frescura visita** | 10 pts | Días desde última visita (<30d=10, 30-60d=7, 60-90d=4, >90d=0) |

---

## Alertas Automáticas

### Alerta: Sin visitar (rojo)
Se activa cuando `days_since_last_visit > 60`. Visible en Ficha Comercial y Kanban de portfolio.

### Alerta: En declive (naranja)
Se activa cuando el tag de tendencia del contacto es "Declive" o "Inactivo".

### Alerta: Oportunidad cross-sell (verde)
Se activa cuando el contacto tiene al menos un tag de cross-sell.

---

## Crons y Automatizaciones

| Cron | Frecuencia | Descripción |
|------|------------|-------------|
| **Notificar actividades vencidas** | Diario (07:00) | Envía notificación al responsable de eventos comerciales vencidos |
| **Recalcular puntuaciones comerciales** | Diario (06:00) | Recalcula score, días sin visita, visitas YTD y alertas para todos los contactos con comercial asignado. Procesa en lotes de 100 |
| **Avisar clientes sin visitar** | Semanal (lunes 07:00) | Notifica a cada comercial la lista de clientes con objetivo de visitas que llevan > 60 días sin visitar |

---

## Referencia Técnica

### Nuevos Modelos

| Modelo | Tipo | Descripción |
|--------|------|-------------|
| `commercial.followup.rule` | Modelo regular | Reglas de seguimiento automático |
| `commercial.quick.log` | TransientModel | Wizard de registro rápido |
| `commercial.quick.log.line` | TransientModel | Líneas del wizard de registro lote |
| `commercial.visit.planner` | TransientModel | Wizard planificador de visitas |
| `commercial.visit.planner.line` | TransientModel | Líneas del planificador |

### Campos Añadidos a `res.partner`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `commercial_user_id` | Many2one(res.users) | Comercial asignado |
| `commercial_score` | Float | Puntuación 0-100 |
| `days_since_last_visit` | Integer | Días desde última visita |
| `visit_frequency_target` | Integer | Objetivo visitas/año |
| `visit_count_ytd` | Integer | Visitas completadas este año |
| `commercial_alert_overdue` | Boolean | Alerta: sin visitar |
| `commercial_alert_declining` | Boolean | Alerta: en declive |
| `commercial_alert_opportunity` | Boolean | Alerta: oportunidad cross-sell |

### Campos existentes (v1)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `commercial_event_ids` | One2many(calendar.event) | Eventos comerciales vinculados |
| `commercial_event_count` | Integer (computed) | Número de eventos |
| `next_commercial_activity_date` | Date (computed, stored) | Fecha próxima actividad |
| `next_commercial_activity_type` | Char (computed, stored) | Tipo próxima actividad |
| `last_commercial_activity_date` | Date (computed, stored) | Fecha última actividad |

### Menús (bajo Ventas)

| Menú | Secuencia | Grupo |
|------|-----------|-------|
| Mis Clientes | 4 | Comerciales |
| Calendario Comercial | 5 | Comerciales |
| Registro Rápido | 6 | Comerciales |
| Planificador de Visitas | 7 | Comerciales |
| Configuración Comercial → Reglas de Seguimiento | 90 | Managers |

### Seguridad

| Regla | Grupo | Efecto |
|-------|-------|--------|
| Eventos comerciales propios | Comerciales | Solo ven sus propios eventos comerciales |
| Eventos comerciales todos | Managers | Ven todos los eventos |
| Reglas seguimiento (lectura) | Comerciales | Solo lectura |
| Reglas seguimiento (CRUD) | Managers | Control total |

### Estructura de Archivos

```
commercial_calendar/
├── __init__.py
├── __manifest__.py
├── data/
│   ├── commercial_activity_type_data.xml    (6 tipos de actividad)
│   ├── calendar_event_type_data.xml         (6 tipos de evento calendario)
│   ├── commercial_followup_data.xml         (6 reglas de seguimiento)
│   └── commercial_cron_data.xml             (3 cron jobs)
├── models/
│   ├── __init__.py
│   ├── calendar_event.py                    (extensión de calendar.event)
│   ├── commercial_followup_rule.py          (modelo de reglas)
│   ├── mail_activity.py                     (cadenas de seguimiento)
│   └── res_partner.py                       (campos y lógica comercial)
├── security/
│   ├── commercial_calendar_security.xml     (record rules)
│   └── ir.model.access.csv                  (ACL)
├── static/src/
│   ├── scss/commercial_calendar.scss
│   └── views/ (JS + XML de renderizado calendario)
├── views/
│   ├── calendar_event_views.xml
│   ├── commercial_calendar_menu.xml
│   ├── commercial_followup_rule_views.xml
│   ├── commercial_portfolio_views.xml
│   └── res_partner_views.xml
└── wizard/
    ├── __init__.py
    ├── commercial_quick_log.py
    ├── commercial_quick_log_views.xml
    ├── commercial_visit_planner.py
    └── commercial_visit_planner_views.xml
```
