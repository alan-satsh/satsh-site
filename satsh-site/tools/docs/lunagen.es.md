## 1. Qué es lunagen

`lunagen` simula un cultivo célula por célula (un *agente* por célula, vectorizado con NumPy) y
permite **buscar las condiciones que maximizan o minimizan lo que elijas**. Cada célula tiene una
reserva de energía, un ciclo de división propio, puede morir (por hambre, vejez o azar) y puede
producir uno o varios compuestos.

Nació de un proyecto de celulosa bacteriana (*Komagataeibacter xylinus*), y se generalizó para que
el motor **no dependa de ningún organismo**: lo específico se declara. Con eso se puede:

- optimizar la producción de celulosa, de etanol, de proteína u otra biomasa;
- medir solo el **tiempo de vida**, solo la **reproducción** o cualquier otra métrica;
- elegir con **qué variables** operar y cuáles dejar fijas;
- animar cada simulación en una ventana de estilo ciencia ficción;
- exportar los mejores resultados a CSV, JSON y XML (para Unity).

Un principio de diseño importante: las condiciones del cultivo **no actúan mientras corre la
simulación**. Se traducen **una sola vez** a *parámetros efectivos*; con ellos constantes, el motor
aplica siempre las mismas ecuaciones.

## 2. Instalación

Requisitos: Python 3.9 o superior (probado en 3.12) y NumPy.

```bash
pip install lunagen                  # núcleo
pip install "lunagen[viz]"           # + pygame-ce y scipy para la ventana en vivo
pip install lunagen-0.1.1-py3-none-any.whl     # desde el archivo .whl
```

- **pygame-ce** abre la ventana (`viz=True`). También funciona con `pygame` clásico, pero no instales
  los dos a la vez: ambos se importan como `pygame` y se estorban. `pygame-ce` suele publicar versiones
  precompiladas para los Python nuevos antes que `pygame`. Sin ninguno o sin pantalla, `optimize` sigue funcionando
  y solo imprime en consola.
- **scipy** es opcional: añade colisiones entre las cápsulas de la ventana. Sin él las células se
  pueden solapar, pero todo lo demás es idéntico.

Comprobar la instalación:

```bash
python -c "import lunagen; print(lunagen.__version__)"
lunagen --metrics
```

## 3. Inicio rápido

```python
import lunagen as lg

if __name__ == "__main__":
    organismo = lg.presets.komagataeibacter_xylinus()
    estudio = lg.Study(organismo, objective="yield[cellulose]", workers=4)
    resultado = estudio.optimize(samples=60, generations=8, population=16, viz=True)
    print(resultado.best_conditions)       # las mejores condiciones
    print(resultado.best_value)            # g/L de celulosa (validado con semillas nuevas)
```

Una simulación suelta, sin optimizar:

```python
res = estudio.simulate(temperature_c=29, ph=5.3)
print(res.product_mg["cellulose"], res.peak_alive, res.deaths_by_cause)
```

## 4. Cómo funciona

```
 Condiciones ──► Organism.derive ──► Parámetros efectivos ──► Motor (simulate) ──► SimulationResult
 (temperatura,        (leyes y                (constantes)         (agentes)               │
  pH, glucosa…)        factores)                                                            ▼
                                                                        Métricas ──► Objective ──► valor
                                                                                                    ▲
                                                           Study.optimize: línea base → exploración → refinamiento → validación
```

| Pieza | Módulo | Qué hace |
|---|---|---|
| `Organism` | `organism` | Describe el organismo: variables, factores, leyes, productos. |
| motor `simulate` | `engine` | Simula un cultivo. Determinista para una semilla. |
| métricas / `Objective` | `metrics` | Qué se mide y qué se optimiza. |
| `Study` | `study` | Une todo: simula, evalúa y optimiza, con informes y exportación. |
| ventana | `viz` | Anima cada simulación (se activa con `viz=True`). |
| `presets` | `presets` | Organismos ya descritos (*Komagataeibacter xylinus*). |
| respuestas | `responses` | Curvas combinables: `Cardinal`, `CPM`, `Saturation`… |

## 5. El modelo de simulación

Unidades: tiempo en **horas**, masa en **miligramos** (por célula), longitudes en **µm**.
En cada paso de tiempo `dt`, y para cada célula, en este orden:

1. **Metabolismo.** Con `c = nutriente_restante / nutriente_inicial`:
   `toma = uptake_rate · c/(Ks + c) · (1 − reserva/capacidad) · dt`;
   `reserva += toma · rendimiento`; `reserva −= mantenimiento · dt`.
   Si entre todas piden más nutriente del que queda, se reparte proporcionalmente.
2. **Muerte** (prioridad: hambre, vejez, azar).
   *Hambre:* reserva ≈ 0 durante `starvation_tolerance` horas.
   *Vejez:* edad ≥ `max_lifespan` (solo si `max_lifespan > 0`).
   *Azar:* probabilidad `1 − exp(−random_death_rate · dt)`.
3. **Crecimiento.** `escala = clip(reserva / (umbral · capacidad), 0, 1)`; el reloj del ciclo avanza
   `dt · escala` (más lento con poca reserva) y cuesta `growth_cost · dt · escala`. Con la población
   llena (`max_agents`) no empiezan a crecer las células que aún no iniciaron el estrangulamiento.
4. **Productos.** Para cada producto: `masa = rate · factor_individual · escala_prod · dt`, y se gasta
   `masa · cost` de reserva (nunca más reserva de la que hay).
5. **División.** Al completar el ciclo, la célula se divide en dos hijas que se reparten la reserva a
   partes iguales; la hija hereda el factor individual de producción. Si no cabe, se dividen solo
   algunas, elegidas al azar.

Toda la aleatoriedad sale de una semilla, así que **la misma semilla da exactamente el mismo
resultado**. Cada célula inicial tiene una fase distinta del ciclo y variación individual de ciclo y
de producción (`variation`), que se hereda.

## 6. Describir un organismo

Un `Organism` es una descripción **declarativa**. Mira `lunagen/presets.py` (xylinus) y
`examples/03_new_organism.py` (levadura) como modelos (vienen en el código fuente del paquete, el `.tar.gz` de PyPI).

```python
import lunagen as lg
from lunagen import Cardinal, CPM, Inhibition, Ref, Saturation

org = lg.Organism(
    name="Mi organismo",
    nutrient_label="Azúcar",                     # nombre del nutriente (solo para mostrar)
    variables=[                                  # qué se puede controlar
        lg.Variable("temperature_c", 30.0, (20, 40), "°C", "Temperatura", "{:.1f}"),
        lg.Variable("ph", 5.5, (4, 7), "", "pH", "{:.2f}"),
        lg.Variable("sugar_gl", 40.0, (10, 100), "g/L", "Azúcar", "{:.0f}"),
        lg.Variable("inoculum_pct", 5.0, (1, 15), "%", "Inóculo", "{:.1f}"),
    ],
    params=dict(base_cycle_h=2.0, base_uptake=0.04),          # números sueltos calibrables
    factors={                                                  # respuestas entre 0 y 1
        "g_temp": Cardinal("temperature_c", 10, 31, 42),
        "g_ph": CPM("ph", 3.5, 5.5, 8.0),
        "growth": Ref("g_temp") * Ref("g_ph"),
        "osmotic": Inhibition("sugar_gl", 80.0, 2),
    },
    laws={                                                     # condiciones -> parámetros
        "n_initial": lambda v: round(v["inoculum_pct"] * 40),
        "nutrient_mg": lambda v: v["sugar_gl"] * v["volume_l"] * 1000.0,
        "division_interval": lambda v: v["base_cycle_h"] / max(v["growth"], 1e-3),
        "uptake_rate": lambda v: v["base_uptake"] * v["osmotic"],
        "maintenance_rate": lambda v: 0.002,
        "random_death_rate": lambda v: 0.001 + 0.01 * (1 - v["g_temp"]) ** 2,
    },
    products=[lg.Product("biomass_x", rate=0.004, law=Ref("growth"), cost=2.0, label="Biomasa X")],
)
```

### Las partes

**`variables`** — lista de `Variable(name, default, bounds, unit, label, fmt)`. Son las condiciones que
se pueden fijar u optimizar. `bounds` son los límites de búsqueda por defecto.

**`params`** — diccionario de números sueltos que las leyes pueden leer (`v["base_cycle_h"]`). Sirven
para calibrar sin tocar las fórmulas (`org.with_params(base_uptake=0.05)`).

**`derived`** (opcional) — variables calculadas a partir de otras, por ejemplo un pH efectivo:
`derived={"ph_eff": lambda v: v["ph"] - 0.03 * max(0, v["glucose_gl"] - 10)}`.

**`factors`** — respuestas intermedias (normalmente entre 0 y 1), definidas con las
[curvas de respuesta](#7-curvas-de-respuesta). Se evalúan en orden, así que un factor puede usar los
anteriores con `Ref("nombre")`.

**`laws`** — traducen el entorno a los parámetros de la simulación. Cada ley recibe un diccionario `v`
y devuelve un número. Son **obligatorias** estas seis:

| Ley | Significado | Unidad |
|---|---|---|
| `n_initial` | células iniciales (se limita a `[1, max_agents]`) | células |
| `nutrient_mg` | nutriente total inicial del cultivo | mg |
| `division_interval` | duración del ciclo celular (tope 10 000 h) | h |
| `uptake_rate` | toma máxima de nutriente por célula | mg/h |
| `maintenance_rate` | gasto de reserva por mantenimiento | reserva/h |
| `random_death_rate` | mortalidad por azar | 1/h |

Además, **cualquier campo de `Physiology`** puede ser una ley (p. ej. `max_lifespan` ligada al pH).
Lo que ve una ley en `v`: los `params`, las variables, las derivadas, los factores y tres constantes
de la simulación: `volume_l`, `duration_h`, `max_agents`.

**`products`** — uno o varios `Product(name, rate, law, cost, variation, reserve_threshold, label, unit, color)`:

| Campo | Significado |
|---|---|
| `rate` | mg / h / célula en condiciones ideales |
| `law` | efecto del entorno que multiplica `rate` (una curva; `None` = constante) |
| `cost` | reserva consumida por cada mg producido |
| `variation` | variación individual (±), heredada por las hijas |
| `reserve_threshold` | fracción de la capacidad por debajo de la cual produce menos |
| `label`, `unit`, `color` | solo para mostrar (ventana e informes) |

El primer producto es el **principal**: es el que dibuja la ventana como fibras y el que usan por defecto
las métricas sin argumento (`"yield"` = `"yield[<primer producto>]"`).

**`physiology`** (`Physiology`) — constantes del metabolismo y del ciclo:

| Campo | Defecto | Significado |
|---|---|---|
| `half_saturation` | 0.1 | constante de saturación del nutriente (fracción del inicial) |
| `yield_coefficient` | 0.5 | reserva ganada por mg de nutriente |
| `reserve_capacity` | 0.05 | capacidad máxima de reserva |
| `initial_reserve` | 0.6 | reserva inicial (fracción de la capacidad) |
| `growth_cost` | 0.004 | reserva/h a velocidad de crecimiento completa |
| `growth_reserve_threshold` | 0.3 | umbral de reserva para crecer a pleno ritmo |
| `division_variation` | 0.2 | variación individual de la duración del ciclo (±) |
| `constriction_start` | 0.7 | fracción del ciclo en que empieza el estrangulamiento (visual) |
| `max_lifespan` | 0.0 | h; 0 = sin muerte por vejez |
| `starvation_tolerance` | 4.0 | h con reserva ≈ 0 antes de morir |

**`morphology`** (`Morphology`) — `length_um`, `radius_um`, `length_variation`, `radius_variation`.
Solo se usa para la ventana y para el XML de Unity.

## 7. Curvas de respuesta

Se combinan con `*`, `+`, `-` y `**`. Todo parámetro numérico puede darse también como **nombre de un
parámetro** (un texto), para calibrarlo sin tocar el código.

| Curva | Descripción |
|---|---|
| `Cardinal(var, mín, óptimo, máx)` | Campana asimétrica (CTMI, Rosso 1993). 0 / 1 / 0 en mín / óptimo / máx. Típica para temperatura. Falla al construirla si no es unimodal con esos valores. |
| `CPM(var, mín, óptimo, máx)` | Campana (Rosso 1995), unimodal para cualquier `mín < óptimo < máx`. Típica para pH. |
| `Saturation(var, k, vmax=1, normalized=True)` | Monod `x/(k+x)`. Normalizada vale 1 en el máximo. |
| `Inhibition(var, ki, order=2)` | `1/(1+(x/ki)^orden)`: inhibición por exceso (sustrato, sal…). |
| `Q10(var, q10=2, ref=30)` | Se multiplica por `q10` cada +10 unidades sobre la referencia. |
| `Overload(var, start, end=1, penalty=0.5, vmax=1)` | `1 − penalidad · smoothstep(inicio, fin, x)`: penaliza el exceso. |
| `Gaussian(var, mu, sigma)` | Campana simétrica. |
| `Hill(var, k, n=2)` | Respuesta sigmoidea. |
| `Linear(var, slope, intercept, lo, hi)` | Recta recortada a `[lo, hi]`. |
| `Ref(nombre)` | Valor ya calculado de otra variable, factor o parámetro. |
| `Const(valor)` | Constante. |
| `Func(f)` | Cualquier función propia: `Func(lambda v: v["ph"] * 2)`. |

Ejemplo (crecimiento de *K. xylinus*):
`Cardinal("temperature_c", 12, 31, 40) * CPM("ph_eff", 3.5, 5.5, 8.0) * Saturation("aeration", 0.15)`.

## 8. Estudios: simular, evaluar y optimizar

```python
study = lg.Study(
    organism,
    objective="yield[cellulose]",      # métrica, diccionario ponderado u Objective
    space=["temperature_c", "ph"],     # con qué variables operar (lista o {nombre: (mín, máx)})
    fixed={"glucose_gl": 30},          # variables que se dejan fijas
    sim={"duration_h": 96},            # opciones de SimConfig
    replicas=3,                        # réplicas estocásticas por candidata
    seed=12345,
    workers=1,                         # procesos en paralelo
    direction=None,                    # "max" | "min" (por defecto, el de la métrica)
    constraints=[],                    # [(métrica, operador, valor)]
)
```

- **`space`** admite una lista de nombres (usa los límites del organismo) o un diccionario para
  cambiar los límites. Si se omite, se optimizan todas las variables que no estén en `fixed`.
- Las variables que no están ni en `space` ni en `fixed` se quedan en su valor por defecto.
- `SimConfig`: `duration_h` (96), `dt_h` (0.1), `culture_volume_l` (0.05), `max_agents` (3000),
  `record_every` (10). El volumen solo convierte masas totales en g/L.

### Métodos

| Método | Qué hace |
|---|---|
| `study.simulate(seed=None, observer=None, **condiciones)` | Una simulación → `SimulationResult`. |
| `study.evaluate(replicas=None, **condiciones)` | Varias réplicas + el objetivo → `Candidate`. |
| `study.metrics(nombres, seed=None, **condiciones)` | Valores de varias métricas para unas condiciones. |
| `study.conditions(**override)` | Condiciones por defecto + `fixed` + lo indicado. |
| `study.optimize(...)` | Búsqueda completa (abajo). |
| `Study.from_config(cfg)` | Construye el estudio desde un dict/JSON (devuelve `(estudio, opciones)`). |

### `optimize`

```python
resultado = study.optimize(
    method="evolutionary",   # "evolutionary" | "random" | "grid"
    samples=60,              # candidatas de la exploración (random y evolutionary)
    generations=8,           # generaciones de refinamiento (solo evolutionary)
    population=16,           # hijas por generación
    finalists=3,             # candidatas que pasan a la validación
    grid_levels=3,           # niveles por variable (solo grid)
    sensitivity=True,        # informe de sensibilidad al final
    out="output",            # carpeta de salida (None = no escribe archivos)
    unity_sample=200,        # células fundadoras en el XML
    viz=False,               # True abre la ventana en vivo
    seconds_per_sim=4.0,     # duración en pantalla de cada simulación
    fps=45, fullscreen=False,
)
```

Etapas (todas se imprimen en consola, y salen también en el log de la ventana):

0. **Línea base:** condiciones por defecto, para comparar.
1. **Exploración:** muestreo Latin Hypercube (`evolutionary`), aleatorio (`random`) o malla completa (`grid`).
2. **Refinamiento** (solo `evolutionary`): cada generación muta a las mejores con ruido gaussiano de
   paso decreciente (empieza en 0.15 del rango y se reduce; más rápido si no mejora).
3. **Validación:** las mejores se reevalúan con **semillas nuevas**, para no quedarse con una
   candidata que ganó por suerte. El ganador es el mejor *validado*.
4. **Informe:** parámetros efectivos, métricas de una réplica, avisos (población limitada por el tope
   o nutriente sin agotar) y sensibilidad a cada variable.
5. **Exportación:** CSV, JSON y XML.

Devuelve un `StudyResult`:

| Campo | Contenido |
|---|---|
| `best_conditions` | `Conditions` ganadoras |
| `best_value`, `best_std` | valor y desviación del objetivo en la validación |
| `baseline_value`, `improvement_pct` | línea base y mejora relativa |
| `history`, `validated` | todas las candidatas evaluadas / las validadas |
| `sensitivity` | `{variable: [(valor, objetivo), …]}` |
| `replica_seed` | semilla de la réplica descrita y exportada |
| `simulations`, `elapsed_s`, `out_dir`, `interrupted` | datos de la ejecución |

`resultado.top(n)` devuelve las `n` mejores candidatas. Si cierras la ventana antes de terminar, el
estudio se interrumpe y devuelve lo mejor encontrado hasta ese momento (`interrupted=True`).

## 9. Métricas y objetivos

Una **métrica** es un número sacado de una simulación. Se pide por nombre; algunas llevan argumento
entre corchetes (`"yield[ethanol]"`); sin argumento usan el primer producto (o, en `death_fraction`,
la causa `starvation`).

| Métrica | Unidad | Sentido | Descripción |
|---|---|---|---|
| `yield[p]` | g/L | max | Producto acumulado al final |
| `efficiency[p]` | g/g | max | Producto por nutriente inicial |
| `productivity[p]` | g/L/h | max | Rendimiento dividido entre la duración |
| `specific_production[p]` | mg/(cel·h) | max | Producto por célula y hora viva |
| `peak_population` | cel | max | Máximo de células vivas |
| `final_population` | cel | max | Células vivas al terminar |
| `time_to_peak_h` | h | min | Hora de la población máxima |
| `total_divisions` | | max | Divisiones totales |
| `max_growth_rate` | 1/h | max | Máxima tasa específica de crecimiento (media móvil de 3 puntos) |
| `doubling_time_h` | h | min | ln 2 / tasa máxima (la duración si no crece) |
| `mean_lifespan_h` | h | max | Tiempo medio de vida, desde el último nacimiento/división hasta la muerte |
| `median_lifespan_h` | h | max | Mediana del anterior |
| `max_lifespan_h` | h | max | Máximo observado (incluye a las que siguen vivas) |
| `survival_fraction` | | max | 1 − muertes / (células iniciales + divisiones) |
| `total_deaths` | | min | Muertes totales |
| `extinction_time_h` | h | max | Hora en que muere la última célula (la duración si sobreviven) |
| `death_fraction[causa]` | | min | Fracción de muertes por `starvation`, `age` o `random` |
| `nutrient_consumed_fraction` | | max | Fracción del nutriente inicial consumida |

> **Ojo con el tiempo de vida.** Se mide desde el último nacimiento o división, así que
> `mean_lifespan_h` por sí sola premia condiciones donde las células casi no se dividen. Combínala con
> una restricción (`("final_population", ">=", …)`) o con `survival_fraction`.

### Métricas propias

```python
@lg.metric("viabilidad", unit="%", direction="max")
def viabilidad(result, cond, ctx):
    return 100 * result.final_alive / max(1, result.peak_alive)
```

`result` es el `SimulationResult`, `cond` las `Conditions` y `ctx` tiene `.organism` y `.sim`. Con
`workers > 1`, defínela **a nivel de módulo** (fuera de funciones) para que exista también en los
procesos hijos. Para métricas con argumento, mira `_factory` en `lunagen/metrics.py`.

### Objetivos

```python
lg.Objective("yield")                                         # una métrica
lg.Objective("doubling_time_h", direction="min")              # minimizar
lg.Objective({"yield[cellulose]": 1.0, "survival_fraction": 2.0})   # suma ponderada
lg.Objective("yield", constraints=[("final_population", ">=", 100)])
```

- En una suma ponderada un peso **negativo** penaliza esa métrica.
- Una **restricción** incumplida resta `1000 · (1 + violación relativa)` (el optimizador la evita; no
  se descarta la candidata). Operadores: `>=`, `<=`, `>`, `<`.
- Con restricciones violadas, los valores impresos ya incluyen la penalización.
- Con `Study` puedes pasar directamente un texto, un diccionario o un `Objective`.

## 10. Ventana en vivo

`study.optimize(viz=True)` abre una ventana (requiere `pygame-ce`) y anima **cada simulación** de la
búsqueda en cámara rápida. La simulación avanza al ritmo al que se dibuja.

- **Izquierda:** caja Petri vista desde arriba (cada célula, una cápsula 2D) y, debajo, la telemetría
  en tiempo real: tiempo, vivas, muertas, divisiones, reserva media, producto principal, nutriente
  restante, causas de muerte y tres gráficas (con una línea gris para la mejor simulación hasta ahora).
- **Derecha:** nombre del organismo y progreso global con tiempo estimado, condiciones y parámetros
  efectivos de la simulación en curso, estado del optimizador y log con scroll.

**Qué viene de la simulación y qué no.** Todo es fiel a los datos: quién vive, muere (y de qué) o se
divide; el **tamaño** de la cápsula es su fase del ciclo celular; el **color**, su reserva (rojo =
vacía, cian = llena); la línea de **estrangulamiento** aparece al pasar `constriction_start`; las
**fibras** son el producto principal realmente producido; el **brillo ámbar** del medio es el
nutriente que queda. Lo único decorativo son las posiciones X/Y (el modelo no es espacial): las
células se mueven con una física suave y las hijas nacen pegadas a su madre.

| Tecla | Acción |
|---|---|
| `ESPACIO` | pausa |
| `+` / `-` | velocidad de la animación |
| `S` | saltar la animación de la simulación en curso |
| `F` | animación activada/desactivada (el cálculo sigue a máxima velocidad) |
| `F11` | pantalla completa |
| rueda del ratón, `RePág`, `AvPág`, `Inicio`, `Fin` | desplazar el log |
| `ESC` o cerrar la ventana | salir (el estudio se interrumpe y devuelve lo mejor hasta entonces) |

Si pygame-ce no está instalado o no hay pantalla, el estudio corre igual, solo en consola. Con
`workers > 1`, las réplicas de cada candidata (salvo la animada) se calculan en paralelo mientras se
anima la primera.

## 11. Archivos que se generan

Con `out="output"` (por defecto):

| Archivo | Contenido |
|---|---|
| `evaluations.csv` | cada candidata: etapa, índice, valor de cada variable, media y desviación del objetivo |
| `results.json` | resumen: mejores condiciones, línea base, mejora, límites, fijas, simulación, sensibilidad, semillas |
| `best_unity.xml` | la mejor condición, simulada con la `replica_seed`, lista para Unity |

El XML tiene la raíz `<Simulation>` con: `<Conditions>` (una etiqueta por variable), `<Metrics>`
(rendimiento de cada producto y métricas estándar, con su unidad), `<Parameters>` (los parámetros
efectivos, con un `<product>` por producto) y `<Founders>` (muestra de `unity_sample` células
iniciales con longitud, radio, fase del ciclo, reserva, destino y lo producido por su linaje:
`celluloseMg`, `ethanolMg`…). El esquema es una propuesta y hay que alinearlo con el script que lo lee.

## 12. Configuración con JSON y terminal

Un estudio completo sin escribir código (solo con organismos de `presets`):

```json
{
  "organism": "komagataeibacter_xylinus",
  "calibration": {"base_uptake_rate": 0.04},
  "objective": "yield[cellulose]",
  "direction": "max",
  "constraints": [["final_population", ">=", 100]],
  "space": {"temperature_c": [24, 34], "ph": [4.5, 6.5]},
  "fixed": {"glucose_gl": 30},
  "sim": {"duration_h": 72},
  "replicas": 3,
  "seed": 12345,
  "workers": 1,
  "optimize": {"samples": 20, "generations": 3, "population": 8, "viz": false, "out": "output_config"}
}
```

`space` puede ser una lista de nombres o un diccionario con límites; `objective` un texto o un
diccionario de pesos; `optimize` admite los mismos argumentos que `Study.optimize`.

```python
lg.run("config.json")
```
```bash
lunagen config.json            # equivale a: python -m lunagen config.json
lunagen --metrics              # lista las métricas disponibles
lunagen --version
```

Los organismos propios se describen en Python (contienen funciones); luego se pueden usar con `Study`
como cualquier otro.

## 13. Calibración

Los presets son funciones cuyos argumentos son las perillas de calibración, todos con el valor del
modelo original:

```python
org = lg.presets.komagataeibacter_xylinus(
    base_uptake_rate=0.05,
    growth_ph=(3.5, 5.6, 8.0),                  # (mín, óptimo, máx)
    physiology=lg.Physiology(max_lifespan=48.0),
)
org2 = org.with_params(maintenance_q10=2.2)      # recalibrar parámetros sueltos de una copia
org3 = org.replace(morphology=lg.Morphology(length_um=3.0))
```

Perillas de *K. xylinus*: `base_division_interval_h`, `base_uptake_rate`, `base_maintenance_rate`,
`maintenance_q10`, `base_random_death_rate`, `stress_death_gain`, `agents_per_inoculum_pct`,
`base_production_rate`, `production_variation`, `production_cost_per_unit`,
`production_reserve_threshold`, `growth_temperature`, `production_temperature`, `growth_ph`,
`production_ph`, `oxygen_half_saturation`, `oxygen_overload_start`, `oxygen_overload_penalty`,
`glucose_inhibition`, `gluconic_threshold_gl`, `gluconic_ph_drop_per_gl`, `physiology`, `morphology`.

Los efectos del entorno sobre las tasas (curvas cardinales, saturación de oxígeno, inhibición por
glucosa…) son **supuestos del modelo**: están todos expuestos para calibrarlos con datos reales.
Tras calibrar, conviene mantener una prueba que vuelva a los valores originales (ver §16).

## 14. Paralelismo y reproducibilidad

- **Semillas.** Todo es determinista para una semilla. La búsqueda usa `seed + 1000 + i` y la
  validación `seed + 50000 + i`. Usar las mismas semillas para todas las candidatas hace la
  comparación más justa.
- **`workers`.** Con `workers > 1` se usan procesos (método `spawn`, seguro junto a la ventana). Solo
  viajan datos entre procesos (parámetros y resultados), así que se pueden usar organismos con
  funciones `lambda`. El script debe llevar el resguardo `if __name__ == "__main__":`.
- Las **métricas propias** deben estar definidas a nivel de módulo (ver §9).
- `max_agents` limita el número de células vivas por rendimiento. Si el informe avisa de que la
  población estuvo limitada por el tope, el resultado depende de ese tope: valora subirlo.

## 15. Referencia de la API

```python
import lunagen as lg
```

**Núcleo**

| Nombre | Descripción |
|---|---|
| `lg.Study` | Simular, evaluar y optimizar (§8). |
| `lg.StudyResult`, `lg.Candidate` | Resultados de `optimize` y de una evaluación. |
| `lg.run(config)` | Ejecuta un estudio desde un dict o JSON. |
| `lg.Organism`, `lg.Variable`, `lg.Product`, `lg.Conditions` | Descripción del organismo (§6). `Conditions` es de solo lectura: `c["ph"]`, `c.ph`, `c.replace(ph=6)`, `c.to_dict()`. |
| `lg.SimConfig`, `lg.Physiology`, `lg.Morphology` | Configuración de simulación, fisiología y forma. |
| `lg.simulate(params, sim, seed, morphology, observer)` | Motor de bajo nivel; `params` sale de `Organism.derive(cond, sim)`. |
| `lg.SimulationResult` | Resultado de una simulación (abajo). |
| `lg.presets` | `komagataeibacter_xylinus(...)`, `load(nombre, **calibración)`, `PRESETS`. |

**Métricas y curvas**

| Nombre | Descripción |
|---|---|
| `lg.metric`, `lg.get_metric`, `lg.available_metrics` | Registrar, obtener y listar métricas. |
| `lg.Objective`, `lg.Metric`, `lg.Context`, `lg.report_values` | Objetivos y utilidades de informe. |
| `lg.Cardinal`, `CPM`, `Saturation`, `Inhibition`, `Q10`, `Overload`, `Gaussian`, `Hill`, `Linear`, `Const`, `Ref`, `Func`, `Effect` | Curvas de respuesta (§7). |

**`SimulationResult`**

| Campo | Contenido |
|---|---|
| `times`, `alive`, `dead`, `nutrient_mg`, `mean_reserve` | series temporales (un punto cada `record_every` pasos) |
| `product_series` | `{producto: producido acumulado (mg) en el tiempo}` |
| `product_mg` | `{producto: total producido (mg)}` |
| `nutrient_initial_mg`, `nutrient_final_mg` | nutriente inicial y final (mg) |
| `n_initial`, `duration_h`, `volume_l` | datos de la simulación |
| `peak_alive`, `time_of_peak_h`, `final_alive` | población |
| `total_deaths`, `deaths_by_cause`, `total_divisions`, `capped_steps` | eventos |
| `lifespans`, `survivor_ages`, `death_times` | tiempos de vida (h desde el último nacimiento/división) |
| `founders` | registro de las células iniciales (para Unity) |

**Observador.** `simulate(..., observer=f)` llama a `f(StepInfo)` al final de cada paso con las
células vivas (`uids`, `reserve`, `age_frac`), las muertes y divisiones de ese paso y los totales. El
observador solo **lee**: los resultados son idénticos con o sin él. Así funciona la ventana.

## 16. Pruebas

```bash
python tests/test_regression.py     # la librería == el modelo original, bit a bit
python tests/test_library.py        # métricas, objetivos, validaciones, varios productos, paralelo, exportación
```

Las pruebas vienen en el código fuente del paquete (el `.tar.gz` de PyPI). `test_regression.py` compara contra `tests/legacy_bacillus_model.py` (copia del modelo original):
5 condiciones × 3 semillas, con parámetros, series, fundadoras y totales exactamente iguales. Si
cambias el motor, esta prueba debe seguir pasando.

## 17. Limitaciones y preguntas frecuentes

- **Las posiciones X/Y de la ventana son decorativas.** El modelo no es espacial.
- **Los efectos del entorno son supuestos** (curvas, inhibición, ácido glucónico…). Calíbralos con datos
  reales antes de sacar conclusiones biológicas.
- **El tiempo de vida se mide desde el último nacimiento o división** (ver §9).
- **El esquema del XML** para Unity es una propuesta: alinéalo con tu lector.
- **Rendimiento:** cada simulación tarda decenas o cientos de milisegundos; la animación es lo que
  consume tiempo (`seconds_per_sim`, o `F` para desactivarla).
- **¿Puedo usar un organismo propio con `lunagen config.json`?** No: contienen funciones. Descríbelo en
  Python y úsalo con `Study`.
- **¿Por qué `if __name__ == "__main__":`?** Con varios procesos, cada proceso hijo vuelve a importar
  el script; sin ese resguardo se relanzaría el estudio.
- **La ventana no abre.** Instala `pygame-ce` (`pip install "lunagen[viz]"`); si no hay pantalla, el estudio
  corre solo en consola.
