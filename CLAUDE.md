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

**Pruebas Playwright (2026-09-24): 5/7 pasaron, 1 bug sistémico encontrado y corregido.**
Antenas, retenidas/feeders (valores), export DOCX, export STAAD (`UNIT FEET KIP` OK) y
regresión a MKS: todo correcto. **Bug encontrado:** en tablas/paneles generados por JS
(Cargas de Viento, retenidas, feeders/CGO, memoria de cálculo HTML) el valor se convertía
bien a imperial pero la ETIQUETA de unidad quedaba fija en métrico —
`<span class="unit-len">m</span>` en vez de `${uLabel('len')}` — un valor en pies mostrado
como si fuera metros. **Corregido en `0451846`**, 93 ocurrencias, verificado en navegador
tras el fix (ASNM, retenidas y memoria HTML ya muestran ft/lb/psf en IMP sin residuos al
volver a MKS).

**Nota para quien retome esto:** si hace falta volver a hacer un fix mecánico de este tipo
(buscar/reemplazar texto dentro de `app/web/viewer.html`, que es ~1 MB de JS embebido en
`<script>`), **usar un tokenizer JS real** (`acorn`, instalable con `npm install acorn` —
hay acceso a red desde esta VM) para saber si una posición está dentro de un template
literal vs. un string simple, NO un tokenizer de comillas hecho a mano. Un intento con
tokenizer casero en esta misma sesión se equivocó silenciosamente en una zona con mucha
concatenación de strings (`'...' + fn() + '...'`), clasificando contenido de un template
literal como si fuera un string de comillas simples — se detectó a tiempo (antes de
commitear) por una inspección manual, no automáticamente.

**Picker de perfiles — HECHO (`bf66c13`, 2026-09-24):** sin perfil previo, abre en AISC
en modo IMP / IMCA en MKS. La tabla del picker (área, peso, diámetro/espesor/d/tw) ahora
muestra ambos catálogos convertidos a in²/lb-ft/in cuando IMP está activo (antes siempre
mostraba cm²/kg-m/cm sin importar el modo). Importante para quien toque esto después:
está separado en `_pickerMetric()` (SIEMPRE cm²/kg-m/cm, la usa `_profileWeightPerMeter()`
para sumar peso real de mástil apuntalado / steel takeoff — nunca condicionar esta función
a `isImperial()`) y `_pickerMetricDisplay()` (nueva, solo pinta la tabla del picker, nunca
alimenta un cálculo). Verificado en navegador que `_profileWeightPerMeter()` da el mismo
valor exacto en MKS e IMP.

**Artefacto preexistente detectado de paso (no corregido, prioridad baja):** el total del
steel takeoff (`_reportSteelTakeoff().total`) varía ~0.002% entre MKS/IMP — no por peso o
longitud de perfil (confirmados idénticos), sino por el redondeo `toFixed(3)` en pies de
`baseW`/`topW` en `_convDomLen()`, que afecta levemente el `faceWidth` interpolado usado
para longitud de diagonales. Magnitud despreciable para ingeniería estructural.

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
