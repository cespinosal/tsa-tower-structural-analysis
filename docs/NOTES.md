# Notas de proyecto

Notas de contexto entre sesiones/máquinas que no encajan como comentario de código.
Cuando una nota queda resuelta o implementada, bórrala de aquí.

## Módulo K/KL·r por patrón de arriostramiento (planeado, no implementado) — 2026-08-25

Pregunta origen: ¿se necesita un análisis de estabilidad para determinar los
coeficientes K de arriostramiento en la celosía? Respuesta (verificada contra el texto
de TIA-222-H en otra conversación): no — a diferencia de un edificio, en torres
reticuladas K y KL/r salen de tablas prescriptivas (§4.5), no de un análisis numérico de
pandeo:

- Piernas (§4.5.1): K = 1.0 mínimo, Tabla 4-3.
- Diagonales/montantes (§4.5.2): KL/r de la Tabla 4-4 (o 4-5 si son miembros redondos
  soldados directo a la pierna), según el patrón de arriostramiento y la restricción en
  los extremos.
- Un solo bulón NO cuenta como restricción parcial a la rotación — hacen falta 2+
  bulones o soldadura.
- Límites recomendados de KL/r: 150 piernas, 200 compresión principal, 250 secundarios,
  300 tensión (§4.4.2).

TSA ya captura el dato clave para automatizar esto: el patrón de bracing por sección
(`DIAG_PATTERNS` en `app/web/viewer.html:19080` — X, X-50/25Pct, K, K-Rev,
K-50/33/25Pct + variantes Rev/2, Staggered, Staggered-50Pct, Z, Z-50Pct; ver también
`HIP_BRACING_DEFS` y `PLAN_BRACING_PATTERNS`). Mapeo lógico borrador (sin números aún):

| Patrón TSA | Categoría §4.5.2 |
|---|---|
| X, X-50Pct, X-25Pct | Diagonales cruzadas conectadas en el cruce (Lcr = mitad de la diagonal) |
| K, K-Rev | Diagonal en K a horizontal de tope |
| K-50/33/25Pct (+Rev, +variante 2) | Igual que K pero con más quiebres — un K/KL·r por segmento |
| Staggered, Staggered-50Pct | Diagonal simple sin redundancia a media altura |
| Z, Z-50Pct | Diagonal simple en Z, sin punto medio restringido |

**Bloqueador:** no fabricar/adivinar los valores numéricos de las Tablas 4-3/4-4/4-5 —
falta pegar el texto/valores exactos de la norma antes de escribir números reales en
el código.

**Decisiones ya tomadas, pendientes de ejecutar:**
- Condición de extremo (1 bulón vs. 2+/soldado): aún no se implementa, no se ha
  decidido si usar placeholder conservador (1 bulón en todos los miembros) o agregar ya
  un campo por miembro en `secData`.
- El resultado debe inyectarse **también en `exportSTAAD()`** como parámetro de diseño
  por miembro, no solo como reporte informativo en la Memoria de Cálculo.

Retomar solo después de conseguir el texto verificado de las tablas.
