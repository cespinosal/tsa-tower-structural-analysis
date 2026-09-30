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

## Pierna explícita de antenas ahora controla la carga real — HECHO (`04a841c`, 2026-09-24)

El dropdown de pierna (P1/P2/P3) en la tabla de antenas ya existía pero solo afectaba el
dibujo en el visor 3D (`renderAntenas3D`) — la carga real de viento/peso (flechas 3D y
export STAAD) ignoraba `a.pierna` y recalculaba automáticamente la pierna "más cercana por
azimut" (`_nearestLegNodeByAz`), pudiendo aplicar la carga en una pierna distinta a la que
el usuario eligió. Corregido con `_legNodeForPierna()`/`_legNodeForLoad()` — usan la pierna
explícita si está definida, si no caen al automático de siempre. `_calcAntennaForces()` y
`_calcHerrajeWindForces()` ahora devuelven `pierna` en cada objeto.

Verificado en navegador: forzar pierna cambia el nodo STAAD real (viento y peso); antenas
sin pierna elegida no cambian de comportamiento. **No verificado en vivo** (mismo patrón de
código, no debería fallar, pero no se probó): la ruta de herrajes (`_calcHerrajeWindForces`)
con pierna explícita, ni un proyecto monopolo/atirantado con `mastType==='mast-guyed'`.

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

## Empalme de pierna a media bahía — planeado, no implementado (2026-09-24)

El usuario mostró un plano real (torre celosía, 4 puntos "CORTE 1-1..4-4" marcados donde
cambia el perfil de pierna) donde el empalme **no cae en el límite de un tramo**, sino a
media altura de lo que hoy sería una sola bahía de celosía (el patrón ahí es un X grande
que cruza 2 niveles con una horizontal intermedia — el empalme cae justo en esa horizontal
intermedia, no en el cruce principal de la diagonal).

**Hoy esto no se puede modelar**: `secData[i].M`/`MCal` (perfil/calidad de pierna) es UN
solo valor por tramo completo, aplicado a todos los miembros de pierna de ese tramo sin
importar cuántas bahías tenga.

**Buena noticia para cuando se retome**: la geometría YA genera la pierna partida en cada
punto de cruce de diagonal dentro de una bahía — no es un miembro monolítico por tramo.
Ver `addMembersWithSecs()` (`app/web/viewer.html`, ~línea 3774): `legCuts` ya trae cada
corte de pierna como nodo/miembro independiente (`members.push({ni:prev, nj:c, type:'leg',
sec})` en un loop). El problema es solo de ASIGNACIÓN de perfil (siempre `secData[sec].M`
para todo el tramo `sec`), no de geometría — la pieza que falta es un mecanismo para
asociar un perfil distinto a partir de un corte de pierna específico dentro del tramo.

**Bloqueador:** se le preguntó al usuario cómo prefiere capturar el punto de empalme (por
altura absoluta desde la base, buscando el nodo de corte más cercano, vs. por tramo+bahía
específica) — pidió dejarlo para una investigación más a fondo más adelante, sin decidir
todavía. No implementar nada de esto sin retomar esa conversación primero.

## Sistema de temas claro/oscuro — HECHO (2026-09-25)

Se completó la transición de todos los elementos hardcoded a un sistema de tokens CSS
(`--bg-main`, `--txt-pri`, `--border`, etc.) con doble paleta (dark por defecto,
light vía `[data-theme="light"]`).

Cambios clave:
- **`buildGrid()`**: ya detecta el tema y usa colores para la malla 3D
  (oscuro: `0x1E3A5F`/`0x1E6FBE`; claro: `0xC8D8EC`/`0x5E90C0`). `refreshGrid()` se
  llama desde `toggleTheme()` y desde `applyAppSettings()` → la malla siempre es consistente.
- **`applyAppSettings()`**: ya respeta el tema actual para `scene.background`; solo aplica
  `appSettings.bgColor` en modo oscuro, y `#EEF3FA` en modo claro.
- **Vista en Planta (`_fdDrawPlan`)**: paleta JS theme-aware (`_planBg`, `_planGrid`,
  `_planBord`, `_planLbl`, `_planInner`); azimut de torre integrado (`ctx.rotate(_planAzRad)`);
  indicador de Norte; etiquetas de cara visibles en ambos temas.
- **Editor de paquetes de feeders**: botones ✕ y `+ cable` usan `var(--txt-sec)` en vez de
  `var(--txt-dim)` — visibles en modo oscuro.
- **Botón Guardar en modal de configuración**: usa `.btn-apply` con `var(--btn-pri)` en vez de
  `var(--btn)` (que nunca estuvo definido → botón transparente en modo claro).
- **Color de tramos impares**: default cambiado de `#CCEEFF` (invisible en claro) a `#1A90CC`;
  migración automática en `loadAppSettings()` para proyectos con el valor viejo cacheado.
- **Etiquetas de colores** en el panel de configuración: renombradas como
  "Color tramos pares/impares (piernas/diag.)" para hacerlas descriptivas.

**Bug a no reintroducir:** `replace_all` con un hex hardcodeado (`#172a45`) puede
sustituir dentro de la declaración `const _planInner = ... : '#172a45'` creando una
auto-referencia. Si se hacen sustituciones masivas de hex en `_fdDrawPlan`, excluir
las propias declaraciones de variables.

## Paquetes de feeders — mejoras y correcciones (2026-09-28)

### Editor de Paquete
- Ventana más alta: `max-height` de 88 vh → 96 vh; grid de 340 px → 440 px.
- Nueva fila **N / T** (dimensiones proyectadas del rectángulo tangente) visible para
  paquetes no-cluster. Usa la misma fórmula que el dibujo real:
  - **N** = Σ(diáms de la columna más profunda) + (nCables−1)×2 mm
  - **T** = Σ(maxDiám de cada columna) + (nCols−1)×2 mm  ← usa el diámetro real de
    cada columna, no el máximo global uniforme.
- La fila Dc (cluster) y la fila N/T (no-cluster) se excluyen mutuamente.

### Tabla de feeders
- Columna "Ø MM" de paquetes no-cluster ahora muestra `N 85 · T 87 mm` en vez de
  solo los tipos de cable.

### Renderizado 3D de columnas en paquete
- Paso entre columnas ahora es variable (depende de los diámetros adyacentes, no de
  `maxD` global): centra cada columna con `colX[i] = colX[i-1] + (d_{i-1}+d_i)/2 + 2mm`.
- El rectángulo visual en 3D coincide exactamente con el N/T reportado.

### Separación entre cables en paquete
- `PAQ_GAP = 2 mm` (superficies), igual que cluster TIA-222-H Fig. 2-14.
- Los feeders individuales no-paquete conservan `CABLE_GAP = 20 mm`.

### Fix: aislamiento de feeders y antenas con dado
- `_isoMinZ/_isoMaxZ` en `_renderFeeders3D` y en el filtro de antenas ahora arrancan
  desde `dadoHeight` (en vez de 0). Antes el clip de feeders no coincidía con los nodos
  de la torre cuando `dadoHeight > 0`.

## Tooltips en QWebEngineView — patrón definitivo (2026-09-30)

El atributo `title` nativo en botones interactivos aparece en la esquina superior de la
ventana en QWebEngineView, no junto al elemento. Regla: **nunca usar `title` en botones**.

- **Sidebar (`.side-btn`)**: `<span class="side-tip">Texto</span>` dentro del botón.
  CSS ya existe — aparece a la derecha al hover.
- **Topbar (`.btn`)**: envolver en `<span class="has-tb-tip">`, con
  `<span class="tb-tip">Texto</span>` como hermano. CSS `.has-tb-tip`/`.tb-tip` añadido
  en esta fecha — aparece debajo del botón, alineado a la derecha.

Aplicado a `#solver-btn` (sesión anterior) y `#btn-theme` (2026-09-30).

**Re-renderizar la torre:** usar siempre `refresh()`, nunca `renderTower(data)` directamente.
`refresh()` llama `generateTower(getConfig())` + `renderTower()` y verifica `projectGenerated`.

## Auto-ajuste de color de tramos pares al cambiar tema (2026-09-30)

`toggleTheme()` ahora actualiza `appSettings.colors.leg = _legColorDefault()` después de
aplicar el nuevo `data-theme`, guarda en localStorage, actualiza el color picker si el modal
de configuración está abierto, y llama `refresh()`. La función `_legColorDefault()` ya es
theme-aware — devuelve `#FFFFFF` en oscuro y `#1A6EC0` en claro.

## Colores de sección — defaults y bug de paridad (2026-09-30)

- Tramos pares (`colors.leg`): blanco en tema oscuro, azul (`#1A6EC0`) en tema claro.
- Tramos impares (`colors.ring`): rojo (`#FF2233`) en ambos temas.
- **Bug corregido:** la sección 0 (base de la torre) se renderizaba en blanco en vez de
  rojo. Causa: clave de batch usaba `m.sec%2` — sección 0 daba paridad 0 (tramos pares).
  Fix: `(m.sec+1)%2` — sección 0 da paridad 1 (tramos impares = rojo). ← no reintroducir.
- **Monopolo sólido**: mismo criterio — `(p0.sec ?? 0) % 2 === 0 ? C_RING() : C_LEG()`.

## Export STAAD — correcciones de fuerzas de viento (2026-09-30)

### Fix: z y ancho de cara en `_wlSecs`
`_wlSecs` (precálculo del export) tenía dos errores vs. `buildCargasVientoPanel`/`_renderWindAngleTable`:
1. `zMid` para `calcSectionWindForce` (presión Kz) no incluía el offset de rooftop (`_rooftopZ`).
2. `fw` para `_faceWidthAt` incluía `dadoHeight` — ancho de cara incorrecto en torres con dado > 0 ahusadas.

Ahora usa tres variables paralelas: `_wlZabs` (z absoluta para presión, con rooftop+dado),
`_wlZtower` (z relativa a base de torre para ancho de cara), `_wlZ3D` (z en espacio 3D
para filtrar nodos). Coincide exactamente con `buildCargasVientoPanel`.

### PERFORM ANALYSIS PRINT ALL
Agregado justo antes de `FINISH` en el .std.

## Fuerzas de viento: feeders + CGO + escalerilla sumadas a FST (2026-09-30)

Las fuerzas de coaxiales, CGO y escalerilla ahora se suman a la fuerza estructural (FST)
tanto en el panel de TSA como en el export STAAD.

### Panel "Cargas de Viento"
- `_renderWindAngleTable`: tres columnas finales: **FST** (estructura), **FC** (feeders+CGO+escal),
  **FTotal = FST+FC**. El TOTAL al pie muestra las tres.
- Nueva sección **"FUERZA EN CGO Y ESCALERILLA"** (container `cgo-escal-force-table-container`)
  debajo de "FUERZA EN COAXIALES". Mismas columnas pero solo filas de CGO/escalerilla.
- "FUERZA EN COAXIALES" ahora muestra solo feeders/coaxiales.

### Export STAAD (`_emitWindLoad`)
Antes de escribir el JOINT LOAD, calcula `_calcFeederWindForces(cfg, windData, angleDeg, vKmhOverride)`
y suma `totalF_kgf` de feeders+CGO+escal al `F_kgf` estructural por sección. El caso de
servicio usa la misma `vKmhOverride` que las demás fuerzas.

### Cambios de soporte
- `_calcFeederWindForces`: acepta `vKmhOverride` (4° parámetro), lo pasa a `calcWindPressure`.
- Cada fila ahora incluye `srcType: 'feeder' | 'cgo' | 'escal'` para poder filtrar por tabla.
- `_renderCgoEscalForceTable`: nueva función; se llama desde `buildCargasVientoPanel` y `_onWindAngleSelect`.

## Convención de caras A/B/C en torre triangular — CAMBIADA (2026-09-25)

La cara **A** es ahora la cara inferior del triángulo (paralela al eje X, normal hacia el
Sur, 180°). Antes era la cara superior-derecha (60°).

Ciclo: B→A, C→B, A→C (la cara que era B pasó a ser A, etc.)

| Cara | Normal (brújula) | Posición en planta |
|------|------------------|--------------------|
| A    | 180° (Sur)       | Base inferior (paralela a X) |
| B    | 300°             | Superior-izquierda |
| C    | 60°              | Superior-derecha |

Archivos actualizados:
- `faceVectors()` (feeder renderer): `{A: -Math.PI/2, B: 5*Math.PI/6, C: Math.PI/6}`
- `_fdDrawPlan()`: `midLabel(0,1,'C'); midLabel(1,2,'A'); midLabel(2,0,'B')` + `faceMid` ajustado
- `_updateAntAddAngles()`: default triangular ahora `(180 + 120*i) % 360` → 180°, 300°, 60°
- Comentario en `genTriangular()` actualizado

**Nota:** proyectos existentes con feeders/antenas asignados a cara A/B/C conservan el
string pero ahora apuntan a la nueva cara — revisar y reasignar si es necesario.
