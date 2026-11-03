## 1. What is lunagen

`lunagen` simulates a culture cell by cell (one *agent* per cell, vectorized with NumPy) and lets you
**search for the conditions that maximize or minimize whatever you choose**. Every cell has an energy
reserve and its own division cycle, it can die (from starvation, old age or chance) and it can produce
one or several compounds.

It was born from a bacterial cellulose project (*Komagataeibacter xylinus*) and generalized so that the
engine **does not depend on any particular organism**: everything specific is declared. With that you can:

- optimize the production of cellulose, ethanol, protein or any other biomass;
- measure only **lifespan**, only **reproduction**, or any other metric;
- choose **which variables** to work with and which to keep fixed;
- animate every simulation in a sci-fi style live window;
- export the best results to CSV, JSON and XML (for Unity).

One important design principle: culture conditions **do not act while the simulation runs**. They are
translated **once** into *effective parameters*; with those held constant, the engine always applies the
same equations.

## 2. Installation

Requirements: Python 3.9 or later (tested on 3.12) and NumPy.

```bash
pip install lunagen                  # core
pip install "lunagen[viz]"           # + pygame-ce and scipy for the live window
pip install lunagen-0.1.1-py3-none-any.whl     # from the .whl file
```

- **pygame-ce** opens the window (`viz=True`). It also works with classic `pygame`, but do not install
  both at once: they are both imported as `pygame` and get in each other's way. `pygame-ce` usually
  publishes prebuilt packages for new Python versions before `pygame` does. Without either one, or without
  a display, `optimize` still works and just prints to the console.
- **scipy** is optional: it adds collisions between the capsules in the window. Without it the cells can
  overlap, but everything else is identical.

Check the installation:

```bash
python -c "import lunagen; print(lunagen.__version__)"
lunagen --metrics
```

## 3. Quick start

```python
import lunagen as lg

if __name__ == "__main__":
    organism = lg.presets.komagataeibacter_xylinus()
    study = lg.Study(organism, objective="yield[cellulose]", workers=4)
    result = study.optimize(samples=60, generations=8, population=16, viz=True)
    print(result.best_conditions)       # the best conditions
    print(result.best_value)            # g/L of cellulose (validated with fresh seeds)
```

A single simulation, without optimizing:

```python
res = study.simulate(temperature_c=29, ph=5.3)
print(res.product_mg["cellulose"], res.peak_alive, res.deaths_by_cause)
```

## 4. How it works

```
 Conditions ──► Organism.derive ──► Effective parameters ──► Engine (simulate) ──► SimulationResult
 (temperature,       (laws and             (constants)             (agents)               │
  pH, glucose…)       factors)                                                             ▼
                                                                      Metrics ──► Objective ──► value
                                                                                                  ▲
                                                     Study.optimize: baseline → exploration → refinement → validation
```

| Piece | Module | What it does |
|---|---|---|
| `Organism` | `organism` | Describes the organism: variables, factors, laws, products. |
| `simulate` engine | `engine` | Simulates one culture. Deterministic for a given seed. |
| metrics / `Objective` | `metrics` | What is measured and what is optimized. |
| `Study` | `study` | Ties it all together: simulates, evaluates and optimizes, with reports and export. |
| window | `viz` | Animates every simulation (enabled with `viz=True`). |
| `presets` | `presets` | Ready-made organisms (*Komagataeibacter xylinus*). |
| responses | `responses` | Composable curves: `Cardinal`, `CPM`, `Saturation`… |

## 5. The simulation model

Units: time in **hours**, mass in **milligrams** (per cell), lengths in **µm**.
At every time step `dt`, and for every cell, in this order:

1. **Metabolism.** With `c = remaining_nutrient / initial_nutrient`:
   `uptake = uptake_rate · c/(Ks + c) · (1 − reserve/capacity) · dt`;
   `reserve += uptake · yield`; `reserve −= maintenance · dt`.
   If together the cells ask for more nutrient than is left, it is shared out proportionally.
2. **Death** (priority: starvation, old age, chance).
   *Starvation:* reserve ≈ 0 for `starvation_tolerance` hours.
   *Old age:* age ≥ `max_lifespan` (only if `max_lifespan > 0`).
   *Chance:* probability `1 − exp(−random_death_rate · dt)`.
3. **Growth.** `scale = clip(reserve / (threshold · capacity), 0, 1)`; the cycle clock advances
   `dt · scale` (slower with a low reserve) and costs `growth_cost · dt · scale`. With a full population
   (`max_agents`), cells that have not yet started constriction do not start growing.
4. **Products.** For each product: `mass = rate · individual_factor · product_scale · dt`, and
   `mass · cost` of reserve is spent (never more reserve than is available).
5. **Division.** When the cycle is complete, the cell divides into two daughters that share the reserve
   equally; the daughter inherits the individual production factor. If there is no room, only some divide,
   chosen at random.

All randomness comes from a seed, so **the same seed gives exactly the same result**. Every initial cell
starts in a different phase of its cycle and has individual variation in cycle and production
(`variation`), which is inherited.

## 6. Describing an organism

An `Organism` is a **declarative** description. See `lunagen/presets.py` (xylinus) and
`examples/03_new_organism.py` (yeast) as models (both ship in the package's source distribution, the
`.tar.gz` on PyPI).

```python
import lunagen as lg
from lunagen import Cardinal, CPM, Inhibition, Ref, Saturation

org = lg.Organism(
    name="My organism",
    nutrient_label="Sugar",                      # nutrient name (display only)
    variables=[                                  # what can be controlled
        lg.Variable("temperature_c", 30.0, (20, 40), "°C", "Temperature", "{:.1f}"),
        lg.Variable("ph", 5.5, (4, 7), "", "pH", "{:.2f}"),
        lg.Variable("sugar_gl", 40.0, (10, 100), "g/L", "Sugar", "{:.0f}"),
        lg.Variable("inoculum_pct", 5.0, (1, 15), "%", "Inoculum", "{:.1f}"),
    ],
    params=dict(base_cycle_h=2.0, base_uptake=0.04),          # loose, tunable numbers
    factors={                                                  # responses between 0 and 1
        "g_temp": Cardinal("temperature_c", 10, 31, 42),
        "g_ph": CPM("ph", 3.5, 5.5, 8.0),
        "growth": Ref("g_temp") * Ref("g_ph"),
        "osmotic": Inhibition("sugar_gl", 80.0, 2),
    },
    laws={                                                     # conditions -> parameters
        "n_initial": lambda v: round(v["inoculum_pct"] * 40),
        "nutrient_mg": lambda v: v["sugar_gl"] * v["volume_l"] * 1000.0,
        "division_interval": lambda v: v["base_cycle_h"] / max(v["growth"], 1e-3),
        "uptake_rate": lambda v: v["base_uptake"] * v["osmotic"],
        "maintenance_rate": lambda v: 0.002,
        "random_death_rate": lambda v: 0.001 + 0.01 * (1 - v["g_temp"]) ** 2,
    },
    products=[lg.Product("biomass_x", rate=0.004, law=Ref("growth"), cost=2.0, label="Biomass X")],
)
```

### The parts

**`variables`** — a list of `Variable(name, default, bounds, unit, label, fmt)`. These are the conditions
that can be fixed or optimized. `bounds` are the default search limits.

**`params`** — a dictionary of loose numbers that the laws can read (`v["base_cycle_h"]`). They let you
calibrate without touching the formulas (`org.with_params(base_uptake=0.05)`).

**`derived`** (optional) — variables computed from other ones, for example an effective pH:
`derived={"ph_eff": lambda v: v["ph"] - 0.03 * max(0, v["glucose_gl"] - 10)}`.

**`factors`** — intermediate responses (normally between 0 and 1), defined with the
[response curves](#7-response-curves). They are evaluated in order, so a factor can use the previous ones
with `Ref("name")`.

**`laws`** — translate the environment into simulation parameters. Each law receives a dictionary `v`
and returns a number. These six are **required**:

| Law | Meaning | Unit |
|---|---|---|
| `n_initial` | initial cells (limited to `[1, max_agents]`) | cells |
| `nutrient_mg` | total initial nutrient of the culture | mg |
| `division_interval` | length of the cell cycle (capped at 10 000 h) | h |
| `uptake_rate` | maximum nutrient uptake per cell | mg/h |
| `maintenance_rate` | reserve spent on maintenance | reserve/h |
| `random_death_rate` | death by chance | 1/h |

In addition, **any `Physiology` field** can be a law (e.g. `max_lifespan` tied to pH).
What a law sees in `v`: the `params`, the variables, the derived values, the factors and three simulation
constants: `volume_l`, `duration_h`, `max_agents`.

**`products`** — one or several `Product(name, rate, law, cost, variation, reserve_threshold, label, unit, color)`:

| Field | Meaning |
|---|---|
| `rate` | mg / h / cell in ideal conditions |
| `law` | environmental effect that multiplies `rate` (a curve; `None` = constant) |
| `cost` | reserve consumed per mg produced |
| `variation` | individual variation (±), inherited by the daughters |
| `reserve_threshold` | fraction of the capacity below which it produces less |
| `label`, `unit`, `color` | display only (window and reports) |

The first product is the **main** one: it is the one the window draws as fibers and the one used by default
by metrics without an argument (`"yield"` = `"yield[<first product>]"`).

**`physiology`** (`Physiology`) — constants of metabolism and the cycle:

| Field | Default | Meaning |
|---|---|---|
| `half_saturation` | 0.1 | nutrient saturation constant (fraction of the initial amount) |
| `yield_coefficient` | 0.5 | reserve gained per mg of nutrient |
| `reserve_capacity` | 0.05 | maximum reserve capacity |
| `initial_reserve` | 0.6 | initial reserve (fraction of capacity) |
| `growth_cost` | 0.004 | reserve/h at full growth speed |
| `growth_reserve_threshold` | 0.3 | reserve threshold for growing at full pace |
| `division_variation` | 0.2 | individual variation of the cycle length (±) |
| `constriction_start` | 0.7 | fraction of the cycle at which constriction starts (visual) |
| `max_lifespan` | 0.0 | h; 0 = no death by old age |
| `starvation_tolerance` | 4.0 | h with reserve ≈ 0 before dying |

**`morphology`** (`Morphology`) — `length_um`, `radius_um`, `length_variation`, `radius_variation`.
Used only for the window and the Unity XML.

## 7. Response curves

They combine with `*`, `+`, `-` and `**`. Any numeric parameter can also be given as the **name of a
parameter** (a string), so you can calibrate without touching the code.

| Curve | Description |
|---|---|
| `Cardinal(var, min, optimum, max)` | Asymmetric bell (CTMI, Rosso 1993). 0 / 1 / 0 at min / optimum / max. Typical for temperature. Fails when built if it is not unimodal with those values. |
| `CPM(var, min, optimum, max)` | Bell (Rosso 1995), unimodal for any `min < optimum < max`. Typical for pH. |
| `Saturation(var, k, vmax=1, normalized=True)` | Monod `x/(k+x)`. Normalized, it equals 1 at the maximum. |
| `Inhibition(var, ki, order=2)` | `1/(1+(x/ki)^order)`: inhibition by excess (substrate, salt…). |
| `Q10(var, q10=2, ref=30)` | Multiplied by `q10` for every +10 units above the reference. |
| `Overload(var, start, end=1, penalty=0.5, vmax=1)` | `1 − penalty · smoothstep(start, end, x)`: penalizes excess. |
| `Gaussian(var, mu, sigma)` | Symmetric bell. |
| `Hill(var, k, n=2)` | Sigmoid response. |
| `Linear(var, slope, intercept, lo, hi)` | Line clipped to `[lo, hi]`. |
| `Ref(name)` | Already-computed value of another variable, factor or parameter. |
| `Const(value)` | Constant. |
| `Func(f)` | Any function of your own: `Func(lambda v: v["ph"] * 2)`. |

Example (growth of *K. xylinus*):
`Cardinal("temperature_c", 12, 31, 40) * CPM("ph_eff", 3.5, 5.5, 8.0) * Saturation("aeration", 0.15)`.

## 8. Studies: simulate, evaluate and optimize

```python
study = lg.Study(
    organism,
    objective="yield[cellulose]",      # metric, weighted dictionary or an Objective
    space=["temperature_c", "ph"],     # which variables to work with (list or {name: (min, max)})
    fixed={"glucose_gl": 30},          # variables that stay fixed
    sim={"duration_h": 96},            # SimConfig options
    replicas=3,                        # stochastic replicas per candidate
    seed=12345,
    workers=1,                         # parallel processes
    direction=None,                    # "max" | "min" (by default, the metric's own)
    constraints=[],                    # [(metric, operator, value)]
)
```

- **`space`** accepts a list of names (using the organism's limits) or a dictionary to change the limits.
  If omitted, every variable not in `fixed` is optimized.
- Variables that are in neither `space` nor `fixed` stay at their default value.
- `SimConfig`: `duration_h` (96), `dt_h` (0.1), `culture_volume_l` (0.05), `max_agents` (3000),
  `record_every` (10). The volume only converts total masses into g/L.

### Methods

| Method | What it does |
|---|---|
| `study.simulate(seed=None, observer=None, **conditions)` | A single simulation → `SimulationResult`. |
| `study.evaluate(replicas=None, **conditions)` | Several replicas + the objective → `Candidate`. |
| `study.metrics(names, seed=None, **conditions)` | Values of several metrics for some conditions. |
| `study.conditions(**override)` | Default conditions + `fixed` + whatever you indicate. |
| `study.optimize(...)` | Full search (below). |
| `Study.from_config(cfg)` | Builds the study from a dict/JSON (returns `(study, options)`). |

### `optimize`

```python
result = study.optimize(
    method="evolutionary",   # "evolutionary" | "random" | "grid"
    samples=60,              # exploration candidates (random and evolutionary)
    generations=8,           # refinement generations (evolutionary only)
    population=16,           # daughters per generation
    finalists=3,             # candidates that go on to validation
    grid_levels=3,           # levels per variable (grid only)
    sensitivity=True,        # sensitivity report at the end
    out="output",            # output folder (None = write no files)
    unity_sample=200,        # founder cells in the XML
    viz=False,               # True opens the live window
    seconds_per_sim=4.0,     # on-screen duration of each simulation
    fps=45, fullscreen=False,
)
```

Stages (all printed to the console, and also shown in the window's log):

0. **Baseline:** default conditions, for comparison.
1. **Exploration:** Latin Hypercube sampling (`evolutionary`), random (`random`) or a full grid (`grid`).
2. **Refinement** (`evolutionary` only): each generation mutates the best candidates with Gaussian noise
   of decreasing step (starting at 0.15 of the range and shrinking; faster if there is no improvement).
3. **Validation:** the best ones are re-evaluated with **fresh seeds**, so you do not keep a candidate
   that won by luck. The winner is the best *validated* one.
4. **Report:** effective parameters, single-replica metrics, warnings (population limited by the cap or
   nutrient left over) and sensitivity to each variable.
5. **Export:** CSV, JSON and XML.

It returns a `StudyResult`:

| Field | Content |
|---|---|
| `best_conditions` | winning `Conditions` |
| `best_value`, `best_std` | value and deviation of the objective in validation |
| `baseline_value`, `improvement_pct` | baseline and relative improvement |
| `history`, `validated` | every candidate evaluated / the validated ones |
| `sensitivity` | `{variable: [(value, objective), …]}` |
| `replica_seed` | seed of the replica that is described and exported |
| `simulations`, `elapsed_s`, `out_dir`, `interrupted` | run data |

`result.top(n)` returns the `n` best candidates. If you close the window before it finishes, the study is
interrupted and returns the best found so far (`interrupted=True`).

## 9. Metrics and objectives

A **metric** is a number extracted from a simulation. You ask for it by name; some take an argument in
square brackets (`"yield[ethanol]"`); without an argument they use the first product (or, in
`death_fraction`, the cause `starvation`).

| Metric | Unit | Direction | Description |
|---|---|---|---|
| `yield[p]` | g/L | max | Product accumulated at the end |
| `efficiency[p]` | g/g | max | Product per initial nutrient |
| `productivity[p]` | g/L/h | max | Yield divided by the duration |
| `specific_production[p]` | mg/(cell·h) | max | Product per cell per living hour |
| `peak_population` | cells | max | Maximum number of living cells |
| `final_population` | cells | max | Living cells at the end |
| `time_to_peak_h` | h | min | Hour of the maximum population |
| `total_divisions` | | max | Total cell divisions |
| `max_growth_rate` | 1/h | max | Maximum specific growth rate (3-point moving average) |
| `doubling_time_h` | h | min | ln 2 / maximum rate (the duration if it does not grow) |
| `mean_lifespan_h` | h | max | Mean lifespan, from the last birth/division to death |
| `median_lifespan_h` | h | max | Median of the above |
| `max_lifespan_h` | h | max | Maximum observed (includes cells still alive) |
| `survival_fraction` | | max | 1 − deaths / (initial cells + divisions) |
| `total_deaths` | | min | Total deaths |
| `extinction_time_h` | h | max | Hour the last cell dies (the duration if some survive) |
| `death_fraction[cause]` | | min | Fraction of deaths from `starvation`, `age` or `random` |
| `nutrient_consumed_fraction` | | max | Fraction of the initial nutrient consumed |

> **Careful with lifespan.** It is measured from the last birth or division, so `mean_lifespan_h` on its
> own rewards conditions where cells barely divide. Combine it with a constraint
> (`("final_population", ">=", …)`) or with `survival_fraction`.

### Custom metrics

```python
@lg.metric("viability", unit="%", direction="max")
def viability(result, cond, ctx):
    return 100 * result.final_alive / max(1, result.peak_alive)
```

`result` is the `SimulationResult`, `cond` the `Conditions`, and `ctx` has `.organism` and `.sim`. With
`workers > 1`, define it **at module level** (outside functions) so it also exists in the child processes.
For metrics with an argument, see `_factory` in `lunagen/metrics.py`.

### Objectives

```python
lg.Objective("yield")                                         # one metric
lg.Objective("doubling_time_h", direction="min")              # minimize
lg.Objective({"yield[cellulose]": 1.0, "survival_fraction": 2.0})   # weighted sum
lg.Objective("yield", constraints=[("final_population", ">=", 100)])
```

- In a weighted sum, a **negative** weight penalizes that metric.
- A violated **constraint** subtracts `1000 · (1 + relative violation)` (the optimizer avoids it; the
  candidate is not discarded). Operators: `>=`, `<=`, `>`, `<`.
- With violated constraints, the printed values already include the penalty.
- With `Study` you can pass a string, a dictionary or an `Objective` directly.

## 10. Live window

`study.optimize(viz=True)` opens a window (requires `pygame-ce`) and animates **every simulation** of the
search in fast motion. The simulation advances at the pace at which it is drawn.

- **Left:** a Petri dish seen from above (every cell, a 2D capsule) and, below it, the real-time telemetry:
  time, living, dead, divisions, mean reserve, main product, remaining nutrient, causes of death and three
  charts (with a gray line for the best simulation so far).
- **Right:** organism name and overall progress with estimated time, conditions and effective parameters of
  the simulation in progress, optimizer status and a scrollable log.

**What comes from the simulation and what does not.** Everything is faithful to the data: who lives, dies
(and from what) or divides; the **size** of the capsule is its phase of the cell cycle; the **color**, its
reserve (red = empty, cyan = full); the **constriction** line appears past `constriction_start`; the
**fibers** are the main product actually produced; the **amber glow** of the medium is the nutrient left.
The only decorative thing is the X/Y positions (the model is not spatial): cells move with soft physics
and daughters are born next to their mother.

| Key | Action |
|---|---|
| `SPACE` | pause |
| `+` / `-` | animation speed |
| `S` | skip the animation of the current simulation |
| `F` | animation on/off (the computation keeps going at full speed) |
| `F11` | fullscreen |
| mouse wheel, `PgUp`, `PgDn`, `Home`, `End` | scroll the log |
| `ESC` or closing the window | quit (the study is interrupted and returns the best found so far) |

If pygame-ce is not installed or there is no display, the study runs anyway, console only. With
`workers > 1`, the replicas of every candidate (except the animated one) are computed in parallel while the
first one is animated.

## 11. Files that are generated

With `out="output"` (the default):

| File | Content |
|---|---|
| `evaluations.csv` | every candidate: stage, index, value of each variable, mean and deviation of the objective |
| `results.json` | summary: best conditions, baseline, improvement, limits, fixed values, simulation, sensitivity, seeds |
| `best_unity.xml` | the best condition, simulated with `replica_seed`, ready for Unity |

The XML has the root `<Simulation>` with: `<Conditions>` (one tag per variable), `<Metrics>` (yield of each
product and standard metrics, with their unit), `<Parameters>` (the effective parameters, with one
`<product>` per product) and `<Founders>` (a sample of `unity_sample` initial cells with length, radius,
cycle phase, reserve, fate and what their lineage produced: `celluloseMg`, `ethanolMg`…). The schema is a
proposal and has to be aligned with the script that reads it.

## 12. Configuration with JSON and the terminal

A complete study without writing code (only with organisms from `presets`):

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

`space` can be a list of names or a dictionary with limits; `objective` a string or a dictionary of
weights; `optimize` accepts the same arguments as `Study.optimize`.

```python
lg.run("config.json")
```
```bash
lunagen config.json            # equivalent to: python -m lunagen config.json
lunagen --metrics              # list the available metrics
lunagen --version
```

Your own organisms are described in Python (they contain functions); after that you can use them with
`Study` like any other.

## 13. Calibration

Presets are functions whose arguments are the calibration knobs, all set to the original model's values:

```python
org = lg.presets.komagataeibacter_xylinus(
    base_uptake_rate=0.05,
    growth_ph=(3.5, 5.6, 8.0),                  # (min, optimum, max)
    physiology=lg.Physiology(max_lifespan=48.0),
)
org2 = org.with_params(maintenance_q10=2.2)      # recalibrate loose parameters of a copy
org3 = org.replace(morphology=lg.Morphology(length_um=3.0))
```

*K. xylinus* knobs: `base_division_interval_h`, `base_uptake_rate`, `base_maintenance_rate`,
`maintenance_q10`, `base_random_death_rate`, `stress_death_gain`, `agents_per_inoculum_pct`,
`base_production_rate`, `production_variation`, `production_cost_per_unit`,
`production_reserve_threshold`, `growth_temperature`, `production_temperature`, `growth_ph`,
`production_ph`, `oxygen_half_saturation`, `oxygen_overload_start`, `oxygen_overload_penalty`,
`glucose_inhibition`, `gluconic_threshold_gl`, `gluconic_ph_drop_per_gl`, `physiology`, `morphology`.

The effects of the environment on the rates (cardinal curves, oxygen saturation, glucose inhibition…) are
**model assumptions**: all of them are exposed so you can calibrate them with real data. After calibrating,
it is wise to keep a test that returns to the original values (see §16).

## 14. Parallelism and reproducibility

- **Seeds.** Everything is deterministic for a given seed. The search uses `seed + 1000 + i` and the
  validation `seed + 50000 + i`. Using the same seeds for every candidate makes the comparison fairer.
- **`workers`.** With `workers > 1`, processes are used (the `spawn` method, safe alongside the window).
  Only data travels between processes (parameters and results), so organisms with `lambda` functions can
  be used. The script must have the `if __name__ == "__main__":` guard.
- **Custom metrics** must be defined at module level (see §9).
- `max_agents` limits the number of living cells for performance. If the report warns that the population
  was limited by the cap, the result depends on that cap: consider raising it.

## 15. API reference

```python
import lunagen as lg
```

**Core**

| Name | Description |
|---|---|
| `lg.Study` | Simulate, evaluate and optimize (§8). |
| `lg.StudyResult`, `lg.Candidate` | Results of `optimize` and of an evaluation. |
| `lg.run(config)` | Runs a study from a dict or JSON. |
| `lg.Organism`, `lg.Variable`, `lg.Product`, `lg.Conditions` | Organism description (§6). `Conditions` is read-only: `c["ph"]`, `c.ph`, `c.replace(ph=6)`, `c.to_dict()`. |
| `lg.SimConfig`, `lg.Physiology`, `lg.Morphology` | Simulation, physiology and shape settings. |
| `lg.simulate(params, sim, seed, morphology, observer)` | Low-level engine; `params` comes from `Organism.derive(cond, sim)`. |
| `lg.SimulationResult` | Result of a simulation (below). |
| `lg.presets` | `komagataeibacter_xylinus(...)`, `load(name, **calibration)`, `PRESETS`. |

**Metrics and curves**

| Name | Description |
|---|---|
| `lg.metric`, `lg.get_metric`, `lg.available_metrics` | Register, get and list metrics. |
| `lg.Objective`, `lg.Metric`, `lg.Context`, `lg.report_values` | Objectives and report utilities. |
| `lg.Cardinal`, `CPM`, `Saturation`, `Inhibition`, `Q10`, `Overload`, `Gaussian`, `Hill`, `Linear`, `Const`, `Ref`, `Func`, `Effect` | Response curves (§7). |

**`SimulationResult`**

| Field | Content |
|---|---|
| `times`, `alive`, `dead`, `nutrient_mg`, `mean_reserve` | time series (one point every `record_every` steps) |
| `product_series` | `{product: accumulated production (mg) over time}` |
| `product_mg` | `{product: total produced (mg)}` |
| `nutrient_initial_mg`, `nutrient_final_mg` | initial and final nutrient (mg) |
| `n_initial`, `duration_h`, `volume_l` | simulation data |
| `peak_alive`, `time_of_peak_h`, `final_alive` | population |
| `total_deaths`, `deaths_by_cause`, `total_divisions`, `capped_steps` | events |
| `lifespans`, `survivor_ages`, `death_times` | lifespans (h since the last birth/division) |
| `founders` | record of the initial cells (for Unity) |

**Observer.** `simulate(..., observer=f)` calls `f(StepInfo)` at the end of every step with the living
cells (`uids`, `reserve`, `age_frac`), that step's deaths and divisions, and the totals. The observer only
**reads**: results are identical with or without it. This is how the window works.

## 16. Tests

```bash
python tests/test_regression.py     # the library == the original model, bit by bit
python tests/test_library.py        # metrics, objectives, validations, several products, parallel, export
```

The tests ship in the package's source distribution (the `.tar.gz` on PyPI). `test_regression.py`
compares against `tests/legacy_bacillus_model.py` (a copy of the original model): 5 conditions × 3 seeds,
with parameters, series, founders and totals exactly equal. If you change the engine, this test must keep
passing.

## 17. Limitations and frequently asked questions

- **The X/Y positions in the window are decorative.** The model is not spatial.
- **The effects of the environment are assumptions** (curves, inhibition, gluconic acid…). Calibrate them
  with real data before drawing biological conclusions.
- **Lifespan is measured from the last birth or division** (see §9).
- **The Unity XML schema** is a proposal: align it with your reader.
- **Performance:** every simulation takes tens to hundreds of milliseconds; the animation is what takes
  time (`seconds_per_sim`, or `F` to turn it off).
- **Can I use my own organism with `lunagen config.json`?** No: they contain functions. Describe it in
  Python and use it with `Study`.
- **Why `if __name__ == "__main__":`?** With several processes, every child process imports the script
  again; without that guard the study would be launched again.
- **The window does not open.** Install `pygame-ce` (`pip install "lunagen[viz]"`); if there is no display,
  the study runs console-only.
