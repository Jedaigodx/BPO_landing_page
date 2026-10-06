"""Landing page: BPO de faturamento e auditoria de guias médicas.

Local:     python app.py            (usa SQLite em instance/dev.db)
Railway:   gunicorn app:app         (usa DATABASE_URL do PostgreSQL)
"""
import hashlib
import hmac
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = Path(__file__).resolve().parent

EM_PRODUCAO = bool(os.environ.get("RAILWAY_PROJECT_ID")) or os.environ.get("APP_ENV") == "production"
VERSAO_POLITICA = "2026-09"

# ---------------------------------------------------------------------------
# Aplicação e configuração
# ---------------------------------------------------------------------------
app = Flask(__name__)


def _url_banco():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///" + (BASE_DIR / "instance" / "dev.db").as_posix()
    # Railway entrega postgresql:// (ou postgres://); o driver instalado é o psycopg 3
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url[len(prefixo):]
    return url


SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if EM_PRODUCAO:
        raise RuntimeError("Defina a variável SECRET_KEY no ambiente de produção.")
    SECRET_KEY = "somente-desenvolvimento-local"  # nosec B105

app.config.update(
    SECRET_KEY=SECRET_KEY,
    SQLALCHEMY_DATABASE_URI=_url_banco(),
    SQLALCHEMY_ENGINE_OPTIONS={
        "pool_pre_ping": True,
        "pool_recycle": 300,
        # Evita que valores do formulário (dados pessoais) apareçam em mensagens de erro e logs
        "hide_parameters": True,
    },
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=16 * 1024,  # 16 KB: o formulário nunca precisa de mais
)

# Atrás do proxy do Railway, o IP real vem em X-Forwarded-For (último salto confiável).
if os.environ.get("TRUST_PROXY") == "1" or (EM_PRODUCAO and os.environ.get("TRUST_PROXY") != "0"):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

logging.basicConfig(level=logging.INFO)
db = SQLAlchemy(app)

# ---------------------------------------------------------------------------
# Dados da empresa (deixe vazio enquanto não estiverem definidos)
# ---------------------------------------------------------------------------
EMPRESA = {
    "nome": "",
    "cnpj": "",
    "cidade": "Goiânia, GO",
    "telefone": "",
    "email": "",
    "endereco": "",
}

# ---------------------------------------------------------------------------
# Conteúdo
# ---------------------------------------------------------------------------
AREAS = [
    {"id": "auditoria", "icone": "auditoria", "titulo": "Auditoria de contas médicas",
     "texto": "Conferência de guias, prontuários e contratos para encontrar o erro antes do convênio."},
    {"id": "pre-faturamento", "icone": "escudo", "titulo": "Pré-faturamento",
     "texto": "Checagem de cadastro, autorização e códigos antes do envio."},
    {"id": "faturamento", "icone": "fatura", "titulo": "Faturamento",
     "texto": "Montagem e envio dos lotes, acompanhamento de protocolos e recurso de glosa."},
    {"id": "repasse", "icone": "repasse", "titulo": "Repasse médico",
     "texto": "Cálculo do repasse por profissional, com demonstrativo para conferência."},
]

PASSOS = [
    {"titulo": "Conversa e diagnóstico",
     "texto": "Você pede a cotação e nós visitamos a operação para entender convênios, fluxo de guias e onde a receita escapa."},
    {"titulo": "Escopo combinado",
     "texto": "Definimos juntos quais etapas do ciclo fazem sentido agora. Nada de pacote fechado."},
    {"titulo": "Rotina mensal",
     "texto": "Conferimos, faturamos e acompanhamos os retornos, em contato direto com recepção e financeiro."},
    {"titulo": "Leitura dos números",
     "texto": "Entregamos o relatório e sentamos com você para decidir o que ajustar no mês seguinte."},
]

DIFERENCIAIS = [
    {"icone": "local", "titulo": "Presença em Goiânia",
     "texto": "Acompanhamos a operação de perto, sem depender só de e-mail e planilha."},
    {"icone": "grafico", "titulo": "Decisão com dados",
     "texto": "Cruzamos faturamento, glosa e recebimento para mostrar onde agir primeiro."},
    {"icone": "ajuste", "titulo": "Escopo sob medida",
     "texto": "A contratação acompanha o que a operação precisa hoje e cresce depois."},
    {"icone": "cadeado", "titulo": "Sigilo e LGPD",
     "texto": "Dados tratados com confidencialidade e acesso restrito à equipe responsável."},
]

FAQ = [
    {"p": "Como funciona a cotação?",
     "r": "Você preenche o formulário, conversamos para entender a sua operação e enviamos uma proposta com o escopo combinado. Não há compromisso."},
    {"p": "Preciso contratar o ciclo completo?",
     "r": "Não. Você pode contratar só a auditoria, só o faturamento ou qualquer combinação entre as etapas. O escopo é definido junto com você."},
    {"p": "O atendimento é presencial?",
     "r": "Sim, em Goiânia. A equipe visita a sua operação no diagnóstico e nos acompanhamentos combinados."},
    {"p": "Com quais convênios vocês trabalham?",
     "r": "Com os convênios e tabelas que a sua operação já utiliza. Na primeira conversa mapeamos quais são e o que cada um exige."},
    {"p": "Para qual porte de operação vocês trabalham?",
     "r": "A rotina é adaptada ao volume de guias e ao número de convênios de cada operação."},
    {"p": "Que métricas eu recebo?",
     "r": "Um relatório periódico com faturamento, glosas, recebimentos e repasse, e uma conversa para decidir o que ajustar. Os indicadores são definidos com você."},
    {"p": "Como os dados são protegidos?",
     "r": "Com acesso restrito à equipe responsável e tratamento conforme a LGPD. Pedimos que o formulário de cotação não contenha dados de pacientes."},
]

VOLUMES_GUIAS = ["Até 500 por mês", "De 500 a 2.000 por mês", "De 2.000 a 10.000 por mês",
                 "Mais de 10.000 por mês", "Não sei informar"]

LOTE_DEMO = [
    {"guia": "0001284", "convenio": "Convênio A", "procedimento": "Consulta eletiva",
     "valor": 180.00, "resultado": "ok"},
    {"guia": "0001285", "convenio": "Convênio B", "procedimento": "Ultrassonografia de abdome total",
     "valor": 260.00, "resultado": "erro",
     "motivo": "Código do procedimento diverge da tabela do convênio"},
    {"guia": "0001286", "convenio": "Convênio A", "procedimento": "Eletrocardiograma",
     "valor": 95.00, "resultado": "ok"},
    {"guia": "0001287", "convenio": "Convênio C", "procedimento": "Painel de exames laboratoriais",
     "valor": 410.00, "resultado": "erro", "motivo": "Falta autorização prévia"},
    {"guia": "0001288", "convenio": "Convênio B", "procedimento": "Consulta de retorno",
     "valor": 150.00, "resultado": "ok"},
    {"guia": "0001289", "convenio": "Convênio C", "procedimento": "Sessão de fisioterapia",
     "valor": 120.00, "resultado": "erro", "motivo": "Carteirinha com validade vencida"},
]

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
FATURADO_MIL = [212, 228, 219, 241, 255, 249, 263, 271, 268, 284, 292, 301]
RECEBIDO_MIL = [188, 205, 201, 219, 236, 233, 248, 259, 257, 273, 281, 290]

GLOSA_POR_CONVENIO = [
    {"nome": "Convênio A", "pct": 3.1}, {"nome": "Convênio B", "pct": 5.8},
    {"nome": "Convênio C", "pct": 7.4}, {"nome": "Convênio D", "pct": 2.2},
]

REPASSE_DEMO = [
    {"grupo": "Clínica geral", "guias": 512, "faturado": 98500, "taxa": 0.68},
    {"grupo": "Cardiologia", "guias": 344, "faturado": 81200, "taxa": 0.70},
    {"grupo": "Ortopedia", "guias": 290, "faturado": 67300, "taxa": 0.65},
    {"grupo": "Exames de imagem", "guias": 431, "faturado": 54000, "taxa": 0.72},
]


def montar_grafico_linhas(meses, series, largura=640, altura=240, margem_esq=44,
                          margem_dir=16, margem_sup=16, margem_inf=30, passo=50):
    """Converte séries numéricas em coordenadas de um gráfico de linhas SVG."""
    todos = [v for s in series for v in s["valores"]]
    vmin = (min(todos) // passo) * passo
    vmax = -(-max(todos) // passo) * passo
    area_w = largura - margem_esq - margem_dir
    area_h = altura - margem_sup - margem_inf

    def x(i):
        return margem_esq + area_w * i / (len(meses) - 1)

    def y(v):
        return margem_sup + area_h * (1 - (v - vmin) / (vmax - vmin))

    linhas = []
    for s in series:
        pts = [(round(x(i), 1), round(y(v), 1)) for i, v in enumerate(s["valores"])]
        linhas.append({"nome": s["nome"], "classe": s["classe"],
                       "pontos": " ".join(f"{a},{b}" for a, b in pts), "fim": pts[-1]})
    return {
        "largura": largura, "altura": altura, "margem_esq": margem_esq,
        "margem_dir": margem_dir, "base": altura - margem_inf, "linhas": linhas,
        "grade": [{"y": round(y(v), 1), "rotulo": v} for v in range(int(vmin), int(vmax) + 1, passo)],
        "rotulos_x": [{"x": round(x(i), 1), "texto": m} for i, m in enumerate(meses)],
    }


# ---------------------------------------------------------------------------
# Filtros de formatação (padrão brasileiro)
# ---------------------------------------------------------------------------
@app.template_filter("brl")
def filtro_brl(valor):
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


@app.template_filter("decimal")
def filtro_decimal(valor, casas=1):
    return f"{valor:.{casas}f}".replace(".", ",")


@app.template_filter("milhar")
def filtro_milhar(valor):
    return f"{valor:,.0f}".replace(",", ".")


@app.context_processor
def contexto_global():
    return {"empresa": EMPRESA, "nome_empresa": EMPRESA["nome"] or "Nome da empresa",
            "ano": datetime.now().year}


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
class Cotacao(db.Model):
    __tablename__ = "cotacoes"

    id = db.Column(db.Integer, primary_key=True)
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc), index=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    whatsapp = db.Column(db.String(11), nullable=False)
    instituicao = db.Column(db.String(160))
    volume_guias = db.Column(db.String(40))
    convenios = db.Column(db.String(200))
    interesse = db.Column(db.String(200))
    mensagem = db.Column(db.Text)
    consentimento_em = db.Column(db.DateTime(timezone=True), nullable=False)
    versao_politica = db.Column(db.String(10), nullable=False)
    # Hash do IP (HMAC), usado só para limitar abuso; o IP em si não é guardado.
    ip_hash = db.Column(db.String(64), index=True)
    status = db.Column(db.String(20), nullable=False, default="novo")


def iniciar_banco():
    try:
        with app.app_context():
            db.create_all()
    except SQLAlchemyError:
        # Outro worker pode ter criado a tabela ao mesmo tempo, ou o banco ainda está subindo.
        app.logger.warning("Não foi possível preparar as tabelas agora.", exc_info=False)


iniciar_banco()

# ---------------------------------------------------------------------------
# Cabeçalhos de segurança
# ---------------------------------------------------------------------------
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "base-uri 'none'",
    "object-src 'none'",
])


@app.after_request
def cabecalhos_seguranca(resp):
    h = resp.headers
    h["Content-Security-Policy"] = CSP + ("; upgrade-insecure-requests" if request.is_secure else "")
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "strict-origin-when-cross-origin"
    h["Permissions-Policy"] = ("accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
                               "microphone=(), payment=(), usb=(), interest-cohort=()")
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    h["Cross-Origin-Resource-Policy"] = "same-origin"
    if request.is_secure:
        h["Strict-Transport-Security"] = "max-age=31536000"
    if request.path == "/contato":
        h["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    grafico = montar_grafico_linhas(MESES, [
        {"nome": "Faturado", "classe": "faturado", "valores": FATURADO_MIL},
        {"nome": "Recebido", "classe": "recebido", "valores": RECEBIDO_MIL},
    ])
    glosa_media = sum(c["pct"] for c in GLOSA_POR_CONVENIO) / len(GLOSA_POR_CONVENIO)
    kpis = [
        {"rotulo": "Faturado no mês", "valor": f"R$ {FATURADO_MIL[-1]} mil"},
        {"rotulo": "Recebido no mês", "valor": f"R$ {RECEBIDO_MIL[-1]} mil"},
        {"rotulo": "Glosa média", "valor": f"{filtro_decimal(glosa_media)}%"},
        {"rotulo": "Prazo médio de recebimento", "valor": "38 dias"},
    ]
    repasse = [{**r, "repasse": round(r["faturado"] * r["taxa"])} for r in REPASSE_DEMO]
    return render_template(
        "index.html", areas=AREAS, passos=PASSOS, diferenciais=DIFERENCIAIS, faq=FAQ,
        volumes=VOLUMES_GUIAS, lote=LOTE_DEMO, grafico=grafico, kpis=kpis,
        glosa=GLOSA_POR_CONVENIO, glosa_max=max(c["pct"] for c in GLOSA_POR_CONVENIO),
        repasse=repasse,
    )


@app.get("/privacidade")
def privacidade():
    return render_template("privacidade.html", versao=VERSAO_POLITICA)


# ---------------------------------------------------------------------------
# Formulário de cotação
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CONTROLE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
IDS_INTERESSE = {a["id"] for a in AREAS} | {"indefinido"}
LIMITE_POR_HORA = 5


def _texto(valor, limite, multilinha=False):
    """Aceita só texto; remove caracteres de controle e corta no limite."""
    if not isinstance(valor, str):
        return ""
    valor = CONTROLE_RE.sub("", valor)
    if not multilinha:
        valor = valor.replace("\n", " ").replace("\r", " ")
    return valor.strip()[:limite]


def validar_cotacao(dados):
    erros = {}
    nome = _texto(dados.get("nome"), 120)
    if len(nome) < 3:
        erros["nome"] = "Informe seu nome."

    email = _texto(dados.get("email"), 160)
    if not EMAIL_RE.match(email):
        erros["email"] = "Informe um e-mail válido, como nome@empresa.com.br."

    whatsapp = re.sub(r"\D", "", _texto(dados.get("whatsapp"), 30))
    if len(whatsapp) not in (10, 11):
        erros["whatsapp"] = "Informe o WhatsApp com DDD, por exemplo (62) 91234-5678."

    volume = _texto(dados.get("volume_guias"), 40)
    if volume and volume not in VOLUMES_GUIAS:
        volume = ""

    interesse = dados.get("interesse")
    if not isinstance(interesse, list):
        interesse = []
    interesse = sorted({i for i in interesse if isinstance(i, str) and i in IDS_INTERESSE})

    if dados.get("consentimento") is not True:
        erros["consentimento"] = "Para enviar, confirme que está de acordo com a política de privacidade."

    lead = {
        "nome": nome, "email": email, "whatsapp": whatsapp,
        "instituicao": _texto(dados.get("instituicao"), 160),
        "volume_guias": volume,
        "convenios": _texto(dados.get("convenios"), 200),
        "interesse": ", ".join(interesse),
        "mensagem": _texto(dados.get("mensagem"), 1000, multilinha=True),
    }
    return lead, erros


def _hash_ip():
    ip = request.remote_addr or "desconhecido"
    return hmac.new(SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()


def _origem_permitida():
    """Bloqueia envios vindos de outros sites (defesa contra CSRF, além do JSON obrigatório)."""
    origem = request.headers.get("Origin")
    if not origem:
        return True
    return urlparse(origem).netloc == request.host


def _erro_json(mensagem, status):
    return jsonify(ok=False, erro=mensagem), status


@app.post("/contato")
def contato():
    if not _origem_permitida():
        return _erro_json("Origem não permitida.", 403)
    if not request.is_json:
        return _erro_json("Formato não suportado.", 415)

    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return _erro_json("Requisição inválida.", 400)

    # Campo isca: pessoas não veem; robôs costumam preencher. Respondemos "ok" sem gravar.
    if dados.get("site"):
        return jsonify(ok=True)

    lead, erros = validar_cotacao(dados)
    if erros:
        return jsonify(ok=False, erros=erros), 400

    agora = datetime.now(timezone.utc)
    ip_hash = _hash_ip()
    try:
        recentes = Cotacao.query.filter(
            Cotacao.ip_hash == ip_hash, Cotacao.criado_em >= agora - timedelta(hours=1)
        ).count()
        if recentes >= LIMITE_POR_HORA:
            return _erro_json("Muitos envios em pouco tempo. Tente novamente mais tarde.", 429)

        db.session.add(Cotacao(**lead, consentimento_em=agora, versao_politica=VERSAO_POLITICA,
                               ip_hash=ip_hash))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.error("Falha ao gravar cotação.", exc_info=False)
        return _erro_json("Não foi possível registrar agora. Tente novamente em instantes.", 503)

    return jsonify(ok=True)


# ---------------------------------------------------------------------------
# Erros (sem detalhes técnicos para o visitante)
# ---------------------------------------------------------------------------
def _resposta_erro(status, titulo, texto):
    if request.path == "/contato":
        return _erro_json(titulo, status)
    return render_template("erro.html", status=status, titulo=titulo, texto=texto), status


@app.errorhandler(404)
def erro_404(_):
    return _resposta_erro(404, "Página não encontrada", "O endereço não existe ou foi movido.")


@app.errorhandler(405)
def erro_405(_):
    return _resposta_erro(405, "Método não permitido", "Esta página não aceita esse tipo de requisição.")


@app.errorhandler(413)
def erro_413(_):
    return _resposta_erro(413, "Envio grande demais", "Reduza o tamanho da mensagem e tente de novo.")


@app.errorhandler(500)
def erro_500(_):
    return _resposta_erro(500, "Algo deu errado", "Tente novamente em instantes.")


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
