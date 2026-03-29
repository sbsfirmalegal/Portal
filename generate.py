"""
FIRMA LEGAL S.B.S. — Generador de Portales de Cliente
Conecta con Notion y genera un archivo HTML por proceso activo.
"""

import os, json
from datetime import datetime

try:
    from notion_client import Client
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "notion-client"])
    from notion_client import Client

# ── CONFIGURACIÓN ────────────────────────────────────────────────────────────
NOTION_TOKEN    = os.environ["NOTION_TOKEN"]
PROCESOS_DB_ID  = os.environ.get("PROCESOS_DB_ID",  "cdaf65f1d417491aa54e9a82daa5b50d")
HONORARIOS_DB_ID= os.environ.get("HONORARIOS_DB_ID","d53925ac-b7bb-4379-8e54-d3cf48dcca48")
CLIENTES_DB_ID  = os.environ.get("CLIENTES_DB_ID",  "83a731f4-7afd-4345-9e3b-8d699724bc2a")
OUTPUT_DIR      = "portals"

notion = Client(auth=NOTION_TOKEN)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── HELPERS ──────────────────────────────────────────────────────────────────
def get_prop(props, name, fallback=""):
    p = props.get(name)
    if not p: return fallback
    t = p.get("type","")
    if t == "title":      return "".join(r["plain_text"] for r in p.get("title",[]))
    if t == "rich_text":  return "".join(r["plain_text"] for r in p.get("rich_text",[]))
    if t == "select":     s = p.get("select"); return s["name"] if s else fallback
    if t == "checkbox":   return p.get("checkbox", False)
    if t == "number":     return p.get("number") or 0
    if t == "date":       d = p.get("date"); return d["start"] if d else fallback
    if t == "relation":   return [r["id"] for r in p.get("relation",[])]
    if t == "rollup":
        r = p.get("rollup",{}); rt = r.get("type","")
        if rt == "number": return r.get("number") or 0
        if rt == "array":
            nums = [item.get("number",0) for item in r.get("array",[]) if item.get("type")=="number"]
            return sum(nums)
    if t == "formula":
        f = p.get("formula",{}); ft = f.get("type","")
        if ft == "number": return f.get("number") or 0
        if ft == "string": return f.get("string") or fallback
    if t == "phone_number": return p.get("phone_number","")
    if t == "email":        return p.get("email","")
    if t == "url":          return p.get("url","")
    return fallback

def fmt_date(s):
    if not s or s == "—": return "—"
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d")
        m = ["enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]
        return f"{d.day} de {m[d.month-1]} de {d.year}"
    except: return s

def fmt_date_short(s):
    if not s: return "—"
    try:
        d = datetime.strptime(s[:10], "%Y-%m-%d")
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    except: return s

def fmt_day(s):
    if not s: return "—"
    try: return str(datetime.strptime(s[:10], "%Y-%m-%d").day)
    except: return "—"

def fmt_month(s):
    if not s: return ""
    try:
        m = ["ENE","FEB","MAR","ABR","MAY","JUN",
             "JUL","AGO","SEP","OCT","NOV","DIC"]
        return m[datetime.strptime(s[:10], "%Y-%m-%d").month - 1]
    except: return ""

def cur(v):
    try: return f"${float(v):,.2f}"
    except: return "$0.00"

def estado_class(e):
    return {"En trámite":"pill-tramite","En espera de resolución":"pill-espera",
            "Urgente":"pill-urgente","Listo para entrega":"pill-listo",
            "Cerrado — Favorable":"pill-cerrado","Cerrado — Desfavorable":"pill-cerrado"
           }.get(e,"pill-tramite")

def pct_bar(cobrado, pactado):
    try:
        p = min(100, round(float(cobrado)/float(pactado)*100)) if float(pactado)>0 else 0
        return p
    except: return 0

# ── FETCH DATA ────────────────────────────────────────────────────────────────
def get_all_pages(db_id, filter_obj=None):
    pages, cursor = [], None
    while True:
        kwargs = {"database_id": db_id, "page_size": 100}
        if filter_obj: kwargs["filter"] = filter_obj
        if cursor: kwargs["start_cursor"] = cursor
        res = notion.databases.query(**kwargs)
        pages.extend(res.get("results",[]))
        if not res.get("has_more"): break
        cursor = res.get("next_cursor")
    return pages

def get_client_name(page_id):
    try:
        p = notion.pages.retrieve(page_id)
        return get_prop(p["properties"], "Nombre completo", "—")
    except: return "—"

def get_honorarios(nie_page_id):
    rows = get_all_pages(HONORARIOS_DB_ID, {
        "property": "Proceso (NIE)",
        "relation": {"contains": nie_page_id}
    })
    pagos = []
    for r in rows:
        props = r["properties"]
        pagos.append({
            "concepto":  get_prop(props,"Concepto"),
            "tipo":      get_prop(props,"Tipo de movimiento"),
            "monto":     get_prop(props,"Monto recibido ($)",0),
            "forma":     get_prop(props,"Forma de pago"),
            "fecha":     get_prop(props,"Fecha de pago"),
            "registrado":get_prop(props,"Registrado por"),
            "notas":     get_prop(props,"Observaciones"),
        })
    pagos.sort(key=lambda x: x["fecha"] or "")
    return pagos

# ── HTML GENERATOR ────────────────────────────────────────────────────────────
def generate_portal(proc, client_name, pagos):
    props = proc["properties"]
    nie         = get_prop(props,"NIE")
    asunto      = get_prop(props,"Asunto específico")
    tipo        = get_prop(props,"Tipo de proceso")
    materia     = get_prop(props,"Materia")
    estado      = get_prop(props,"Estado","En trámite")
    abogado_raw = get_prop(props,"Abogado asignado","")
    apertura    = get_prop(props,"Fecha de apertura")
    audiencia   = get_prop(props,"Fecha de próxima audiencia")
    nota_cli    = get_prop(props,"Nota para el cliente","") or ""
    pactado     = float(get_prop(props,"Honorario pactado ($)",0) or 0)
    cobrado_r   = float(get_prop(props,"Total cobrado ($)",0) or 0)
    # Sum manually from pagos as fallback
    cobrado     = cobrado_r if cobrado_r > 0 else sum(float(p["monto"] or 0) for p in pagos)
    pendiente   = max(0, pactado - cobrado)
    pct         = pct_bar(cobrado, pactado)
    e_class     = estado_class(estado)
    updated     = proc.get("last_edited_time","")[:10]

    abogado_map = {
        "Nelson A. Castillo B.": "Nelson Alexander Castillo Barrera",
        "Fátima A. Serrano D.":  "Fátima Alejandra Serrano Díaz",
        "Estela S. Sandoval S.": "Estela Saraí Sandoval Sandoval",
        "Conjunto":              "Equipo S.B.S. — Los tres miembros"
    }
    abogado_full = abogado_map.get(abogado_raw, abogado_raw)
    abogado_ini  = "T" if "Conjunto" in abogado_raw else (abogado_raw[0] if abogado_raw else "N")

    # Pagos HTML rows
    pagos_html = ""
    for p in pagos:
        pagos_html += f"""
        <div class="pago-row">
          <div class="pr-fecha">{fmt_date_short(p['fecha'])}</div>
          <div class="pr-tipo"><span class="pr-tag">{p['tipo']}</span></div>
          <div class="pr-concepto">{p['concepto']}</div>
          <div class="pr-forma">{p['forma']}</div>
          <div class="pr-monto">{cur(p['monto'])}</div>
        </div>"""

    if not pagos_html:
        pagos_html = '<div style="color:rgba(255,255,255,0.28);font-size:12px;padding:.5rem 0;">Sin movimientos registrados aún.</div>'

    # Próxima audiencia
    if audiencia and audiencia != "—":
        fecha_box = f"""
        <div class="fecha-row">
          <div class="fecha-box">
            <div class="fecha-dia">{fmt_day(audiencia)}</div>
            <div class="fecha-mes">{fmt_month(audiencia)}</div>
          </div>
          <div class="fecha-info">
            <div class="fecha-tipo">Próxima diligencia</div>
            <div class="fecha-desc">{fmt_date(audiencia)}</div>
          </div>
        </div>"""
    else:
        fecha_box = '<div style="color:rgba(255,255,255,0.28);font-size:12px;padding:.4rem 0;">Sin fechas programadas por el momento.</div>'

    # Nota para el cliente
    nota_block = ""
    if nota_cli.strip():
        nota_block = f"""
        <div class="novedad">
          <div class="nov-meta">
            <span class="nov-quien">{abogado_full.split()[0]} {abogado_full.split()[-1]}</span>
            <span class="nov-fecha">{fmt_date_short(updated)}</span>
            <span class="nov-tag info">NOVEDAD</span>
          </div>
          <div class="nov-texto">{nota_cli}</div>
        </div>"""
    else:
        nota_block = '<div style="color:rgba(255,255,255,0.28);font-size:12px;padding:.4rem 0;">No hay novedades publicadas aún. Le comunicaremos cuando haya avances relevantes.</div>'

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Mi Proceso — Firma Legal S.B.S.</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
:root{{--navy:#13284e;--navy-deep:#0c1c38;--gold:#C9A84C;--gold-light:#e0c270;--gold-bg:rgba(201,168,76,0.08);--gold-border:rgba(201,168,76,0.22);--white:#fff;--border-dark:rgba(255,255,255,0.07);}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'DM Sans',sans-serif;background:var(--navy-deep);min-height:100vh;color:#fff;}}
.ph{{background:rgba(0,0,0,0.42);border-bottom:1px solid var(--border-dark);height:58px;display:flex;align-items:center;justify-content:space-between;padding:0 2rem;position:sticky;top:0;z-index:100;backdrop-filter:blur(10px);}}
.ph-l{{display:flex;align-items:center;gap:16px;}}
.ph-logo{{font-family:'Playfair Display',serif;font-size:14px;color:var(--gold);letter-spacing:2px;}}
.ph-sep{{width:1px;height:22px;background:rgba(255,255,255,0.12);}}
.ph-tag{{font-size:10px;letter-spacing:3px;color:rgba(255,255,255,0.28);}}
.ph-r{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;}}
.ph-nie{{font-family:'DM Mono',monospace;font-size:11px;color:var(--gold);background:var(--gold-bg);border:1px solid var(--gold-border);padding:3px 11px;letter-spacing:1px;}}
.ph-client{{font-size:12px;color:rgba(255,255,255,0.45);}}
.ph-client strong{{color:rgba(255,255,255,0.82);}}
.ph-secure{{font-size:9px;letter-spacing:2px;color:rgba(100,210,160,0.75);background:rgba(100,210,160,0.07);border:1px solid rgba(100,210,160,0.2);padding:3px 10px;}}
.main{{max-width:1100px;margin:0 auto;padding:2rem 1.5rem;}}
.hero-card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);padding:2rem;margin-bottom:1.5rem;display:grid;grid-template-columns:1fr auto;align-items:center;gap:2rem;}}
.hero-eyebrow{{font-size:9px;letter-spacing:3px;color:rgba(255,255,255,0.22);margin-bottom:.5rem;display:block;}}
.hero-title{{font-family:'Playfair Display',serif;font-size:22px;color:var(--white);line-height:1.3;margin-bottom:.8rem;}}
.hero-meta{{display:flex;gap:1.2rem;flex-wrap:wrap;}}
.hm-item{{font-size:12px;color:rgba(255,255,255,0.35);}}
.hm-item span{{color:rgba(255,255,255,0.68);}}
.status-pill{{display:inline-flex;align-items:center;gap:8px;padding:9px 22px;font-size:11px;letter-spacing:2px;font-weight:600;white-space:nowrap;}}
.status-pill .dot{{width:8px;height:8px;border-radius:50%;background:currentColor;flex-shrink:0;}}
.pill-tramite{{background:rgba(74,111,165,0.15);border:1px solid rgba(74,111,165,0.3);color:#7aacf0;}}
.pill-urgente{{background:rgba(180,60,60,0.15);border:1px solid rgba(180,60,60,0.3);color:#e07878;}}
.pill-espera{{background:rgba(176,124,42,0.12);border:1px solid rgba(176,124,42,0.3);color:#d4a460;}}
.pill-listo{{background:rgba(45,122,95,0.1);border:1px solid rgba(45,122,95,0.3);color:#6ec898;}}
.pill-cerrado{{background:rgba(156,163,175,0.1);border:1px solid rgba(156,163,175,0.2);color:#9ca3af;}}
.two-col{{display:grid;grid-template-columns:1fr 310px;gap:1.5rem;margin-bottom:1.5rem;}}
.col-left,.col-right{{display:flex;flex-direction:column;gap:1.5rem;}}
.card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);padding:1.5rem;}}
.card-hdr{{font-size:9px;letter-spacing:3px;color:rgba(255,255,255,0.22);margin-bottom:1rem;display:flex;align-items:center;gap:8px;}}
.card-hdr::after{{content:'';flex:1;height:1px;background:rgba(255,255,255,0.06);}}
.novedad{{padding:.9rem 0;border-bottom:1px solid rgba(255,255,255,0.05);}}
.novedad:last-child{{border-bottom:none;}}
.nov-meta{{display:flex;align-items:center;gap:9px;margin-bottom:.45rem;flex-wrap:wrap;}}
.nov-quien{{font-size:11px;color:var(--gold);font-weight:500;}}
.nov-fecha{{font-size:10px;color:rgba(255,255,255,0.2);font-family:'DM Mono',monospace;}}
.nov-tag{{display:inline-block;font-size:9px;letter-spacing:1.5px;padding:2px 8px;margin-left:auto;}}
.nov-tag.info{{background:rgba(74,111,165,0.1);border:1px solid rgba(74,111,165,0.25);color:#7aacf0;}}
.nov-texto{{font-size:13px;color:rgba(255,255,255,0.6);line-height:1.65;}}
.pago-row{{display:grid;grid-template-columns:90px 110px 1fr 100px 90px;align-items:center;padding:.6rem 0;border-bottom:1px solid rgba(255,255,255,0.04);gap:8px;font-size:12px;}}
.pago-row:last-child{{border-bottom:none;}}
.pr-fecha{{font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,0.3);}}
.pr-tag{{display:inline-block;font-size:9px;letter-spacing:1px;padding:2px 7px;background:var(--gold-bg);border:1px solid var(--gold-border);color:var(--gold);}}
.pr-concepto{{color:rgba(255,255,255,0.65);}}
.pr-forma{{font-size:11px;color:rgba(255,255,255,0.3);}}
.pr-monto{{font-family:'DM Mono',monospace;color:#6ec898;text-align:right;}}
.abogado-row{{display:flex;align-items:center;gap:12px;margin-bottom:1.2rem;}}
.av-circle{{width:46px;height:46px;border-radius:50%;background:rgba(74,111,165,0.18);border:2px solid rgba(74,111,165,0.35);display:flex;align-items:center;justify-content:center;font-size:17px;font-weight:600;color:#6fa0e0;flex-shrink:0;}}
.av-nombre{{font-size:13.5px;color:rgba(255,255,255,0.85);font-weight:500;}}
.av-cargo{{font-size:10px;color:rgba(255,255,255,0.28);margin-top:2px;}}
.contact-line{{display:flex;align-items:center;gap:9px;padding:.55rem 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:12px;}}
.contact-line:last-child{{border-bottom:none;}}
.cl-label{{color:rgba(255,255,255,0.22);font-size:10px;letter-spacing:.5px;min-width:55px;}}
.cl-val{{color:rgba(255,255,255,0.62);}}
.cl-val a{{color:var(--gold);text-decoration:none;}}
.fecha-row{{display:flex;gap:12px;padding:.75rem 0;border-bottom:1px solid rgba(255,255,255,0.05);}}
.fecha-row:last-child{{border-bottom:none;}}
.fecha-box{{width:44px;height:44px;background:var(--gold-bg);border:1px solid var(--gold-border);display:flex;flex-direction:column;align-items:center;justify-content:center;flex-shrink:0;}}
.fecha-dia{{font-family:'Playfair Display',serif;font-size:18px;color:var(--gold);line-height:1;}}
.fecha-mes{{font-size:8px;letter-spacing:1.5px;color:rgba(201,168,76,0.55);}}
.fecha-tipo{{font-size:11.5px;color:rgba(255,255,255,0.72);font-weight:500;}}
.fecha-desc{{font-size:10.5px;color:rgba(255,255,255,0.32);margin-top:2px;line-height:1.4;}}
.honor-line{{display:flex;justify-content:space-between;align-items:center;padding:.55rem 0;border-bottom:1px solid rgba(255,255,255,0.05);}}
.honor-line:last-child{{border-bottom:none;}}
.hl-label{{color:rgba(255,255,255,0.32);font-size:11px;}}
.hl-val{{font-family:'DM Mono',monospace;font-size:12px;}}
.hl-val.paid{{color:#6ec898;}} .hl-val.pending{{color:#e0b060;}} .hl-val.total{{color:rgba(255,255,255,0.68);}}
.honor-bar{{height:3px;background:rgba(255,255,255,0.06);margin:.8rem 0 4px;border-radius:2px;overflow:hidden;}}
.honor-fill{{height:100%;background:var(--gold);border-radius:2px;}}
.honor-pct{{font-size:10px;color:rgba(255,255,255,0.2);text-align:center;margin-bottom:.8rem;}}
.info-line{{display:flex;justify-content:space-between;align-items:flex-start;padding:.55rem 0;border-bottom:1px solid rgba(255,255,255,0.05);gap:8px;}}
.info-line:last-child{{border-bottom:none;}}
.il-label{{color:rgba(255,255,255,0.28);font-size:10.5px;letter-spacing:.5px;flex-shrink:0;}}
.il-val{{font-size:12px;color:rgba(255,255,255,0.62);text-align:right;line-height:1.4;}}
.portal-footer{{border-top:1px solid rgba(255,255,255,0.06);padding:1.5rem 2rem;text-align:center;}}
.footer-txt{{font-size:11px;color:rgba(255,255,255,0.18);letter-spacing:.5px;line-height:1.8;}}
.footer-txt a{{color:var(--gold);text-decoration:none;}}
.gen-badge{{position:fixed;bottom:12px;right:12px;font-size:9px;letter-spacing:1.5px;color:rgba(255,255,255,0.12);background:rgba(0,0,0,0.3);padding:3px 9px;border:1px solid rgba(255,255,255,0.06);}}
@media(max-width:780px){{.two-col{{grid-template-columns:1fr;}}.ph{{padding:0 1rem;}}.ph-nie,.ph-secure{{display:none;}}.main{{padding:1rem;}}.hero-card{{grid-template-columns:1fr;gap:1rem;}}.pago-row{{grid-template-columns:1fr 1fr;}}}}
</style>
</head>
<body>

<div class="ph">
  <div class="ph-l">
    <span class="ph-logo">FIRMA LEGAL S.B.S.</span>
    <div class="ph-sep"></div>
    <span class="ph-tag">PORTAL DE SEGUIMIENTO</span>
  </div>
  <div class="ph-r">
    <span class="ph-nie">{nie}</span>
    <span class="ph-client">Bienvenido/a, <strong>{client_name.split()[0]}</strong></span>
    <span class="ph-secure">🔒 ACCESO SEGURO</span>
  </div>
</div>

<div class="main">

  <div class="hero-card">
    <div>
      <span class="hero-eyebrow">EXPEDIENTE {nie} · PROCESO {tipo.upper()}</span>
      <div class="hero-title">{asunto}</div>
      <div class="hero-meta">
        <div class="hm-item">Materia: <span>{materia}</span></div>
        <div class="hm-item">Apertura: <span>{fmt_date(apertura)}</span></div>
        <div class="hm-item">Abogado/a: <span>{abogado_full}</span></div>
      </div>
    </div>
    <div class="status-pill {e_class}">
      <div class="dot"></div>
      {estado.upper()}
    </div>
  </div>

  <div class="two-col">
    <div class="col-left">

      <div class="card">
        <div class="card-hdr">NOVEDADES DEL PROCESO</div>
        {nota_block}
      </div>

      <div class="card">
        <div class="card-hdr">HISTORIAL DE PAGOS</div>
        {pagos_html}
      </div>

    </div>
    <div class="col-right">

      <div class="card">
        <div class="card-hdr">SU ABOGADO/A ASIGNADO/A</div>
        <div class="abogado-row">
          <div class="av-circle">{abogado_ini}</div>
          <div>
            <div class="av-nombre">{abogado_full}</div>
            <div class="av-cargo">Firma Legal S.B.S. · San Miguel</div>
          </div>
        </div>
        <div class="contact-line"><span class="cl-label">WhatsApp</span><span class="cl-val"><a href="https://wa.me/50375783147">+503 7578-3147</a></span></div>
        <div class="contact-line"><span class="cl-label">Correo</span><span class="cl-val"><a href="mailto:sbsfirmalegal@gmail.com">sbsfirmalegal@gmail.com</a></span></div>
        <div class="contact-line"><span class="cl-label">Horario</span><span class="cl-val">Lunes a Viernes · 8 a.m. – 5 p.m.</span></div>
        <div class="contact-line"><span class="cl-label">Oficina</span><span class="cl-val">15 C. Oriente y 8ª Av. Sur, B° Concepción, San Miguel</span></div>
      </div>

      <div class="card">
        <div class="card-hdr">PRÓXIMAS FECHAS</div>
        {fecha_box}
      </div>

      <div class="card">
        <div class="card-hdr">ESTADO DE HONORARIOS</div>
        <div class="honor-line"><span class="hl-label">Total pactado</span><span class="hl-val total">{cur(pactado)}</span></div>
        <div class="honor-line"><span class="hl-label">Cancelado</span><span class="hl-val paid">{cur(cobrado)}</span></div>
        <div class="honor-line"><span class="hl-label">Pendiente</span><span class="hl-val pending">{cur(pendiente)}</span></div>
        <div class="honor-bar"><div class="honor-fill" style="width:{pct}%"></div></div>
        <div class="honor-pct">{pct}% cancelado</div>
      </div>

      <div class="card">
        <div class="card-hdr">DATOS DEL PROCESO</div>
        <div class="info-line"><span class="il-label">NIE</span><span class="il-val" style="font-family:'DM Mono',monospace;color:var(--gold);">{nie}</span></div>
        <div class="info-line"><span class="il-label">Tipo</span><span class="il-val">{tipo}</span></div>
        <div class="info-line"><span class="il-label">Materia</span><span class="il-val">{materia}</span></div>
        <div class="info-line"><span class="il-label">Apertura</span><span class="il-val" style="font-family:'DM Mono',monospace;">{fmt_date_short(apertura)}</span></div>
        <div class="info-line"><span class="il-label">Actualiz.</span><span class="il-val" style="font-family:'DM Mono',monospace;">{fmt_date_short(updated)}</span></div>
      </div>

    </div>
  </div>

</div>

<div class="portal-footer">
  <div class="footer-txt">
    Este portal es de uso exclusivo del cliente. La información es confidencial.<br>
    <a href="https://wa.me/50375783147?text=Hola,%20tengo%20una%20pregunta%20sobre%20mi%20proceso%20{nie}">¿Consultas? Escríbanos por WhatsApp</a>
    &nbsp;·&nbsp; Firma Legal S.B.S. · San Miguel, El Salvador · {datetime.now().year}
  </div>
</div>

<div class="gen-badge">ACTUALIZADO {fmt_date_short(datetime.now().strftime('%Y-%m-%d'))}</div>

</body>
</html>"""
    return html

# ── GENERATE INDEX ────────────────────────────────────────────────────────────
def generate_index(portales):
    items = ""
    for p in portales:
        items += f"""
    <div class="item">
      <span class="nie">{p['nie']}</span>
      <span class="nombre">{p['nombre']}</span>
      <span class="estado">{p['estado']}</span>
      <a href="{p['nie']}.html">Ver portal →</a>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Portales — Firma Legal S.B.S.</title>
<style>
body{{font-family:sans-serif;background:#0c1c38;color:#fff;padding:2rem;}}
h1{{color:#C9A84C;font-size:1.4rem;margin-bottom:1rem;}}
.item{{display:flex;gap:1.5rem;padding:.8rem 0;border-bottom:1px solid rgba(255,255,255,0.07);flex-wrap:wrap;align-items:center;}}
.nie{{font-family:monospace;color:#C9A84C;font-size:13px;min-width:150px;}}
.nombre{{flex:1;font-size:14px;}}
.estado{{font-size:12px;color:rgba(255,255,255,.5);min-width:140px;}}
a{{color:#C9A84C;}}
.ts{{font-size:11px;color:rgba(255,255,255,.3);margin-top:2rem;}}
</style>
</head>
<body>
<h1>⚖️ Firma Legal S.B.S. — Portales activos</h1>
{items}
<div class="ts">Última generación: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</div>
</body>
</html>"""

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("📋 Consultando Notion...")
    procesos = get_all_pages(PROCESOS_DB_ID, {
        "property": "Portal activo",
        "checkbox": {"equals": True}
    })
    print(f"   → {len(procesos)} proceso(s) con portal activo encontrado(s)")

    portales = []
    for proc in procesos:
        props = proc["properties"]
        nie = get_prop(props, "NIE")
        if not nie:
            continue

        # Get client name from relation
        client_ids = get_prop(props, "Cliente", [])
        client_name = get_client_name(client_ids[0]) if client_ids else "Cliente"

        # Get payment records
        pagos = get_honorarios(proc["id"])

        print(f"   → Generando portal: {nie} — {client_name}")
        html = generate_portal(proc, client_name, pagos)

        fname = f"{OUTPUT_DIR}/{nie}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html)

        estado = get_prop(props, "Estado", "—")
        portales.append({"nie": nie, "nombre": client_name, "estado": estado})

    # Generate index
    with open(f"{OUTPUT_DIR}/index.html", "w", encoding="utf-8") as f:
        f.write(generate_index(portales))

    print(f"\n✅ {len(portales)} portal(es) generado(s) en /{OUTPUT_DIR}/")
    for p in portales:
        print(f"   · {p['nie']}.html — {p['nombre']}")

if __name__ == "__main__":
    main()
