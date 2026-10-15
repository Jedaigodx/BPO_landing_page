# Gestão do ciclo de receita em saúde

Landing page em Flask para apresentar serviços de auditoria, faturamento e organização dos processos de receita de clínicas e prestadores de saúde. O escopo considera rotinas de convênios e atendimentos particulares, integração com os sistemas já usados pela clínica e recomendações de tecnologia quando houver uma necessidade identificada.

O projeto está em fase de estruturação. Nome empresarial, CNPJ, número de WhatsApp e contatos institucionais ainda precisam ser configurados antes da divulgação pública. O diagnóstico inicial descrito no site é uma proposta gratuita e delimitada; qualquer implementação ou operação recorrente depende de escopo e proposta próprios.

## Requisitos

- Python 3.11 ou superior
- PostgreSQL em produção (por exemplo, Railway) ou SQLite para desenvolvimento local

## Executar localmente no Windows

No PowerShell, a partir da pasta do projeto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000`. Sem `DATABASE_URL`, o app cria/usa `instance/dev.db` em SQLite. O `SECRET_KEY` de desenvolvimento é local e fixo; nunca publique a aplicação em produção com essa configuração.

## Configurar PostgreSQL no Railway

1. No projeto Railway, adicione um serviço **PostgreSQL**.
2. No serviço web Flask, abra **Variables** e crie `DATABASE_URL` como uma **Reference Variable** para `DATABASE_URL` do serviço Postgres (por exemplo, `${{Postgres.DATABASE_URL}}`). O nome `Postgres` deve corresponder ao nome do seu serviço de banco.
3. Crie `SECRET_KEY` como variável secreta do serviço web. Gere um valor forte localmente com `python -c "import secrets; print(secrets.token_hex(32))"` e cole o resultado somente no painel Railway. Não adicione esse valor ao código, README, commit ou issue.
4. Para ativar os botões de WhatsApp, crie `WHATSAPP_NUMBER` com o número comercial completo em dígitos: código do país + DDD + telefone. Exemplo de formato: `55` + `62` + número comercial. Não use espaços, `+`, parênteses ou hífen. Sem essa variável, os botões continuam levando ao formulário do site.
5. Faça o deploy do serviço web. A aplicação lê `DATABASE_URL`, ajusta o prefixo PostgreSQL para o driver `psycopg` e cria a tabela `cotacoes` se ela ainda não existir.

No Railway, prefira a conexão privada entre os serviços e mantenha a porta pública do PostgreSQL desativada se não precisar de acesso externo. Para acesso administrativo, use o painel de dados do Railway ou uma conexão segura autorizada; nunca coloque credenciais de banco em arquivo versionado.

### Quais dados vão para o banco

Envios do formulário são gravados em `cotacoes`: nome, e-mail, WhatsApp, nome da clínica (se informado), volume aproximado, convênios, áreas de interesse, mensagem, data/versão do consentimento e um hash do IP para limitação de abuso. O endereço IP original não é guardado. O formulário orienta a não enviar informações de pacientes.

O botão de WhatsApp abre uma conversa no WhatsApp com uma mensagem genérica pré-preenchida. Essa conversa é tratada no WhatsApp e **não** é gravada automaticamente na tabela `cotacoes`. O visitante só envia a mensagem depois de revisar e tocar em enviar.

`db.create_all()` cria tabelas ausentes, mas não é uma ferramenta de migração: mudanças futuras na estrutura das tabelas precisam de migrações planejadas antes do deploy. Faça backups antes de alterações de schema e defina uma política de retenção e exclusão dos pedidos.

## Variáveis de ambiente

| Variável | Obrigatória | Uso |
|---|---|---|
| `DATABASE_URL` | Produção | URL privada do PostgreSQL; sem ela, usa SQLite local |
| `SECRET_KEY` | Produção | Segredo do app e chave do HMAC usado no hash do IP |
| `WHATSAPP_NUMBER` | Opcional | Telefone comercial internacional em dígitos; ativa os links com texto pré-preenchido |
| `APP_ENV=production` | Fora do Railway | Faz o app exigir `SECRET_KEY` em outros provedores |
| `TRUST_PROXY=1` | Opcional | Só quando estiver atrás de exatamente um proxy confiável |

Não existe leitura automática de `.env` neste app. Para desenvolvimento, configure variáveis na sessão do terminal ou use uma ferramenta local que as injete. `.env` está excluído do Git; não use dados reais de pacientes durante desenvolvimento.

## Onde alterar

- `app.py`: conteúdo dos serviços, etapas, perguntas frequentes, configuração empresarial e variáveis de ambiente.
- `templates/index.html`: explicação dos gargalos, serviços, sistemas, LGPD e formulário/WhatsApp.
- `templates/base.html`: título, navegação e rodapé.
- `static/css/style.css`: identidade visual, componentes e responsividade.
- `static/js/main.js`: menu, botão fixo em telas pequenas e envio do formulário.
- `templates/privacidade.html`: aviso de privacidade do formulário; completar dados da empresa e retenção antes de publicar.
- `SECURITY.md`: controles atuais, limites e ações de segurança pendentes.

## Testes de segurança

```powershell
python test_seguranca.py
```

A suíte usa SQLite em memória para não apagar o banco local ou conectar ao PostgreSQL configurado no ambiente. Não execute testes ou scripts destrutivos contra produção.

## Antes de publicar

1. Configure o nome empresarial, CNPJ, contatos e número de WhatsApp reais.
2. Complete a política de privacidade, defina a retenção dos leads e peça revisão profissional adequada.
3. Configure PostgreSQL, `SECRET_KEY`, HTTPS e backups no provedor.
4. Revise `SECURITY.md`, as permissões do repositório e as variáveis do Railway.
5. Não envie ao formulário, a issues do GitHub ou a commits dados de pacientes, credenciais ou URLs de conexão.
