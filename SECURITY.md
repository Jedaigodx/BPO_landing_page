# Análise de segurança

Escopo: aplicação Flask (rotas, formulário de cotação, banco), front-end, dependências e
implantação no Railway. Ferramentas usadas: `test_seguranca.py` (36 verificações, todas
passando), `bandit` (sem achados) e `pip-audit` (sem vulnerabilidades conhecidas nas
dependências fixadas).

## O que está protegido

| Risco | Como é tratado |
|---|---|
| XSS | Jinja com autoescape; CSP `script-src 'self'` e `style-src 'self'` (sem JS ou estilo inline); `object-src 'none'` |
| Clickjacking | `frame-ancestors 'none'` e `X-Frame-Options: DENY` |
| SQL injection | SQLAlchemy com parâmetros; teste grava texto malicioso como dado |
| CSRF no formulário | Só aceita `application/json` (form-urlencoded dá 415) e confere o cabeçalho `Origin` |
| Vazamento de dados a terceiros | Fontes hospedadas localmente; CSP bloqueia qualquer domínio externo; sem Google Fonts, analytics ou CDN |
| Robôs e abuso | Campo isca, limite de 5 envios por hora por IP, corpo máximo de 16 KB |
| Dados pessoais (LGPD) | Consentimento e versão da política gravados; IP guardado só como hash HMAC; parâmetros SQL ocultos nos logs |
| Interceptação | HSTS e `upgrade-insecure-requests` em HTTPS; `ProxyFix` para o proxy do Railway |
| Segredos | `SECRET_KEY` obrigatória em produção; nenhuma credencial no código; `.env` no `.gitignore` |
| Erros | Páginas 404/405/413/500 sem detalhes técnicos |
| Superfície | Sem login, sem painel, sem upload: a única entrada de dados é `POST /contato` |

## Riscos que sobram (e o que fazer)

1. **Robôs distribuídos.** O limite por IP não segura um ataque vindo de muitos IPs. Se aparecer spam,
   adicione um desafio (Cloudflare Turnstile ou hCaptcha) e ajuste a CSP para o domínio do serviço.
2. **Aviso de novos pedidos.** Os pedidos só ficam no banco. Quem verificar o Railway com pouca frequência pode demorar a responder.
   Um e-mail de aviso exige guardar credenciais SMTP: use variável de ambiente, nunca o código.
3. **Banco no Railway.** Mantenha a conexão pela rede privada, não exponha o proxy TCP público,
   ative 2FA na conta Railway e confira os backups do plugin.
4. **Retenção de dados.** Defina por quanto tempo guardar pedidos antigos e como atender pedido de exclusão (LGPD).
5. **Política de privacidade.** O texto atual é um modelo: preencha nome, CNPJ e contato do encarregado
   e peça revisão jurídica antes de publicar.
6. **Dependências.** Rode `pip-audit -r requirements.txt` de vez em quando e antes de cada deploy.
7. **Domínio próprio.** Depois de apontar o domínio, ative HTTPS e considere o `includeSubDomains` no HSTS.

## Limite desta análise

Os testes rodaram com SQLite. O caminho PostgreSQL usa o mesmo código SQLAlchemy, mas não foi exercitado
contra um PostgreSQL real nesta máquina: faça um envio de teste logo após o primeiro deploy.
Não foi feito teste de invasão externo.
