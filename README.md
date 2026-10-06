# Landing page – BPO de faturamento e auditoria médica (demonstração)

Landing page em Flask para apresentar o conceito do negócio. Nome, CNPJ e contatos
ainda estão em branco de propósito.

## Rodar no Windows

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python app.py

Abra http://127.0.0.1:5000

## Onde mexer

- `app.py`: dicionário `EMPRESA` (nome, CNPJ, telefone, e-mail, endereço), além de
  serviços, etapas, diferenciais, perguntas frequentes e os dados fictícios das demos.
  Quando `nome` ou `cnpj` estiverem preenchidos, a página passa a exibi-los sozinha.
- `templates/index.html`: estrutura e textos da página.
- `static/css/style.css`: cores e tipografia (variáveis no topo do arquivo).
- `static/js/main.js`: simulação de auditoria, formulário de cotação.

## Contatos recebidos (pedidos de cotação)

Ficam na tabela `cotacoes`: PostgreSQL no Railway (via `DATABASE_URL`) e SQLite local
(`instance/dev.db`) em desenvolvimento. Não há painel administrativo de propósito (menos
superfície de ataque): consulte pela aba **Data** do plugin PostgreSQL no Railway.

## Publicar no Railway

1. Crie o projeto a partir deste código e adicione o plugin **PostgreSQL**.
2. No serviço web, defina `SECRET_KEY` (valor longo e aleatório, ex.: `python -c "import secrets; print(secrets.token_hex(32))"`)
   e `DATABASE_URL` como referência à variável do plugin.
3. Sem `SECRET_KEY` o app se recusa a iniciar em produção.
4. Leia o `SECURITY.md` antes de divulgar o endereço.

## Testes

    python test_seguranca.py
