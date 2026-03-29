"""
FIRMA LEGAL S.B.S. — Generador de Portales de Cliente
Usa la API de Notion directamente con requests. Sin notion-client.
"""

import os, requests
from datetime import datetime

NOTION_TOKEN     = os.environ["NOTION_TOKEN"]
PROCESOS_DB_ID   = os.environ.get("PROCESOS_DB_ID",   "cdaf65f1d417491aa54e9a82daa5b50d")
HONORARIOS_DB_ID = os.environ.get("HONORARIOS_DB_ID", "d53925ac-b7bb-4379-8e54-d3cf48dcca48")
OUTPUT_DIR       = "portals"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
os.makedirs(OUTPUT_DIR, exist_ok=True)

def notion_query(db_id, filter_obj=None):
    pages, cursor = [], None
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    while True:
        body = {"page_size": 100}
        if filter_obj: body["filter"] = filter_obj
        if cursor: body["start_cursor"] = cursor
        r = requests.post(url, headers=HEADERS, json=body)
        r.raise_for_status()
        data = r.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"): break
        cursor = data.get("next_cursor")
    return pages

def notion_get_page(page_id):
    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}", headers=HEADERS)
    r.raise_for_status()
    return r.json()

def gp(props, name, fallback=""):
    p = props.get(name)
    if not p: return fallback
    t = p.get("type", "")
    if t == "title":     return "".join(r["plain_text"] for r in p.get("title", []))
    if t == "rich_text": return "".join(r["plain_text"] for r in p.get("rich_text", []))
    if t == "select":    s = p.get("select"); return s["name"] if s else fallback
    if t == "checkbox":  return p.get("checkbox", False)
    if t == "number":    return p.get("number") or 0
    if t == "date":      d = p.get("date"); return d["start"] if d else fallback
    if t == "relation":  return [r["id"] for r in p.get("relation", [])]
    if t == "rollup":
        ro = p.get("rollup", {}); rt = ro.get("type", "")
        if rt == "number": return ro.get("number") or 0
        if rt == "array":  return sum(i.get("number",0) for i in ro.get("array",[]) if i.get("type")=="number")
    if t == "formula":
        f = p.get("formula", {}); ft = f.get("type", "")
        if ft == "number": return f.get("number") or 0
        if ft == "string": return f.get("string") or fallback
    return fallback

def fdate(s):
    if not s or s=="—": return "—"
    try:
        d=datetime.strptime(s[:10],"%Y-%m-%d")
        m=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
        return f"{d.day} de {m[d.month-1]} de {d.year}"
    except: return s

def fshort(s):
    if not s: return "—"
    try: d=datetime.strptime(s[:10],"%Y-%m-%d"); return f"{d.day:02d}/{d.month:02d}/{d.year}"
    except: return s

def fday(s):
    try: return str(datetime.strptime(s[:10],"%Y-%m-%d").day)
    except: return "—"

def fmon(s):
    m=["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"]
    try: return m[datetime.strptime(s[:10],"%Y-%m-%d").month-1]
    except: return ""

def cur(v):
    try: return f"${float(v):,.2f}"
    except: return "$0.00"

def pct(c,p):
    try: return min(100,round(float(c)/float(p)*100)) if float(p)>0 else 0
    except: return 0

def ecls(e):
    return {"En trámite":"pill-tramite","En espera de resolución":"pill-espera","Urgente":"pill-urgente","Listo para entrega":"pill-listo","Cerrado — Favorable":"pill-cerrado","Cerrado — Desfavorable":"pill-cerrado"}.get(e,"pill-tramite")

ABG={"Nelson A. Castillo B.":"Nelson Alexander Castillo Barrera","Fátima A. Serrano D.":"Fátima Alejandra Serrano Díaz","Estela S. Sandoval S.":"Estela Saraí Sandoval Sandoval","Conjunto":"Equipo S.B.S."}

CSS="""
:root{--deep:#0c1c38;--gold:#C9A84C;--gb:rgba(201,168,76,.08);--gbd:rgba(201,168,76,.22);--bd:rgba(255,255,255,.07);}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--deep);color:#fff;min-height:100vh;}
.ph{background:rgba(0,0,0,.42);border-bottom:1px solid var(--bd);height:58px;display:flex;align-items:center;justify-content:space-between;padding:0 2rem;position:sticky;top:0;z-index:100;backdrop-filter:blur(10px);}
.ph-l{display:flex;align-items:center;gap:16px;}
.logo{font-family:'Playfair Display',serif;font-size:14px;color:var(--gold);letter-spacing:2px;}
.sep{width:1px;height:22px;background:rgba(255,255,255,.12);}
.tag{font-size:10px;letter-spacing:3px;color:rgba(255,255,255,.28);}
.ph-r{display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.nie-badge{font-family:'DM Mono',monospace;font-size:11px;color:var(--gold);background:var(--gb);border:1px solid var(--gbd);padding:3px 11px;letter-spacing:1px;}
.who{font-size:12px;color:rgba(255,255,255,.45);}
.who strong{color:rgba(255,255,255,.82);}
.sec{font-size:9px;letter-spacing:2px;color:rgba(100,210,160,.75);background:rgba(100,210,160,.07);border:1px solid rgba(100,210,160,.2);padding:3px 10px;}
.wrap{max-width:1100px;margin:0 auto;padding:2rem 1.5rem;}
.hero{background:rgba(255,255,255,.03);border:1px solid var(--bd);padding:2rem;margin-bottom:1.5rem;display:grid;grid-template-columns:1fr auto;align-items:center;gap:2rem;}
.eye{font-size:9px;letter-spacing:3px;color:rgba(255,255,255,.22);margin-bottom:.5rem;display:block;}
.tit{font-family:'Playfair Display',serif;font-size:22px;color:#fff;line-height:1.3;margin-bottom:.8rem;}
.meta{display:flex;gap:1.2rem;flex-wrap:wrap;}
.mi{font-size:12px;color:rgba(255,255,255,.35);}
.mi span{color:rgba(255,255,255,.68);}
.pill{display:inline-flex;align-items:center;gap:8px;padding:9px 22px;font-size:11px;letter-spacing:2px;font-weight:600;white-space:nowrap;}
.pill .dot{width:8px;height:8px;border-radius:50%;background:currentColor;flex-shrink:0;}
.pill-tramite{background:rgba(74,111,165,.15);border:1px solid rgba(74,111,165,.3);color:#7aacf0;}
.pill-urgente{background:rgba(180,60,60,.15);border:1px solid rgba(180,60,60,.3);color:#e07878;}
.pill-espera{background:rgba(176,124,42,.12);border:1px solid rgba(176,124,42,.3);color:#d4a460;}
.pill-listo{background:rgba(45,122,95,.1);border:1px solid rgba(45,122,95,.3);color:#6ec898;}
.pill-cerrado{background:rgba(156,163,175,.1);border:1px solid rgba(156,163,175,.2);color:#9ca3af;}
.cols{display:grid;grid-template-columns:1fr 310px;gap:1.5rem;margin-bottom:1.5rem;}
.col{display:flex;flex-direction:column;gap:1.5rem;}
.card{background:rgba(255,255,255,.03);border:1px solid var(--bd);padding:1.5rem;}
.ch{font-size:9px;letter-spacing:3px;color:rgba(255,255,255,.22);margin-bottom:1rem;display:flex;align-items:center;gap:8px;}
.ch::after{content:'';flex:1;height:1px;background:rgba(255,255,255,.06);}
.nov{padding:.9rem 0;border-bottom:1px solid rgba(255,255,255,.05);}
.nov:last-child{border-bottom:none;}
.nm{display:flex;align-items:center;gap:9px;margin-bottom:.45rem;flex-wrap:wrap;}
.nq{font-size:11px;color:var(--gold);font-weight:500;}
.nf{font-size:10px;color:rgba(255,255,255,.2);font-family:'DM Mono',monospace;}
.nt{font-size:9px;letter-spacing:1.5px;padding:2px 8px;margin-left:auto;background:rgba(74,111,165,.1);border:1px solid rgba(74,111,165,.25);color:#7aacf0;}
.ntx{font-size:13px;color:rgba(255,255,255,.6);line-height:1.65;}
.pr{display:grid;grid-template-columns:85px 100px 1fr 90px 85px;align-items:center;padding:.6rem 0;border-bottom:1px solid rgba(255,255,255,.04);gap:8px;font-size:12px;}
.pr:last-child{border-bottom:none;}
.prf{font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.3);}
.prg{font-size:9px;letter-spacing:1px;padding:2px 7px;background:var(--gb);border:1px solid var(--gbd);color:var(--gold);}
.prc{color:rgba(255,255,255,.65);}
.prfm{font-size:11px;color:rgba(255,255,255,.3);}
.prm{font-family:'DM Mono',monospace;color:#6ec898;text-align:right;}
.avr{display:flex;align-items:center;gap:12px;margin-bottom:1.2rem;}
.av{width:46px;height:46px;border-radius:50%;background:rgba(74,111,165,.18);border:2px solid rgba(74,111,165,.35);display:flex;align-items:center;justify-content:center;font-size:17px;font-weight:600;color:#6fa0e0;flex-shrink:0;}
.avn{font-size:13.5px;color:rgba(255,255,255,.85);font-weight:500;}
.avc{font-size:10px;color:rgba(255,255,255,.28);margin-top:2px;}
.cl{display:flex;align-items:center;gap:9px;padding:.55rem 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:12px;}
.cl:last-child{border-bottom:none;}
.cll{color:rgba(255,255,255,.22);font-size:10px;letter-spacing:.5px;min-width:55px;}
.clv{color:rgba(255,255,255,.62);}
.clv a{color:var(--gold);text-decoration:none;}
.fr{display:flex;gap:12px;padding:.75rem 0;}
.fb{width:44px;height:44px;background:var(--gb);border:1px solid var(--gbd);display:flex;flex-direction:column;align-items:center;justify-content:center;flex-shrink:0;}
.fd{font-family:'Playfair Display',serif;font-size:18px;color:var(--gold);line-height:1;}
.fm{font-size:8px;letter-spacing:1.5px;color:rgba(201,168,76,.55);}
.ft{font-size:11.5px;color:rgba(255,255,255,.72);font-weight:500;}
.fdesc{font-size:10.5px;color:rgba(255,255,255,.32);margin-top:2px;}
.hl{display:flex;justify-content:space-between;align-items:center;padding:.55rem 0;border-bottom:1px solid rgba(255,255,255,.05);}
.hl:last-child{border-bottom:none;}
.hll{color:rgba(255,255,255,.32);font-size:11px;}
.hlv{font-family:'DM Mono',monospace;font-size:12px;}
.paid{color:#6ec898;}.pend{color:#e0b060;}.tot{color:rgba(255,255,255,.68);}
.hbar{height:3px;background:rgba(255,255,255,.06);margin:.8rem 0 4px;border-radius:2px;overflow:hidden;}
.hfill{height:100%;background:var(--gold);border-radius:2px;}
.hpct{font-size:10px;color:rgba(255,255,255,.2);text-align:center;margin-bottom:.8rem;}
.il{display:flex;justify-content:space-between;align-items:flex-start;padding:.55rem 0;border-bottom:1px solid rgba(255,255,255,.05);gap:8px;}
.il:last-child{border-bottom:none;}
.ill{color:rgba(255,255,255,.28);font-size:10.5px;letter-spacing:.5px;flex-shrink:0;}
.ilv{font-size:12px;color:rgba(255,255,255,.62);text-align:right;line-height:1.4;}
.empty{color:rgba(255,255,255,.28);font-size:12px;padding:.4rem 0;}
footer{border-top:1px solid rgba(255,255,255,.06);padding:1.5rem 2rem;text-align:center;}
footer p{font-size:11px;color:rgba(255,255,255,.18);letter-spacing:.5px;line-height:1.8;}
footer a{color:var(--gold);text-decoration:none;}
.gen{position:fixed;bottom:10px;right:12px;font-size:9px;letter-spacing:1.5px;color:rgba(255,255,255,.1);background:rgba(0,0,0,.3);padding:3px 9px;border:1px solid rgba(255,255,255,.06);}
@media(max-width:780px){.cols{grid-template-columns:1fr;}.ph{padding:0 1rem;}.nie-badge,.sec{display:none;}.wrap{padding:1rem;}.hero{grid-template-columns:1fr;gap:1rem;}.pr{grid-template-columns:1fr 1fr;}}
"""

def build_portal(proc, client_name, pagos):
    props    = proc["properties"]
    nie      = gp(props,"NIE")
    asunto   = gp(props,"Asunto específico")
    tipo     = gp(props,"Tipo de proceso")
    materia  = gp(props,"Materia")
    estado   = gp(props,"Estado","En trámite")
    abg_raw  = gp(props,"Abogado asignado","")
    apertura = gp(props,"Fecha de apertura")
    aud      = gp(props,"Fecha de próxima audiencia")
    nota     = gp(props,"Nota para el cliente") or ""
    pactado  = float(gp(props,"Honorario pactado ($)",0) or 0)
    cobrado_r= float(gp(props,"Total cobrado ($)",0) or 0)
    cobrado  = cobrado_r if cobrado_r>0 else sum(float(p["monto"] or 0) for p in pagos)
    pendiente= max(0,pactado-cobrado)
    bar      = pct(cobrado,pactado)
    updated  = (proc.get("last_edited_time") or "")[:10]
    abg_full = ABG.get(abg_raw, abg_raw)
    abg_ini  = "T" if "Conjunto" in abg_raw else (abg_raw[0] if abg_raw else "N")

    pagos_html = ""
    for p in pagos:
        pagos_html += f'<div class="pr"><span class="prf">{fshort(p["fecha"])}</span><span class="prg">{p["tipo"]}</span><span class="prc">{p["concepto"]}</span><span class="prfm">{p["forma"]}</span><span class="prm">{cur(p["monto"])}</span></div>'
    if not pagos_html:
        pagos_html = '<p class="empty">Sin movimientos registrados aún.</p>'

    if aud and aud != "—":
        fecha_blk = f'<div class="fr"><div class="fb"><div class="fd">{fday(aud)}</div><div class="fm">{fmon(aud)}</div></div><div><div class="ft">Próxima diligencia</div><div class="fdesc">{fdate(aud)}</div></div></div>'
    else:
        fecha_blk = '<p class="empty">Sin fechas programadas por el momento.</p>'

    if nota.strip():
        nota_blk = f'<div class="nov"><div class="nm"><span class="nq">{abg_full}</span><span class="nf">{fshort(updated)}</span><span class="nt">NOVEDAD</span></div><div class="ntx">{nota}</div></div>'
    else:
        nota_blk = '<p class="empty">Sin novedades publicadas aún. Le comunicaremos cuando haya avances relevantes.</p>'

    yr = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Mi Proceso — Firma Legal S.B.S.</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="ph">
  <div class="ph-l"><span class="logo">FIRMA LEGAL S.B.S.</span><div class="sep"></div><span class="tag">PORTAL DE SEGUIMIENTO</span></div>
  <div class="ph-r"><span class="nie-badge">{nie}</span><span class="who">Bienvenido/a, <strong>{client_name.split()[0]}</strong></span><span class="sec">🔒 ACCESO SEGURO</span></div>
</div>
<div class="wrap">
  <div class="hero">
    <div>
      <span class="eye">EXPEDIENTE {nie} · PROCESO {tipo.upper()}</span>
      <div class="tit">{asunto}</div>
      <div class="meta">
        <div class="mi">Materia: <span>{materia}</span></div>
        <div class="mi">Apertura: <span>{fdate(apertura)}</span></div>
        <div class="mi">Abogado/a: <span>{abg_full}</span></div>
      </div>
    </div>
    <div class="pill {ecls(estado)}"><div class="dot"></div>{estado.upper()}</div>
  </div>
  <div class="cols">
    <div class="col">
      <div class="card"><div class="ch">NOVEDADES DEL PROCESO</div>{nota_blk}</div>
      <div class="card"><div class="ch">HISTORIAL DE PAGOS</div>{pagos_html}</div>
    </div>
    <div class="col">
      <div class="card">
        <div class="ch">SU ABOGADO/A ASIGNADO/A</div>
        <div class="avr"><div class="av">{abg_ini}</div><div><div class="avn">{abg_full}</div><div class="avc">Firma Legal S.B.S. · San Miguel</div></div></div>
        <div class="cl"><span class="cll">WhatsApp</span><span class="clv"><a href="https://wa.me/50375783147">+503 7578-3147</a></span></div>
        <div class="cl"><span class="cll">Correo</span><span class="clv"><a href="mailto:sbsfirmalegal@gmail.com">sbsfirmalegal@gmail.com</a></span></div>
        <div class="cl"><span class="cll">Horario</span><span class="clv">Lunes a Viernes · 8 a.m. – 5 p.m.</span></div>
        <div class="cl"><span class="cll">Oficina</span><span class="clv">15 C. Oriente y 8ª Av. Sur, B° Concepción, San Miguel</span></div>
      </div>
      <div class="card"><div class="ch">PRÓXIMAS FECHAS</div>{fecha_blk}</div>
      <div class="card">
        <div class="ch">ESTADO DE HONORARIOS</div>
        <div class="hl"><span class="hll">Total pactado</span><span class="hlv tot">{cur(pactado)}</span></div>
        <div class="hl"><span class="hll">Cancelado</span><span class="hlv paid">{cur(cobrado)}</span></div>
        <div class="hl"><span class="hll">Pendiente</span><span class="hlv pend">{cur(pendiente)}</span></div>
        <div class="hbar"><div class="hfill" style="width:{bar}%"></div></div>
        <div class="hpct">{bar}% cancelado</div>
      </div>
      <div class="card">
        <div class="ch">DATOS DEL PROCESO</div>
        <div class="il"><span class="ill">NIE</span><span class="ilv" style="font-family:'DM Mono',monospace;color:var(--gold);">{nie}</span></div>
        <div class="il"><span class="ill">Tipo</span><span class="ilv">{tipo}</span></div>
        <div class="il"><span class="ill">Materia</span><span class="ilv">{materia}</span></div>
        <div class="il"><span class="ill">Apertura</span><span class="ilv" style="font-family:'DM Mono',monospace;">{fshort(apertura)}</span></div>
        <div class="il"><span class="ill">Actualiz.</span><span class="ilv" style="font-family:'DM Mono',monospace;">{fshort(updated)}</span></div>
      </div>
    </div>
  </div>
</div>
<footer><p>Portal de uso exclusivo del cliente · Información confidencial<br>
<a href="https://wa.me/50375783147?text=Consulta%20proceso%20{nie}">¿Consultas? WhatsApp</a> · Firma Legal S.B.S. · San Miguel · {yr}</p></footer>
<div class="gen">ACTUALIZADO {fshort(datetime.now().strftime('%Y-%m-%d'))}</div>
</body></html>"""

def build_index(portales):
    items = "".join(f'<div class="item"><span class="nie">{p["nie"]}</span><span class="nombre">{p["nombre"]}</span><span class="estado">{p["estado"]}</span></div>' for p in portales)
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Portales SBS</title>
<style>body{{font-family:sans-serif;background:#0c1c38;color:#fff;padding:2rem;}}h1{{color:#C9A84C;margin-bottom:1rem;}}.item{{display:flex;gap:1.5rem;padding:.7rem 0;border-bottom:1px solid rgba(255,255,255,.07);flex-wrap:wrap;}}.nie{{font-family:monospace;color:#C9A84C;min-width:160px;}}.nombre{{flex:1;}}.estado{{color:rgba(255,255,255,.5);min-width:140px;}}.ts{{font-size:11px;color:rgba(255,255,255,.3);margin-top:2rem;}}</style>
</head><body><h1>⚖️ Firma Legal S.B.S. — Portales activos</h1>{items}<div class="ts">Última generación: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</div></body></html>"""

def main():
    print("📋 Consultando Notion...")
    procesos = notion_query(PROCESOS_DB_ID, {"property":"Portal activo","checkbox":{"equals":True}})
    print(f"   → {len(procesos)} proceso(s) con portal activo")

    portales = []
    for proc in procesos:
        props = proc["properties"]
        nie = gp(props, "NIE")
        if not nie: continue

        client_ids = gp(props, "Cliente", [])
        client_name = "Cliente"
        if client_ids:
            try:
                cp = notion_get_page(client_ids[0])
                client_name = gp(cp["properties"], "Nombre completo", "Cliente")
            except Exception as e:
                print(f"   ⚠️  {nie}: {e}")

        pagos_raw = notion_query(HONORARIOS_DB_ID, {"property":"Proceso (NIE)","relation":{"contains":proc["id"]}})
        pagos = sorted([{"concepto":gp(p["properties"],"Concepto"),"tipo":gp(p["properties"],"Tipo de movimiento"),"monto":gp(p["properties"],"Monto recibido ($)",0),"forma":gp(p["properties"],"Forma de pago"),"fecha":gp(p["properties"],"Fecha de pago")} for p in pagos_raw], key=lambda x: x["fecha"] or "")

        print(f"   → {nie} — {client_name} ({len(pagos)} pago(s))")
        html = build_portal(proc, client_name, pagos)
        with open(f"{OUTPUT_DIR}/{nie}.html","w",encoding="utf-8") as f: f.write(html)
        portales.append({"nie":nie,"nombre":client_name,"estado":gp(props,"Estado","—")})

    with open(f"{OUTPUT_DIR}/index.html","w",encoding="utf-8") as f: f.write(build_index(portales))
    print(f"\n✅ {len(portales)} portal(es) en /{OUTPUT_DIR}/")
    for p in portales: print(f"   · {p['nie']}.html — {p['nombre']}")

if __name__ == "__main__":
    main()
