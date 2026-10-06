"""Testes automatizados de segurança e do fluxo de cotação. Rodar: python test_seguranca.py"""
import os, tempfile, json
os.environ.pop("DATABASE_URL", None)
import app as a

cliente = a.app.test_client()
ok_payload = {"nome": "Maria Silva", "email": "maria@exemplo.com.br", "whatsapp": "(62) 91234-5678",
              "interesse": ["auditoria", "faturamento"], "consentimento": True, "volume_guias": "Até 500 por mês"}
falhas = []

def checar(nome, cond, extra=""):
    print(("OK   " if cond else "FALHA"), nome, extra)
    if not cond: falhas.append(nome)

with a.app.app_context():
    a.db.drop_all(); a.db.create_all()

# --- páginas e cabeçalhos
r = cliente.get("/")
checar("GET / 200", r.status_code == 200)
h = r.headers
for k in ["Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy",
          "Permissions-Policy", "Cross-Origin-Opener-Policy", "Cross-Origin-Resource-Policy"]:
    checar(f"cabeçalho {k}", k in h)
html = r.get_data(as_text=True)
checar("sem style= inline no HTML", 'style="' not in html)
checar("sem <script> inline", "<script>" not in html and "<script " in html and "src=" in html)
checar("sem recursos de terceiros", "googleapis" not in html and "gstatic" not in html and "http://" not in html and "https://" not in html)
checar("GET /privacidade 200", cliente.get("/privacidade").status_code == 200)
r = cliente.get("/nao-existe"); checar("404 amigável sem detalhes", r.status_code == 404 and "Traceback" not in r.get_data(as_text=True))
r = cliente.get("/contato"); checar("GET /contato -> 405", r.status_code == 405)
r = cliente.get("/", base_url="https://site.exemplo", headers={"X-Forwarded-Proto": "https"})
checar("HSTS só em HTTPS", "Strict-Transport-Security" in r.headers)
checar("sem HSTS em HTTP", "Strict-Transport-Security" not in cliente.get("/").headers)

# --- formulário
post = lambda d, **kw: cliente.post("/contato", json=d, **kw)
r = post(ok_payload); checar("envio válido 200", r.status_code == 200 and r.get_json()["ok"])
checar("resposta de /contato sem cache", r.headers.get("Cache-Control") == "no-store")
with a.app.app_context():
    c = a.Cotacao.query.one()
    checar("gravou no banco", c.nome == "Maria Silva" and c.whatsapp == "62912345678")
    checar("IP não é guardado em claro", "127.0.0.1" not in (c.ip_hash or "") and len(c.ip_hash) == 64)
    checar("consentimento registrado", c.consentimento_em is not None and c.versao_politica)

r = post({**ok_payload, "consentimento": False}); checar("sem consentimento -> 400", r.status_code == 400 and "consentimento" in r.get_json()["erros"])
r = post({**ok_payload, "consentimento": "true"}); checar("consentimento como texto -> 400", r.status_code == 400)
r = post({"nome": ["x"], "email": {"a": 1}, "whatsapp": 123, "interesse": "x", "consentimento": True}); checar("tipos errados não causam 500", r.status_code == 400)
r = cliente.post("/contato", data="nome=x", content_type="application/x-www-form-urlencoded"); checar("form-urlencoded -> 415 (anti-CSRF)", r.status_code == 415)
r = post(ok_payload, headers={"Origin": "https://site-malicioso.com"}); checar("Origin de outro site -> 403", r.status_code == 403)
r = post(ok_payload, headers={"Origin": "http://localhost"}); checar("Origin do próprio site aceito", r.status_code == 200)
r = cliente.post("/contato", data="[1,2,3]", content_type="application/json"); checar("JSON não-objeto -> 400", r.status_code == 400)
r = cliente.post("/contato", data="{quebrado", content_type="application/json"); checar("JSON inválido -> 400", r.status_code == 400)
r = cliente.post("/contato", data=json.dumps({**ok_payload, "mensagem": "x" * 20000}), content_type="application/json"); checar("corpo grande -> 413", r.status_code == 413)
n = None
with a.app.app_context(): n = a.Cotacao.query.count()
r = post({"site": "spam", **ok_payload}); 
with a.app.app_context(): checar("honeypot não grava", a.Cotacao.query.count() == n and r.status_code == 200)
r = post({**ok_payload, "nome": "Zé <script>alert(1)</script>", "mensagem": "=HYPERLINK(\"x\")\x00\x07ok"})
with a.app.app_context():
    c = a.Cotacao.query.order_by(a.Cotacao.id.desc()).first()
    checar("caracteres de controle removidos", "\x00" not in c.mensagem and "\x07" not in c.mensagem)
    checar("SQL usa parâmetros (texto malicioso gravado como dado)", "<script>" in c.nome)
r = post({**ok_payload, "nome": "Robert'); DROP TABLE cotacoes;--"})
with a.app.app_context(): checar("SQL injection inofensivo", a.Cotacao.query.count() >= 1 and r.status_code == 200)

# --- limite de envios (já enviamos alguns; o 5º na mesma hora passa, o 6º não)
with a.app.app_context():
    a.Cotacao.query.delete(); a.db.session.commit()
codigos = [post(ok_payload).status_code for _ in range(7)]
checar("limite por hora (5 ok, depois 429)", codigos == [200]*5 + [429]*2, str(codigos))

# --- página injetada: autoescape
checar("autoescape ativo", a.app.jinja_env.autoescape is not False)

print("\nFALHAS:", falhas if falhas else "nenhuma")
raise SystemExit(1 if falhas else 0)
