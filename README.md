# 🚀 Invexa Control — Sistema de Gestão Industrial, Estoque e Produção

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/SQLAlchemy-ORM-red?style=for-the-badge" alt="SQLAlchemy" />
  <img src="https://img.shields.io/badge/SQLite%20%2F%20PostgreSQL-Database-blue?style=for-the-badge&logo=sqlite&logoColor=white" alt="Database" />
  <img src="https://img.shields.io/badge/Multi--Tenant-Supported-success?style=for-the-badge" alt="Multi-Tenancy" />
  <img src="https://img.shields.io/badge/Donate-Crypto-yellow?style=for-the-badge&logo=ethereum&logoColor=white" alt="Donate Crypto" />
</p>

O **Invexa Control** é uma solução completa de gestão operacional e controle de estoque voltada para confecções, indústrias leves e empresas com fluxo terceirizado (faccionistas/trabalhadores externos). O sistema conta com arquitetura **Multi-Tenancy** (múltiplas empresas), gestão de insumos, ordens de produção, relatórios gerenciais e central de suporte.

---

## 🔑 Credenciais Padrão para Testes

Para testar o sistema localmente logo após a inicialização:

| Campo | Valor Padrão |
| :--- | :--- |
| **URL de Acesso** | `http://localhost:8001/login` |
| **E-mail / Usuário** | `admin@invexa.com` |
| **Senha** | `admin123` |
| **Perfil** | Administrador Geral (Super Admin) |

> 💡 *Para alterar ou redefinir a senha do administrador a qualquer momento, execute:*
> ```powershell
> python reset_admin.py admin@invexa.com nova_senha
> ```

---

## 🖥️ Módulos e Telas do Sistema

O sistema é dividido em módulos com interfaces dinâmicas desenvolvidas em Jinja2 e CSS moderno:

### 1. 🔐 Autenticação & Perfil (`/login`, `/register`, `/profile`)
- Autenticação segura via **JWT** armazenado em cookies `HttpOnly`.
- Criação de contas com vinculação automática ou seleção de empresa (*Multi-Tenancy*).
- Gerenciamento de perfil do usuário e alteração de senha.

### 2. 📊 Dashboard Gerencial (`/dashboard`)
- Indicadores em tempo real (KPIs de estoque, ordens de produção ativas, saldo financeiro e peças em trânsito).
- Gráficos visuais de movimentações e fluxos operacionais.
- Alertas de produtos com estoque zerado ou abaixo do nível de segurança.

### 3. 📦 Gestão de Estoque e Produtos (`/inventory`)
- Cadastro completo de itens: **produtos simples**, **matérias-primas/insumos** e **produtos compostos (kits)**.
- Definição de SKU, código de barras, unidade de medida (`un`, `kg`, `m`, `cx`), preço de custo e preço de venda.
- Categorização de produtos e busca instantânea com filtros avançados.
- Controle rigoroso de estoque mínimo e reposição.

### 4. 🔄 Movimentações & Romaneios (`/movements`)
- Registro de movimentações de **Entrada**, **Saída** e **Ajustes de Inventário**.
- Histórico completo de transações com data, responsável e motivo.
- Geração e impressão de **Romaneios de Carga / Packing List** para conferência física de mercadorias.

### 5. 🏭 Ordens de Produção — OP (`/production`)
- Emissão de Ordens de Produção vinculadas a produtos compostos e fichas técnicas.
- Baixa automática de matérias-primas e insumos na inicialização da OP.
- Acompanhamento de estágios da produção: *Pendente*, *Em Produção*, *Concluída* e *Cancelada*.
- Apuração do rendimento real vs. projetado.

### 6. 👥 Faccionistas & Remessas Externas (`/workers`, `/shipments`)
- Cadastro de trabalhadores externos, costureiras e facções parceiras.
- Emissão de **Remessas de Envio**: envio de lotes de tecidos cortados para montagem externa.
- Registro de **Retorno de Peças**: conferência de peças prontas, peças defeituosas e cálculo automático do valor a pagar ao prestador de serviços.

### 7. 📈 Relatórios Analíticos (`/reports`)
- Relatórios consolidados de giro de estoque, curva ABC, produção e faturamento.
- Exportação de dados e visualização formatada para tomadas de decisão.

### 8. 🎫 Central de Atendimento & Suporte (`/support`)
- Abertura de chamados internos por colaboradores da empresa.
- Sistema de mensagens em tempo real no ticket, marcação de mensagens lidas e resolução de pendências.

### 9. ⚙️ Painel do Super Admin (`/admin/...`)
- **Empresas (`/admin/companies`)**: Criação e gestão de empresas no ambiente Multi-Tenant.
- **Usuários (`/admin/users`)**: Controle de permissões, ativação/desativação e elevação de privilégios.
- **Auditoria (`/admin/audit`)**: Registro cronológico de ações sensíveis realizadas no banco de dados.
- **Backup & Restauração (`/admin/backup`)**: Exportação e salvaguarda do banco de dados em um clique.
- **Guia do Sistema (`/admin/guide`)**: Documentação operacional interna integrada à interface.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.11 / 3.12
- **Framework Web:** [FastAPI](https://fastapi.tiangolo.com/) (rápido, assíncrono e de alta performance)
- **Servidor ASGI:** [Uvicorn](https://www.uvicorn.org/)
- **Templates:** Jinja2 com layout responsivo
- **ORM & Banco de Dados:** [SQLAlchemy](https://www.sqlalchemy.org/) + SQLite (local) / PostgreSQL (suportado para produção)
- **Segurança:** Passlib + Bcrypt para hashing de senhas e Python-JOSE para tokens JWT
- **Processamento de Imagens:** Pillow

---

## ⚙️ Como Instalar e Rodar o Projeto

### Pré-requisitos
- **Python 3.11+** instalado ([Download oficial](https://www.python.org/downloads/))
- Git instalado (opcional)

---

### Opção 1: Inicialização Rápida no Windows (Recomendado)

O projeto inclui um inicializador automático que limpa portas, instala dependências e inicia o servidor:

1. Clone ou extraia o repositório em uma pasta de sua escolha.
2. Dê um duplo-clique no arquivo **`run.bat`** (ou execute via terminal):
   ```cmd
   .\run.bat
   ```
3. O servidor estará ativo em:
   👉 **http://localhost:8001**

---

### Opção 2: Inicialização Manual (Windows / Linux / macOS)

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/Invexa-Control.git
   cd Invexa-Control
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicie a aplicação:**
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
   ```

5. **Acesse no seu navegador:**
   - Tela de Login: [http://localhost:8001/login](http://localhost:8001/login)
   - Documentação Interativa da API (Swagger): [http://localhost:8001/docs](http://localhost:8001/docs)

---

### Opção 3: Executando via Docker

O projeto já contém um `Dockerfile` pronto para contêineres:

```bash
# Construir a imagem
docker build -t invexa-control .

# Executar o container
docker run -d -p 8001:8001 --name invexa_app invexa-control
```

---

## 📂 Estrutura de Diretórios

```text
Invexa-Control/
├── app/
│   ├── api/
│   │   ├── dependencies.py       # Injeção de dependências (Auth, DB)
│   │   └── routers/              # Rotas divididas por módulos funcionais
│   │       ├── admin.py          # Telas e ações administrativas
│   │       ├── auth.py           # Login, logout, registro e perfil
│   │       ├── dashboard.py      # Visão geral e métricas
│   │       ├── inventory.py      # Produtos e categorias
│   │       ├── movements.py      # Movimentações e romaneios
│   │       ├── production.py     # Ordens de produção (OP)
│   │       ├── reports.py        # Relatórios analíticos
│   │       ├── shipments.py      # Remessas para facções
│   │       ├── support.py        # Tickets de suporte
│   │       └── workers.py        # Trabalhadores externos
│   ├── core/
│   │   ├── config.py             # Configurações de ambiente
│   │   ├── database.py           # Conexão e sessão do SQLAlchemy
│   │   ├── security.py           # Hash de senhas e JWT
│   │   └── init_db.py            # Criação de dados iniciais
│   ├── models/                   # Modelos relacionais (ORM)
│   │   ├── company.py            # Multi-Tenancy (Empresas)
│   │   ├── user.py               # Usuários
│   │   ├── inventory.py          # Produtos, Categorias e Movimentações
│   │   ├── production.py         # Ordens de Produção
│   │   ├── worker.py             # Faccionistas e Remessas
│   │   └── ticket.py             # Tickets de suporte
│   ├── static/                   # Arquivos estáticos (CSS, imagens, JS)
│   └── templates/                # Telas Jinja2 renderizadas pelo servidor
├── cleanup.py                    # Script para liberar portas e processos travados
├── list_users.py                 # Lista usuários cadastrados no banco
├── reset_admin.py                # Script de redefinição de senhas
├── requirements.txt              # Dependências do projeto
├── run.bat                       # Script de inicialização automática no Windows
└── Dockerfile                    # Configuração para deploy em container
```

---

## 🛠️ Scripts Úteis

- **Listar usuários cadastrados:**
  ```powershell
  python list_users.py
  ```
- **Redefinir senha de qualquer usuário:**
  ```powershell
  python reset_admin.py email@exemplo.com nova_senha
  ```
- **Limpar portas ocupadas e processos antigos:**
  ```powershell
  python cleanup.py
  ```

---

## ☕ Apoie o Projeto / Doações

Se este projeto foi útil para você ou para sua empresa e você deseja apoiar o desenvolvimento e manutenção contínua, considere fazer uma contribuição via criptomoeda:

| Rede / Padrão | Endereço da Carteira (ETH / BSC / Polygon / Arbitrum / USDT / USDC) |
| :--- | :--- |
| **EVM Multi-Chain** | `0x1c4E87f67Eb42a72F562d242f518b0F31DDa2688` |

> 💖 *Toda contribuição é muito bem-vinda e incentiva a continuidade do projeto com novas funcionalidades open-source!*

---

## 📄 Licença

Este projeto está sob licença proprietária / de uso interno. Consulte os mantenedores para permissões de uso comercial e distribuição.

