# Segurança: estado atual e próximos passos

Este documento descreve a implementação observada no código. Não é uma certificação de segurança, auditoria jurídica, pentest ou declaração de conformidade com a LGPD.

## Controles presentes no app

| Área | Implementação observada |
|---|---|
| Segredos de produção | O app exige `SECRET_KEY` quando `RAILWAY_PROJECT_ID` ou `APP_ENV=production` está presente. Configure segredos no provedor, nunca no repositório. |
| Banco | SQLAlchemy usa parâmetros; `DATABASE_URL` é lida do ambiente; `hide_parameters=True` evita valores SQL nos logs do SQLAlchemy. |
| Dados do formulário | Limites de tamanho e validação no servidor; limite do corpo HTTP de 16 KB; respostas do endpoint não são armazenadas em cache. |
| CSRF/abuso | `POST /contato` exige JSON, verifica o cabeçalho `Origin` quando enviado, usa honeypot e limita envios pelo hash HMAC do IP. |
| XSS | Templates Jinja usam autoescape; não há conteúdo enviado pelo usuário renderizado em uma página administrativa. |
| Cabeçalhos | CSP restritiva, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` e cabeçalhos Cross-Origin; HSTS quando a requisição é reconhecida como HTTPS. |
| Logs | Erros de banco retornam mensagem genérica e não incluem a exceção ou os dados do lead no log da aplicação. |
| Coleta | O formulário pede dados de contato e informações gerais da clínica, proíbe dados de pacientes na orientação e não tem upload de arquivos. |
| Testes | `test_seguranca.py` foi ajustado para SQLite em memória, isolando-o do banco local e do PostgreSQL externo. |

## Achados desta revisão

### Repositório GitHub público

O remoto `Jedaigodx/BPO_landing_page` está público. O arquivo `.DS_Store` estava versionado e não havia `.gitignore`, apesar de o documento anterior afirmar que `.env` era ignorado. Foi adicionado `.gitignore` e o `.DS_Store` foi removido do índice local (continua no computador, ignorado pelo Git). A exclusão está preparada localmente e só chegará ao GitHub após um commit e push; ela não apaga o arquivo de commits históricos. Não encontrei arquivos `.env`, bancos SQLite ou chaves privadas na árvore atualmente versionada. Esta verificação não substitui um scanner de segredos em todo o histórico Git.

Se uma credencial real já tiver sido enviada ao GitHub em qualquer commit, revogue-a e gere outra. Apagar o arquivo em um commit novo não invalida uma credencial exposta no histórico.

### Dados pessoais e de saúde

Os leads do formulário contêm dados pessoais de contato e ficam no PostgreSQL até serem removidos; não existe rotina automática de retenção ou exclusão. Após persistir o pedido, o servidor devolve um link com os dados preenchidos para o WhatsApp comercial. O navegador abre o link e a pessoa precisa confirmar o envio; o site não envia a mensagem automaticamente. Defina um prazo de retenção e estabeleça como atender solicitações de titulares. A política de privacidade ainda tem campos empresariais e de retenção a completar.

O formulário não foi projetado para receber prontuários ou dados de saúde. Se a operação BPO vier a acessar dados de pacientes, faça avaliação específica antes do início: finalidade, necessidade, acesso mínimo, compartilhamento, segurança, retenção/descarte, resposta a incidentes e obrigações contratuais. A função de controlador ou operador depende de quem determina as finalidades e os meios essenciais do tratamento em cada fluxo; não deve ser presumida apenas pelo nome do contrato. Encaminhe contratos e interpretação jurídica a profissional qualificado.

### Limites técnicos que merecem atenção

1. **Sem retenção automática:** os dados pessoais do formulário permanecem na tabela até uma exclusão manual. Defina prazo e processo de descarte antes de captar leads reais.
2. **Rate limit sujeito a concorrência:** o limite atual conta registros e depois insere; requisições simultâneas podem ultrapassá-lo. Considere um limitador atômico externo se houver abuso.
3. **`db.create_all()` não migra schema:** cria tabelas ausentes, mas não atualiza com segurança tabelas existentes. Adote migrações versionadas antes de alterações de dados/modelos em produção.
4. **Dependências:** as versões estão fixadas em `requirements.txt`, mas não foi executada nesta revisão uma auditoria de avisos de segurança das dependências. Rode `pip-audit -r requirements.txt` antes de publicar e periodicamente.
5. **WhatsApp:** a mensagem de saída contém os dados de contato e o resumo preenchidos no formulário e esses dados aparecem no link gerado no navegador. Avise claramente sobre esse encaminhamento, limite a coleta ao necessário e não solicite dados de pacientes. O WhatsApp recebe esses dados apenas se a pessoa confirmar o envio.
6. **Proxy confiável:** `ProxyFix` confia em um salto quando Railway está configurado ou `TRUST_PROXY=1`. Não ative essa variável sem um proxy controlado à frente da aplicação, pois cabeçalhos encaminhados podem ser falsificados.
7. **Banco:** use a conexão privada do Railway, limite acesso administrativo, habilite autenticação forte na conta do provedor e confirme backups e recuperação. O app não cifra individualmente os campos da tabela.
8. **Privacidade da página:** complete responsável, CNPJ, canal de contato e retenção no aviso de privacidade e obtenha revisão profissional antes da publicação.

## Medidas recomendadas no GitHub

- Manter apenas código e documentação no repositório; nunca versionar `.env`, URLs de banco, dados de leads, backups, exports ou dados de pacientes.
- Ativar Secret scanning e Push protection se disponíveis para o plano/organização e revisar os alertas.
- Ativar autenticação multifator na conta e restringir colaboradores com permissão de escrita.
- Considerar regras de proteção para `main` (revisão de mudanças e checks obrigatórios) antes de receber contribuições externas.
- Se surgir um segredo exposto, revogar primeiro, revisar logs de acesso e só depois limpar histórico se necessário; uma reescrita de histórico exige coordenação com quem usa o repositório.

## Referências oficiais para o trabalho com saúde e dados

- [ANS — TISS e versão vigente](https://www.gov.br/ans/pt-br/assuntos/prestadores/padrao-para-troca-de-informacao-de-saude-suplementar-2013-tiss/)
- [ANPD — Guia de Segurança da Informação para agentes de tratamento de pequeno porte](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte)
- [ANPD — Guia sobre agentes de tratamento e encarregado](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-para-definicoes-dos-agentes-de-tratamento-e-do-encarregado)

## Escopo da revisão

Revisão estática da árvore local e leitura da página pública do repositório em 15/10/2026. Não foram executados testes automatizados, scanner de dependências, análise de histórico de segredos, teste de invasão, revisão de configurações da conta GitHub/Railway nem conexão a um PostgreSQL real nesta atualização.
