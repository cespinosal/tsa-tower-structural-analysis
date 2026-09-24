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

## Audit TIA-222-H — combinaciones de carga y viento (COMMITEADO, con pendiente detectado)

Segundo audit de fórmulas normativas (2026-09-24, commits `4d878d5` y `135b375`), continuación
del de ayer (6 hallazgos en `9194a6c`). Corregido:
- `_renderWindAngleTable_Monopole` (tabla "Cargas de Viento" + flechas 3D vía `_monoSecW`) no
  aplicaba Tabla 2-8a (herrajes lineales/feeders) aunque `computeNodalWindForces_Monopole` sí —
  mismo patrón de "fix a medias" documentado abajo.
- Export STAAD generaba 3 combinaciones de carga **hardcodeadas**, ignorando el panel
  "Combinaciones de Carga" (`_lcCombis`): si el usuario desactivaba una combinación o agregaba
  una personalizada, nunca llegaba al `.std`. Ahora STAAD, la memoria HTML (cap. 7) y el DOCX
  leen todos de `_lcCombis` vía la misma función `_lcAppliesToType()`.
- LC2/LC5 (0.9·D..., §2.3.2-(2)/(5)) tenían la nota "Solo autosoportadas" pero se exportaban
  para todos los tipos. Confirmado con el usuario: **sí aplican** a autosoportadas, monopolo y
  mástil apuntalado (`monopole` + `mastType==='mast-guyed'`) — **no aplican** a atirantadas
  (`cfg.type==='guyed'`). Esto quedó como el campo `excludeGuyed` en `_LC_TIA222H`.

**Patrón de bug a vigilar en este código** (ya visto 2 veces — hallazgo #10 de ayer y el de
`_renderWindAngleTable_Monopole` arriba): la misma fórmula/criterio normativo vive duplicada en
2+ rutas (cálculo real para STAAD/3D vs. tabla de reporte en pantalla/memoria/DOCX). Al corregir
un hallazgo de este tipo, buscar TODOS los call sites de la función involucrada antes de dar el
fix por cerrado.

**Corregido (commits posteriores, mismo día `7b68b38`/`ee79a9d`):** la combinación de servicio
SLC1 en STAAD reutilizaba las fuerzas de viento ÚLTIMO en vez de aplicar una velocidad de
servicio real. `_emitWindLoad` ahora recibe `vKmhOverride` + los arreglos de fuerzas de antena/
herraje correspondientes; el caso SERVICIO usa `windData.velOperacional` (misma fuente que la
memoria, cap. 6.2) vía `_calcAntennaForces`/`_calcHerrajeWindForces`, a los que también se les
agregó soporte de `vKmhOverride`. Si `velOperacional` no está capturado, el fallback es **60 mph
= 96.56 km/h** (fijado por TIA-222-H §2.8.3, no la velocidad última) y se deja un `* AVISO`
explícito con el valor real usado en el .std.

Sin hallazgos nuevos en `calcWindPressure`/`_tiaKz`/`_tiaKzt`/`_tiaKe`/`_tiaKd`, Cf de celosía
(`_cfFromEpsilon`/`_tiaDfDr`) ni EPA de antenas/dish — ya se revisaron a fondo. Hielo y sismo
siguen sin implementar (declarado "Pendiente" en el propio reporte, no es un bug oculto).

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
