# satsh.org — sitio de satsh, Lunagen y documentación

Sitio estático (HTML + CSS + JS, sin dependencias) listo para **GitHub Pages**.
Estilo inspirado en las páginas de SpaceX: negro, paneles a pantalla completa, tipografía en mayúsculas,
efecto paralaje y un campo de estrellas. **Bilingüe**: usa el idioma del navegador (español o inglés) y tiene
un selector ES / EN que recuerda la elección.

| Dirección | Archivo |
|---|---|
| `satsh.org` | `index.html` |
| `satsh.org/lunagen/` | `lunagen/index.html` |
| `satsh.org/lunagen/docs/` | `lunagen/docs/index.html` |

`impara.org` es un sitio aparte: desde aquí solo se enlaza.

## Publicar en GitHub Pages (con el dominio satsh.org)

1. Crea un repositorio en GitHub (por ejemplo `satsh-site`) y sube **el contenido de esta carpeta** a la rama `main`
   (que `index.html` y `CNAME` queden en la raíz del repositorio):
   ```bash
   cd satsh-site
   git init && git add . && git commit -m "Sitio satsh"
   git branch -M main
   git remote add origin https://github.com/TU-USUARIO/satsh-site.git
   git push -u origin main
   ```
2. En el repositorio: **Settings → Pages → Build and deployment → Source: Deploy from a branch**, rama `main`, carpeta `/ (root)`.
3. En **Settings → Pages → Custom domain** escribe `satsh.org` (el archivo `CNAME` ya lo trae).
4. En el proveedor donde registraste el dominio, crea estos registros DNS:
   | Tipo | Nombre | Valor |
   |---|---|---|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `TU-USUARIO.github.io` |
   (Comprueba las direcciones vigentes en la documentación de GitHub Pages: "Managing a custom domain".)
5. Espera a que GitHub verifique el DNS (de minutos a unas horas) y activa **Enforce HTTPS**.

Las rutas del sitio son relativas, así que también funciona en `https://TU-USUARIO.github.io/satsh-site/`
mientras pruebas.

## Probarlo en tu equipo

```bash
cd satsh-site
python -m http.server 8000      # y abre http://localhost:8000
```

## Editar contenido

Los HTML ya están generados y se pueden publicar tal cual. Para cambiar textos sin editar HTML a mano:

```bash
pip install markdown pillow numpy
python tools/build.py           # regenera index.html, lunagen/, lunagen/docs/, 404, sitemap…
python tools/make_images.py     # regenera las imágenes de vista previa social y el favicon
```

- **Textos de las páginas** (español e inglés juntos): `tools/build.py`.
- **Documentación**: `tools/docs/lunagen.es.md` y `tools/docs/lunagen.en.md` (Markdown).
- **Estilos**: `assets/css/site.css` · **Comportamiento** (idioma, paralaje, estrellas): `assets/js/site.js`.
- **Imágenes de la ventana en vivo** (`assets/img/lunagen-live-*.png/.webp`): son vistas generadas con el código de
  dibujo de Lunagen en un entorno de pruebas sin pantalla. Cámbialas por capturas reales de tu ventana con el mismo
  nombre (conserva el formato 1600×900).

## Notas

- Al subir una versión nueva de Lunagen, cambia `VERSION` en `tools/build.py` y la documentación, y vuelve a generar.
- El selector de idioma guarda la preferencia en `localStorage` (clave `satsh-lang`).
- Si el visitante activa "reducir movimiento" en su sistema, se desactivan el paralaje y las animaciones.
- `satsh` aparece sin símbolos de marca registrada, porque aún no la registras.
