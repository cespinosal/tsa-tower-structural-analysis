# Contexto del proyecto (TSA — Tower Structural Analysis)

Este archivo es la fuente de verdad **compartida entre máquinas** (VM y equipo de casa)
sobre el estado del proyecto. Viaja con git (`pull`/`push`/`clone`), a diferencia de la
memoria local de Claude Code (que vive en `~/.claude/` de cada máquina y no se sincroniza
sola). Actualízalo al cerrar cada bloque de trabajo relevante.

## Archivo fuente de verdad del código

- **`app/web/viewer.html`** es el archivo activo — todos los cambios de código van ahí.
- **`TSA.html`** (raíz del repo) está **deprecado**, sin commits de features desde hace
  semanas. No editarlo salvo que se pida explícitamente revivirlo.
- **`index.html`** (raíz) es una copia sincronizada manualmente de `viewer.html` para
  GitHub Pages. Después de editar `viewer.html`, preguntar si también hay que copiar el
  cambio a `index.html` antes de dar la tarea por terminada.

## Bugs corregidos que no deben reintroducirse

- **Monopolo Combinado — `nInc`/`nStr`**: debe ser un conteo **fijo**, fijado al crear la
  torre (flyout Cónico/Escalonado/Combinado), nunca re-derivado de `alturaInclinada` como
  se hace en torres convencionales (cuadrada/triangular/atirantada). Si aparece un bug tipo
  "el cono se come tramos que deberían ser de diámetro constante", revisar `getConfig()`
  (¿sigue leyendo `nInc` como valor fijo del DOM?) y cualquier ruta que borre/inserte
  tramos (`deleteSeccion()`, `insertSeccion()`) — cada una debe actualizar `nInc`/`nStr`
  o los tramos nuevos quedan fuera de `nTot` y no se dibujan.

## Sistema de unidades MKS/IMP — estado: extendido end-to-end, COMMITEADO

Se extendió el toggle MKS/IMP (antes solo cubría dimensiones generales/tramos/viento) a
**toda la app**: antenas, retenidas/anclajes, feeders/CGO/escalerilla, visor 3D, memoria
de cálculo HTML, export DOCX y export STAAD (`UNIT FEET KIP` completo en IMP, no solo
fuerzas). Commits: `29cd3f2`, `bd382b0` (2026-09-23).

Reglas de diseño aplicadas:
- El motor de cálculo (`getConfig()`, `secData`, `windData`, `calcWindPressure`, etc.)
  siempre trabaja en metros/kg/kgf/km-h. La conversión ocurre solo en la frontera de
  captura/presentación vía `uConv`/`uConvInv`/`uLabel`/`isImperial()`.
- Los catálogos MAESTROS compartidos entre proyectos (perfiles IMCA/AISC, calidades de
  acero, catálogo de cables, SectionBuilder) **no se convierten** — se quedan en su
  unidad nativa de captura/edición.
- Las fórmulas narrativas con coeficientes calibrados en SI (qz, Ke, Gh) se dejan sin
  tocar; solo se convierten las tablas de resultados alrededor de ellas.

**Pendiente** (no confirmado que se haya hecho):
- Pruebas en navegador (Playwright) cubriendo antenas, retenidas, feeders/CGO/escalerilla,
  memoria de cálculo HTML, export DOCX (abrir el archivo generado) y export STAAD en modo
  IMP (confirmar `UNIT FEET KIP` y coordenadas convertidas).
- Decidir si el picker de perfiles debe sugerir por defecto la pestaña AISC cuando IMP
  está activo (mejora menor, no implementada).

## Módulo K-factor por patrón de arriostramiento — planeado, no implementado

Módulo que asignaría K/KL·r por miembro de celosía (piernas, diagonales, horizontales)
según TIA-222-H §4.5 (tablas 4-3/4-4/4-5), en vez de correr un análisis de estabilidad.
TSA ya captura el patrón de bracing por sección (`DIAG_PATTERNS`, `HIP_BRACING_DEFS`,
`PLAN_BRACING_PATTERNS`).

**Bloqueador:** no fabricar/adivinar los valores numéricos de las tablas — es dato de
seguridad estructural. Falta que el usuario aporte el texto/valores exactos de las
Tablas 4-3/4-4/4-5 antes de escribir cualquier número real en el código.

También pendiente de decidir: cómo modelar la condición de extremo (1 bulón vs.
2+ bulones/soldado — TIA-222-H dice que cambia la restricción a rotación). El resultado
del cálculo debe inyectarse también en `exportSTAAD()`, no solo como reporte informativo.
