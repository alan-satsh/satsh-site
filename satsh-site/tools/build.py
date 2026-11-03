"""
Genera el sitio estático (HTML listo para GitHub Pages).

    pip install markdown
    python tools/build.py

Qué hace
  - index.html                  satsh.org            (portada de satsh)
  - lunagen/index.html          satsh.org/lunagen/   (principal de Lunagen)
  - lunagen/docs/index.html     satsh.org/lunagen/docs/  (documentación, a partir de tools/docs/*.md)
  - 404.html, robots.txt, sitemap.xml, CNAME, .nojekyll

Cada texto se escribe en español e inglés. El idioma se elige solo (idioma del navegador) y se puede cambiar
con el selector ES / EN; la elección se recuerda. Para editar un texto, cámbialo aquí o en los .md y vuelve
a ejecutar el script. Los HTML generados YA están en el repositorio: no necesitas ejecutarlo para publicar.
"""
from __future__ import annotations

import datetime
import html
import os
import re
import unicodedata

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = "satsh.org"
SITE = f"https://{DOMAIN}"
PYPI = "https://pypi.org/project/lunagen/"
IMPARA = "https://impara.org"
VERSION = "0.1.1"
YEAR = datetime.date.today().year


# ============================================================
# utilidades de plantilla
# ============================================================
def L(es: str, en: str, tag: str = "span") -> str:
    """Un texto en los dos idiomas; el CSS muestra solo el del idioma activo."""
    return f'<{tag} data-lang="es">{es}</{tag}><{tag} data-lang="en">{en}</{tag}>'


def write(path: str, content: str) -> None:
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("  +", path)


LANG_SCRIPT = (
    "(function(){var r=document.documentElement;r.className=r.className.replace('no-js','js');var l=null;"
    "try{l=localStorage.getItem('satsh-lang')}catch(e){}"
    "if(l!=='es'&&l!=='en'){l=null;var a=navigator.languages&&navigator.languages.length?navigator.languages:"
    "[navigator.language||navigator.userLanguage||'en'];"
    "for(var i=0;i<a.length;i++){var c=String(a[i]).toLowerCase();if(c.indexOf('es')===0){l='es';break}"
    "if(c.indexOf('en')===0){l='en';break}}}r.lang=l||'en';})();"
)


def head(root: str, path: str, title: tuple, desc: tuple, og_image: str) -> str:
    url = f"{SITE}/{path}"
    e = html.escape
    return f"""<!doctype html>
<html lang="en" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title data-es="{e(title[0])}" data-en="{e(title[1])}">{e(title[1])}</title>
<meta name="description" content="{e(desc[1])}" data-es="{e(desc[0])}" data-en="{e(desc[1])}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#000000">
<meta property="og:type" content="website">
<meta property="og:site_name" content="satsh">
<meta property="og:title" content="{e(title[1])}">
<meta property="og:description" content="{e(desc[1])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/assets/img/{og_image}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{root}assets/css/site.css">
<script>{LANG_SCRIPT}</script>
</head>
"""


def header(root: str, kind: str) -> str:
    """kind: home | lunagen | docs"""
    brand_extra = {"home": "", "lunagen": "<small>/ Lunagen</small>", "docs": "<small>/ Lunagen / Docs</small>"}[kind]
    if kind == "home":
        links = (f'<a href="#projects">{L("Proyectos", "Projects")}</a>'
                 f'<a href="{root}lunagen/">Lunagen</a>'
                 f'<a href="{IMPARA}" target="_blank" rel="noopener">Impara&nbsp;↗</a>')
    elif kind == "lunagen":
        links = (f'<a href="#overview">{L("Resumen", "Overview")}</a>'
                 f'<a href="#how">{L("Cómo funciona", "How it works")}</a>'
                 f'<a href="#window">{L("Ventana en vivo", "Live window")}</a>'
                 f'<a href="{root}lunagen/docs/">{L("Documentación", "Documentation")}</a>'
                 f'<a href="{PYPI}" target="_blank" rel="noopener">PyPI&nbsp;↗</a>')
    else:
        links = (f'<a href="{root}lunagen/">Lunagen</a>'
                 f'<a href="{root}lunagen/docs/" aria-current="page">{L("Documentación", "Documentation")}</a>'
                 f'<a href="{PYPI}" target="_blank" rel="noopener">PyPI&nbsp;↗</a>')
    return f"""<a class="skip" href="#main">{L("Saltar al contenido", "Skip to content")}</a>
<header class="site-header">
  <a class="brand" href="{root or './'}" aria-label="satsh">SATSH {brand_extra}</a>
  <button class="nav-toggle" aria-expanded="false" aria-controls="nav" data-aria-es="Menú" data-aria-en="Menu" aria-label="Menu"><span></span></button>
  <nav class="nav" id="nav">
    {links}
    <div class="lang" role="group" aria-label="Idioma / Language"><button data-set="es" type="button">ES</button><button data-set="en" type="button">EN</button></div>
  </nav>
</header>
"""


def footer(root: str) -> str:
    return f"""<footer class="site-footer">
  <a class="brand" href="{root or './'}">SATSH</a>
  <div class="links">
    <a href="{root}lunagen/">Lunagen</a>
    <a href="{root}lunagen/docs/">{L("Documentación", "Documentation")}</a>
    <a href="{IMPARA}" target="_blank" rel="noopener">Impara&nbsp;↗</a>
    <a href="{PYPI}" target="_blank" rel="noopener">PyPI&nbsp;↗</a>
  </div>
  <span>© <span data-year>{YEAR}</span> satsh</span>
</footer>
"""


def page(root, path, title, desc, og, kind, body, extra_class="") -> str:
    return (head(root, path, title, desc, og)
            + f'<body class="{extra_class}">\n<canvas id="stars" aria-hidden="true"></canvas>\n'
            + header(root, kind) + body + footer(root)
            + f'<script src="{root}assets/js/site.js" defer></script>\n</body>\n</html>\n')


# ============================================================
# resaltado mínimo de Python para los ejemplos de la portada de Lunagen
# ============================================================
_PY = re.compile(r"(#[^\n]*)|(\"\"\".*?\"\"\"|'[^'\n]*'|\"[^\"\n]*\")|\b(import|from|as|def|return|if|for|in|lambda|with|True|False|None)\b|\b([A-Za-z_]\w*)(?=\()", re.S)


def hl(code: str) -> str:
    out, pos = [], 0
    for m in _PY.finditer(code):
        out.append(html.escape(code[pos:m.start()]))
        t = html.escape(m.group(0))
        cls = "c" if m.group(1) else "s" if m.group(2) else "k" if m.group(3) else "f"
        out.append(f'<span class="{cls}">{t}</span>')
        pos = m.end()
    out.append(html.escape(code[pos:]))
    return "".join(out)


def code_block(code: str) -> str:
    return (f'<div class="code reveal"><pre><code>{hl(code.strip(chr(10)))}</code></pre>'
            f'<button class="copy" type="button">{L("Copiar", "Copy")}</button></div>')


MOON_SVG = """<svg viewBox="0 0 600 600" aria-hidden="true" focusable="false">
  <defs>
    <radialGradient id="mshade" cx="36%" cy="32%" r="78%">
      <stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset=".5" stop-color="#000" stop-opacity=".22"/>
      <stop offset="1" stop-color="#000" stop-opacity=".97"/>
    </radialGradient>
    <filter id="mtex" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.019 0.022" numOctaves="6" seed="9" result="n"/>
      <feDiffuseLighting in="n" lighting-color="#ffffff" surfaceScale="5.2" diffuseConstant="1.25" result="lit">
        <feDistantLight azimuth="220" elevation="42"/>
      </feDiffuseLighting>
      <feComponentTransfer in="lit" result="lit2"><feFuncR type="gamma" amplitude="1.15" exponent="1.35" offset="0"/><feFuncG type="gamma" amplitude="1.15" exponent="1.35" offset="0"/><feFuncB type="gamma" amplitude="1.17" exponent="1.35" offset="0"/></feComponentTransfer>
      <feComposite in="lit2" in2="SourceGraphic" operator="in"/>
    </filter>
    <filter id="mblur"><feGaussianBlur stdDeviation="14"/></filter>
    <clipPath id="mclip"><circle cx="300" cy="300" r="290"/></clipPath>
  </defs>
  <g clip-path="url(#mclip)">
    <circle cx="300" cy="300" r="290" fill="#cdd1d7" filter="url(#mtex)"/>
    <g filter="url(#mblur)" opacity=".5" fill="#05070b">
      <ellipse cx="215" cy="215" rx="96" ry="70"/><ellipse cx="350" cy="170" rx="56" ry="44"/>
      <ellipse cx="330" cy="355" rx="74" ry="56"/><ellipse cx="190" cy="380" rx="40" ry="32"/>
    </g>
    <circle cx="300" cy="300" r="290" fill="url(#mshade)"/>
  </g>
  <circle cx="300" cy="300" r="289.5" fill="none" stroke="rgba(255,255,255,.28)" stroke-width="1"/>
</svg>"""

WORDS = [  # (texto, x, y, tamaño, opacidad, velocidad de paralaje, contorno)
    ("Hola", "6%", "14%", "clamp(44px,8vw,120px)", .16, .30, False), ("Hello", "62%", "10%", "clamp(60px,12vw,190px)", .13, .12, True),
    ("Bonjour", "22%", "28%", "clamp(34px,6vw,92px)", .20, .42, False), ("你好", "78%", "36%", "clamp(60px,10vw,160px)", .15, .22, False),
    ("Ciao", "3%", "27%", "clamp(50px,9vw,140px)", .12, .18, True), ("こんにちは", "52%", "58%", "clamp(34px,6vw,88px)", .22, .50, False),
    ("Olá", "84%", "70%", "clamp(40px,7vw,110px)", .14, .34, True), ("Hallo", "36%", "12%", "clamp(30px,5vw,72px)", .17, .55, False),
    ("Привет", "70%", "84%", "clamp(30px,5vw,76px)", .18, .26, False), ("안녕", "40%", "80%", "clamp(44px,8vw,120px)", .14, .40, False),
]


def words_layers() -> str:
    out = []
    for text, x, y, s, o, sp, outline in WORDS:
        cls = "layer word word--out" if outline else "layer word"
        out.append(f'<span class="{cls}" style="--x:{x};--y:{y};--s:{s};--o:{o}" data-parallax="{-sp}" aria-hidden="true" lang="und">{text}</span>')
    return "\n    ".join(out)


# ============================================================
# 1 · PORTADA  (satsh.org)
# ============================================================
def build_home() -> str:
    root = ""
    body = f"""<main id="main">

  <section class="panel" id="top">
    <div class="layer layer--glow" data-parallax="0.30"></div>
    <div class="layer layer--limb" data-parallax="0.16"></div>
    <div class="layer layer--haze"></div>
    <div class="panel__content">
      <p class="eyebrow reveal">{L("Proyectos de software y ciencia", "Software &amp; science projects")}</p>
      <h1 class="display reveal">SATSH</h1>
      <p class="lead reveal">{L("Una firma para lo que construyo: herramientas para simular, explorar y aprender.",
                                 "A signature for what I build: tools to simulate, explore and learn.")}</p>
      <div class="actions reveal"><a class="btn" href="#projects">{L("Ver proyectos", "View projects")} <span class="arrow">↓</span></a></div>
    </div>
    <span class="scroll-hint" aria-hidden="true"></span>
  </section>

  <section class="panel" id="projects" aria-labelledby="p-lunagen">
    <div class="layer layer--moon" data-parallax="0.14">{MOON_SVG}</div>
    <div class="layer layer--cells" data-parallax="0.06"><canvas data-cells="46" aria-hidden="true"></canvas></div>
    <div class="layer layer--vignette"></div>
    <div class="panel__content">
      <p class="eyebrow reveal">{L("01 — Proyecto · Librería de Python", "01 — Project · Python library")}</p>
      <h2 class="display display--md reveal" id="p-lunagen">LUNAGEN</h2>
      <p class="lead reveal">{L("Simulación de cultivos basada en agentes. Describe un organismo, elige qué optimizar y míralo trabajar en una ventana en vivo.",
                                 "Agent-based culture simulation. Describe an organism, choose what to optimize and watch it work in a live window.")}</p>
      <div class="actions reveal">
        <a class="btn" href="lunagen/">{L("Explorar Lunagen", "Explore Lunagen")} <span class="arrow">→</span></a>
        <a class="btn btn--ghost" href="lunagen/docs/">{L("Documentación", "Documentation")}</a>
      </div>
    </div>
  </section>

  <section class="panel" id="impara" aria-labelledby="p-impara">
    <div class="layer layer--warm" data-parallax="0.18"></div>
    {words_layers()}
    <div class="layer layer--vignette"></div>
    <div class="panel__content">
      <p class="eyebrow reveal">{L("02 — Proyecto · App para Android", "02 — Project · Android app")}</p>
      <span class="chip-status reveal">{L("En desarrollo", "In development")}</span>
      <h2 class="display display--md reveal" id="p-impara">IMPARA</h2>
      <p class="lead reveal">{L("Una app para aprender idiomas en Android. Todavía en desarrollo.",
                                 "A language-learning app for Android. Still in development.")}</p>
      <div class="actions reveal">
        <a class="btn" href="{IMPARA}" target="_blank" rel="noopener">{L("Visitar impara.org", "Visit impara.org")} <span class="arrow">↗</span></a>
      </div>
    </div>
  </section>

  <section class="section section--bordered section--dark" aria-labelledby="all-projects">
    <div class="section__inner">
      <h2 class="title reveal" id="all-projects">{L("Todos los proyectos", "All projects")}</h2>
      <div class="index-list reveal">
        <a href="lunagen/"><span class="n">01</span><span class="t"><strong>Lunagen</strong><small>{L("Librería de Python · simulación y optimización de cultivos", "Python library · culture simulation and optimization")}</small></span><span class="go">→</span></a>
        <a href="{IMPARA}" target="_blank" rel="noopener"><span class="n">02</span><span class="t"><strong>Impara</strong><small>{L("App de idiomas para Android · en desarrollo", "Language app for Android · in development")}</small></span><span class="go">↗</span></a>
      </div>
    </div>
  </section>

</main>
"""
    return page(root, "", ("satsh — Proyectos de software y ciencia", "satsh — Software & science projects"),
                ("Portada de satsh: Lunagen, una librería de Python para simular y optimizar cultivos, e Impara, una app de idiomas para Android en desarrollo.",
                 "satsh home: Lunagen, a Python library to simulate and optimize cultures, and Impara, a language-learning Android app in development."),
                "og-satsh.png", "home", body)


# ============================================================
# 2 · LUNAGEN  (satsh.org/lunagen/)
# ============================================================
QUICK = '''import lunagen as lg

if __name__ == "__main__":
    organismo = lg.presets.komagataeibacter_xylinus()
    estudio = lg.Study(organismo, objective="yield[cellulose]", workers=4)
    resultado = estudio.optimize(samples=60, generations=8, population=16, viz=True)
    print(resultado.best_conditions, resultado.best_value)'''

QUICK_EN = QUICK.replace("organismo", "organism").replace("estudio", "study").replace("resultado", "result")

OTHER = '''# Another question, same organism
lg.Study(org, objective="mean_lifespan_h", space=["temperature_c", "ph"])        # lifespan
lg.Study(org, objective="doubling_time_h", direction="min")                      # reproduction
lg.Study(org, objective={"yield[cellulose]": 1.0, "survival_fraction": 2.0},     # several goals
         constraints=[("final_population", ">=", 100)])                          # and constraints

# Work with only some variables
lg.Study(org, space=["temperature_c", "ph"], fixed={"glucose_gl": 30})

# A metric of your own
@lg.metric("viability", unit="%")
def viability(result, cond, ctx):
    return 100 * result.final_alive / max(1, result.peak_alive)'''

OTHER_ES = '''# Otra pregunta, el mismo organismo
lg.Study(org, objective="mean_lifespan_h", space=["temperature_c", "ph"])        # tiempo de vida
lg.Study(org, objective="doubling_time_h", direction="min")                      # reproducción
lg.Study(org, objective={"yield[cellulose]": 1.0, "survival_fraction": 2.0},     # varios objetivos
         constraints=[("final_population", ">=", 100)])                          # y restricciones

# Operar solo con algunas variables
lg.Study(org, space=["temperature_c", "ph"], fixed={"glucose_gl": 30})

# Una métrica propia
@lg.metric("viabilidad", unit="%")
def viabilidad(result, cond, ctx):
    return 100 * result.final_alive / max(1, result.peak_alive)'''

METRICS = ["yield[p]", "efficiency[p]", "productivity[p]", "max_growth_rate", "doubling_time_h", "peak_population",
           "final_population", "mean_lifespan_h", "median_lifespan_h", "survival_fraction", "extinction_time_h",
           "death_fraction[cause]", "nutrient_consumed_fraction", "total_divisions"]


def picture(name: str, alt_es: str, alt_en: str) -> str:
    return (f'<picture><source srcset="../assets/img/{name}.webp" type="image/webp">'
            f'<img src="../assets/img/{name}.png" width="1600" height="900" loading="lazy" '
            f'alt="{alt_en}" data-alt-es="{alt_es}" data-alt-en="{alt_en}"></picture>')


def build_lunagen() -> str:
    root = "../"
    chips = "".join(f'<span class="chip">{m}</span>' for m in METRICS)
    body = f"""<main id="main">

  <section class="panel" id="top">
    <div class="layer layer--moon" data-parallax="0.16">{MOON_SVG}</div>
    <div class="layer layer--cells" data-parallax="0.07"><canvas data-cells="90" aria-hidden="true"></canvas></div>
    <div class="layer layer--vignette"></div>
    <div class="panel__content">
      <p class="eyebrow reveal">{L("satsh · librería de Python", "satsh · Python library")}</p>
      <h1 class="display reveal">LUNAGEN</h1>
      <p class="lead reveal">{L("Simula un cultivo célula por célula y encuentra las condiciones óptimas. Configurable, optimizable y con visualización en vivo.",
                                 "Simulate a culture cell by cell and find the optimal conditions. Configurable, optimizable and with a live visualization.")}</p>
      <div class="reveal" style="margin:0 0 30px">
        <div class="install"><code>pip install lunagen</code><button class="copy" type="button" data-copy="pip install lunagen">{L("Copiar", "Copy")}</button></div>
      </div>
      <div class="actions reveal">
        <a class="btn" href="docs/">{L("Documentación", "Documentation")} <span class="arrow">→</span></a>
        <a class="btn btn--ghost" href="{PYPI}" target="_blank" rel="noopener">{L("Ver en PyPI", "View on PyPI")} ↗</a>
      </div>
      <div class="badges reveal"><span class="badge">v{VERSION}</span><span class="badge">Python 3.9+</span><span class="badge">MIT</span>
        <span class="badge">lunagen[viz]</span></div>
    </div>
    <span class="scroll-hint" aria-hidden="true"></span>
  </section>

  <section class="section section--dark" id="overview" aria-labelledby="t-overview">
    <div class="section__inner">
      <p class="eyebrow reveal">{L("Resumen", "Overview")}</p>
      <h2 class="title reveal" id="t-overview">{L("De la célula al óptimo", "From the cell to the optimum")}</h2>
      <p class="lead reveal">{L("El motor no sabe nada de ningún organismo concreto: todo lo específico se declara. Con el mismo código puedes estudiar celulosa bacteriana, ácido láctico, etanol, tiempo de vida o reproducción.",
                                 "The engine knows nothing about any particular organism: everything specific is declared. With the same code you can study bacterial cellulose, lactic acid, ethanol, lifespan or reproduction.")}</p>
      <div class="grid grid--3" style="margin-top:56px">
        <div class="feature reveal"><div class="num">01</div><h3>{L("Simula", "Simulate")}</h3>
          <p>{L("Un agente por célula: metabolismo, crecimiento, división, muerte y producción de uno o varios compuestos. Determinista para cada semilla.",
                "One agent per cell: metabolism, growth, division, death and production of one or several compounds. Deterministic for every seed.")}</p></div>
        <div class="feature reveal"><div class="num">02</div><h3>{L("Optimiza", "Optimize")}</h3>
          <p>{L("Exploración, refinamiento evolutivo y validación con semillas nuevas. Maximiza o minimiza lo que definas, con restricciones y varios objetivos.",
                "Exploration, evolutionary refinement and validation with fresh seeds. Maximize or minimize whatever you define, with constraints and several goals.")}</p></div>
        <div class="feature reveal"><div class="num">03</div><h3>{L("Declara", "Declare")}</h3>
          <p>{L("Variables, curvas de respuesta y productos descritos en unas decenas de líneas. Recalibra con perillas, sin tocar el motor.",
                "Variables, response curves and products described in a few dozen lines. Recalibrate with knobs, without touching the engine.")}</p></div>
        <div class="feature reveal"><div class="num">04</div><h3>{L("Visualiza", "Visualize")}</h3>
          <p>{L("Cada simulación se anima en cámara rápida: caja Petri, telemetría en tiempo real, optimizador y log, estilo consola de ciencia ficción.",
                "Every simulation is animated in fast motion: Petri dish, real-time telemetry, optimizer and log, in a sci-fi console style.")}</p></div>
      </div>
    </div>
  </section>

  <section class="section section--bordered section--dark" id="how" aria-labelledby="t-how">
    <div class="section__inner">
      <p class="eyebrow reveal">{L("Cómo funciona", "How it works")}</p>
      <h2 class="title reveal" id="t-how">{L("Cuatro pasos", "Four steps")}</h2>
      <ol class="steps">
        <li class="reveal"><div><h3>{L("Describe el organismo", "Describe the organism")}</h3><p>{L("Variables que se controlan, cómo responde al entorno y qué produce. Hay un preset de <em>Komagataeibacter xylinus</em> listo para usar.",
            "The variables you control, how it responds to the environment and what it produces. A ready-to-use <em>Komagataeibacter xylinus</em> preset is included.")}</p></div></li>
        <li class="reveal"><div><h3>{L("Elige qué medir", "Choose what to measure")}</h3><p>{L("Rendimiento de un producto, eficiencia, tasa de crecimiento, tiempo de vida, supervivencia… o una métrica propia.",
            "A product's yield, efficiency, growth rate, lifespan, survival… or a metric of your own.")}</p></div></li>
        <li class="reveal"><div><h3>{L("Optimiza", "Optimize")}</h3><p>{L("Línea base, exploración, refinamiento evolutivo y validación. Todo se imprime en consola y se anima en la ventana.",
            "Baseline, exploration, evolutionary refinement and validation. Everything is printed to the console and animated in the window.")}</p></div></li>
        <li class="reveal"><div><h3>{L("Exporta", "Export")}</h3><p>{L("<code>evaluations.csv</code>, <code>results.json</code> y un XML con la mejor condición, listo para Unity.",
            "<code>evaluations.csv</code>, <code>results.json</code> and an XML with the best condition, ready for Unity.")}</p></div></li>
      </ol>
    </div>
  </section>

  <section class="section section--bordered" id="window" aria-labelledby="t-window">
    <div class="section__inner">
      <p class="eyebrow reveal">{L("Ventana en vivo", "Live window")}</p>
      <h2 class="title reveal" id="t-window">{L("Mira cada simulación trabajar", "Watch every simulation work")}</h2>
      <p class="lead reveal">{L("Quién vive, muere o se divide; el tamaño de cada cápsula es su fase del ciclo celular y su color, su reserva; las fibras son lo producido y el brillo ámbar, el nutriente que queda. Solo las posiciones son decorativas.",
                                 "Who lives, dies or divides; the size of each capsule is its phase of the cell cycle and its color its reserve; the fibers are what was produced and the amber glow the nutrient left. Only the positions are decorative.")}</p>
      <div class="grid grid--2" style="margin-top:56px;gap:clamp(24px,3vw,48px)">
        <figure class="reveal" style="margin:0"><div class="shot" data-parallax="-0.04">{picture("lunagen-live-1", "Ventana en vivo de Lunagen con la caja Petri llena de colonias", "Lunagen live window with a Petri dish full of colonies")}</div>
          <figcaption class="shot-caption">{L("Crecimiento de la población", "Population growth")}</figcaption></figure>
        <figure class="reveal" style="margin:0"><div class="shot" data-parallax="0.04">{picture("lunagen-live-2", "Ventana en vivo de Lunagen en una etapa posterior", "Lunagen live window at a later stage")}</div>
          <figcaption class="shot-caption">{L("Nutriente agotado: las reservas se vacían", "Nutrient exhausted: reserves run out")}</figcaption></figure>
      </div>
    </div>
  </section>

  <section class="section section--bordered section--dark" id="code" aria-labelledby="t-code">
    <div class="section__inner">
      <p class="eyebrow reveal">{L("Código", "Code")}</p>
      <h2 class="title reveal" id="t-code">{L("Pocas líneas, muchas preguntas", "A few lines, many questions")}</h2>
      <div class="grid grid--2" style="margin-top:44px;align-items:start">
        <div><div data-lang="es">{code_block(QUICK)}</div><div data-lang="en">{code_block(QUICK_EN)}</div></div>
        <div><div data-lang="es">{code_block(OTHER_ES)}</div><div data-lang="en">{code_block(OTHER)}</div></div>
      </div>
      <h3 class="eyebrow reveal" style="margin-top:72px">{L("Métricas incluidas", "Built-in metrics")}</h3>
      <div class="chips reveal">{chips}<span class="chip">+ {L("las tuyas", "your own")}</span></div>
    </div>
  </section>

  <section class="section section--bordered cta" aria-labelledby="t-cta">
    <div class="section__inner">
      <h2 class="title reveal" id="t-cta">{L("Empieza con la documentación", "Start with the documentation")}</h2>
      <p class="lead reveal">{L("Conceptos, el modelo y sus ecuaciones, cómo describir un organismo nuevo, calibración, referencia de la API y más.",
                                 "Concepts, the model and its equations, how to describe a new organism, calibration, the API reference and more.")}</p>
      <div class="actions reveal">
        <a class="btn" href="docs/">{L("Abrir la documentación", "Open the documentation")} <span class="arrow">→</span></a>
        <a class="btn btn--ghost" href="{PYPI}" target="_blank" rel="noopener">PyPI ↗</a>
      </div>
    </div>
  </section>

</main>
"""
    return page(root, "lunagen/", ("Lunagen — Simulación de cultivos basada en agentes", "Lunagen — Agent-based culture simulation"),
                ("Lunagen: librería de Python para simular cultivos célula por célula, optimizar condiciones y verlo en una ventana en vivo.",
                 "Lunagen: a Python library to simulate cultures cell by cell, optimize conditions and watch it in a live window."),
                "og-lunagen.png", "lunagen", body)


# ============================================================
# 3 · DOCUMENTACIÓN  (satsh.org/lunagen/docs/)
# ============================================================
def slug(value: str, sep: str = "-") -> str:
    """Igual que GitHub: minúsculas, sin signos, espacios → guiones (conserva acentos)."""
    value = unicodedata.normalize("NFC", value).lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"\s+", sep, value)


def render_md(path: str, lang: str):
    src = open(os.path.join(ROOT, "tools", "docs", path), encoding="utf-8").read()
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"],
                           extension_configs={"toc": {"slugify": slug, "toc_depth": "2-3"}})
    out = md.convert(src)
    # ids únicos por idioma (los dos idiomas viven en la misma página)
    out = re.sub(r'(<h[23] id=")', lambda m: m.group(1) + f"{lang}-", out)
    out = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{lang}-{m.group(1)}"', out)
    out = out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    out = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', out)
    toc = []
    for t in md.toc_tokens:
        sub = "".join(f'<li><a href="#{lang}-{c["id"]}">{html.escape(c["name"])}</a></li>' for c in t["children"])
        toc.append(f'<li><a href="#{lang}-{t["id"]}">{html.escape(t["name"])}</a>' + (f"<ul>{sub}</ul>" if sub else "") + "</li>")
    return out, "<ul>" + "".join(toc) + "</ul>"


def build_docs() -> str:
    root = "../../"
    es_html, es_toc = render_md("lunagen.es.md", "es")
    en_html, en_toc = render_md("lunagen.en.md", "en")
    body = f"""<main id="main">
  <section class="docs-hero">
    <p class="eyebrow">Lunagen · v{VERSION}</p>
    <h1 class="display">{L("Documentación", "Documentation")}</h1>
    <p>{L("Todo lo que necesitas para simular, optimizar y visualizar cultivos con Lunagen: del primer ejemplo a la referencia de la API.",
          "Everything you need to simulate, optimize and visualize cultures with Lunagen: from the first example to the API reference.")}</p>
    <div class="docs-nav">
      <a class="btn btn--ghost" href="../">← Lunagen</a>
      <a class="btn btn--ghost" href="{PYPI}" target="_blank" rel="noopener">PyPI ↗</a>
    </div>
  </section>
  <div class="docs">
    <button class="btn btn--ghost toc-toggle" type="button">{L("Contenido", "Contents")}</button>
    <nav class="toc" aria-label="Table of contents">
      <p class="toc-title">{L("En esta página", "On this page")}</p>
      <div data-lang="es">{es_toc}</div><div data-lang="en">{en_toc}</div>
    </nav>
    <article class="prose">
      <div data-lang="es" lang="es">{es_html}</div>
      <div data-lang="en" lang="en">{en_html}</div>
    </article>
  </div>
</main>
"""
    return page(root, "lunagen/docs/", ("Documentación de Lunagen", "Lunagen documentation"),
                ("Documentación de Lunagen en español: instalación, el modelo, cómo describir un organismo, métricas, optimización, ventana en vivo y referencia de la API.",
                 "Lunagen documentation: installation, the model, how to describe an organism, metrics, optimization, the live window and the API reference."),
                "og-lunagen.png", "docs", body)


# ============================================================
# 404, robots, sitemap, CNAME
# ============================================================
def build_404() -> str:
    body = f"""<main id="main" class="center-page"><div>
  <p class="eyebrow">404</p>
  <h1 class="display display--md">{L("Página no encontrada", "Page not found")}</h1>
  <p class="lead" style="margin-left:auto;margin-right:auto">{L("Esta dirección no existe (todavía).", "This address does not exist (yet).")}</p>
  <div class="actions" style="justify-content:center"><a class="btn" href="/">{L("Ir al inicio", "Go home")}</a></div>
</div></main>
"""
    # el 404 se sirve desde cualquier ruta: rutas absolutas
    h = head("/", "404.html", ("Página no encontrada — satsh", "Page not found — satsh"),
             ("Página no encontrada.", "Page not found."), "og-satsh.png")
    return (h + '<body>\n<canvas id="stars" aria-hidden="true"></canvas>\n' + header("/", "home").replace('href="#projects"', 'href="/#projects"')
            + body + '<script src="/assets/js/site.js" defer></script>\n</body>\n</html>\n')


def build_extras() -> None:
    write("CNAME", DOMAIN + "\n")
    write(".nojekyll", "")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    today = datetime.date.today().isoformat()
    urls = ["", "lunagen/", "lunagen/docs/"]
    items = "".join(f"  <url><loc>{SITE}/{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{items}</urlset>\n')


if __name__ == "__main__":
    print("Generando el sitio…")
    write("index.html", build_home())
    write("lunagen/index.html", build_lunagen())
    write("lunagen/docs/index.html", build_docs())
    write("404.html", build_404())
    build_extras()
    print("Listo.")
