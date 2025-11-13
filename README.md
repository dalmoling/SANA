# 📊 SANA - Sistema de Análise de Notas Acadêmicas

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-green?logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-orange)

**Sistema inteligente de análise acadêmica com IA integrada**

[Características](#-características) • [Instalação](#-instalação) • [Uso](#-uso) • [Tecnologias](#-tecnologias) • [Contribuição](#-contribuição)

</div>

---

## 📖 Sobre o Projeto

O **SANA** (Sistema de Análise de Notas Acadêmicas) é uma aplicação web desenvolvida como Trabalho de Conclusão de Curso (TCC) por Gustavo Dalmolin, Aluno do Instituto Federal Catarinense (IFC). O sistema oferece análises detalhadas do desempenho acadêmico de estudantes através de visualizações interativas e um chatbot inteligente powered by Google Gemini AI.

### 🎯 Objetivo

Facilitar o acompanhamento pedagógico através de:
- Análise automatizada de dados acadêmicos
- Identificação precoce de alunos em dificuldade
- Visualizações interativas de desempenho
- Comparação entre turmas e disciplinas
- Assistente virtual para consultas em linguagem natural

---

## ✨ Características

### 🤖 Chatbot Inteligente
- Integração com **Google Gemini AI** (gemini-2.0-flash-exp)
- Consultas em linguagem natural sobre dados acadêmicos
- Respostas contextualizadas e precisas
- Interface conversacional intuitiva

### 📊 Dashboard Interativo
- Gráficos dinâmicos com **Plotly**
- Visualização de médias por trimestre
- Ranking de melhores alunos
- Identificação de disciplinas com maior dificuldade
- Análise de desempenho geral da turma

### 👥 Gerenciamento de Turmas
- Upload e processamento de planilhas Excel
- Comparação entre múltiplas turmas
- Agrupamento por curso
- Detecção automática do trimestre atual
- Estatísticas detalhadas por turma

### 🔐 Sistema de Autenticação
- Login seguro com **JWT (JSON Web Tokens)**
- Controle de acesso baseado em roles:
  - **Professor**: Acesso a consultas e dashboard
  - **Coordenador**: Gerenciamento de turmas e comparações
  - **Admin**: Gerenciamento completo de contas

### 📈 Análises Acadêmicas
- Cálculo automático de médias por trimestre
- Classificação de alunos (Aprovado/Recuperação/Reprovado)
- Identificação de alunos que precisam de atenção
- Ranking de disciplinas por dificuldade
- Relatórios detalhados por aluno e disciplina

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.12 ou superior
- pip (gerenciador de pacotes Python)
- Conta Google Cloud com API Gemini habilitada

### Passo a Passo

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/sana-sistema-academico.git
cd sana-sistema-academico
```

2. **Crie um ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**

Crie um arquivo `.env` na raiz do projeto:
```env
GEMINI_API_KEY=sua_chave_api_aqui
```

5. **Execute a aplicação**
```bash
python app.py
```

6. **Acesse no navegador**
```
http://localhost:8080
```

---

## 💻 Uso

### Login Padrão

**Coordenador:**
- Usuário: `coordenador`
- Senha: `coord123`

**Professor:**
- Usuário: `professor`
- Senha: `prof123`

### Estrutura de Planilhas

As planilhas Excel devem seguir o formato:

| Nome | Disciplina | Nota 1º trimestre | Nota 2º trimestre | Nota 3º trimestre |
|------|------------|-------------------|-------------------|-------------------|
| ALUNO_01 | Matemática | 7.5 | 8.0 | 7.8 |
| ALUNO_01 | Português | 6.5 | 7.0 | 6.8 |

### Funcionalidades Principais

#### 1. Dashboard
- Visualize estatísticas gerais da turma selecionada
- Gráficos interativos de desempenho
- Lista de alunos que precisam de atenção

#### 2. Chatbot
- Faça perguntas como:
  - "Quantos alunos estão com média abaixo de 6 em Matemática?"
  - "Qual disciplina tem mais alunos com dificuldade?"
  - "Como está o desempenho do aluno João?"

#### 3. Consultas
- **Por Aluno**: Veja todas as notas e médias de um aluno específico
- **Por Disciplina**: Analise o desempenho geral em uma disciplina

#### 4. Gerenciamento de Turmas (Coordenador)
- Adicione, edite ou remova turmas
- Compare desempenho entre turmas
- Visualize estatísticas por curso

#### 5. Gerenciamento de Contas (Admin)
- Crie e gerencie contas de usuários
- Defina permissões e roles

---

## 🛠️ Tecnologias

### Backend
- **Flask** - Framework web Python
- **Flask-JWT-Extended** - Autenticação JWT
- **Pandas** - Processamento de dados
- **NumPy** - Cálculos numéricos
- **openpyxl** - Leitura de arquivos Excel

### Frontend
- **HTML5/CSS3** - Estrutura e estilização
- **JavaScript** - Interatividade
- **Tailwind CSS** - Framework CSS
- **Font Awesome** - Ícones

### Visualização
- **Plotly** - Gráficos interativos

### IA
- **Google Gemini AI** - Chatbot inteligente
- **python-dotenv** - Gerenciamento de variáveis de ambiente

---

## 📁 Estrutura do Projeto

```
sana-sistema-academico/
├── app.py                      # Aplicação Flask principal
├── analises_academicas.py      # Módulo de análises
├── gerenciador_turmas.py       # Gerenciamento de turmas
├── gerenciador_contas.py       # Gerenciamento de contas
├── requirements.txt            # Dependências Python
├── contas_coordenadores.json   # Banco de dados de usuários
│
├── static/
│   ├── javascript.js           # Scripts JavaScript
│   └── style.css               # Estilos CSS
│
├── templates/
│   ├── base.html               # Template base
│   ├── login.html              # Página de login
│   ├── dashboard.html          # Dashboard principal
│   ├── chatbot.html            # Interface do chatbot
│   ├── consulta.html           # Consulta por aluno
│   ├── consulta_disciplina.html # Consulta por disciplina
│   ├── gerenciar_turmas.html   # Gerenciamento de turmas
│   ├── comparar_turmas.html    # Comparação de turmas
│   ├── gerenciar_contas.html   # Gerenciamento de contas
│   └── manual.html             # Manual do usuário
│
└── turmas/                     # Planilhas das turmas
    ├── agropecuaria_2022.xlsx
    ├── eletro_a_2023.xlsx
    ├── eletro_b_2022.xlsx
    ├── info_a_2022.xlsx
    └── info_b_2022.xlsx
```

---

## 🔧 Funcionalidades Detalhadas

### Sistema de Trimestres
O sistema detecta automaticamente em qual trimestre a turma se encontra:
- **1º Trimestre**: Apenas notas do 1º trimestre preenchidas
- **2º Trimestre**: Notas do 1º e 2º trimestres preenchidas
- **Ano Completo**: Todos os três trimestres preenchidos

### Classificação de Alunos
- **Aprovado**: Média ≥ 6.0 em todas as disciplinas
- **Recuperação**: Pelo menos 1 disciplina com média entre 4.0 e 5.9
- **Reprovado**: Pelo menos 1 disciplina com média < 4.0

### Comparação de Turmas
- Agrupa turmas por curso automaticamente
- Exibe badges coloridos indicando o trimestre atual
- Calcula estatísticas comparativas
- Ranking de turmas por desempenho

---

## 📊 Capturas de Tela

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### Chatbot
![Chatbot](docs/screenshots/chatbot.png)

### Comparação de Turmas
![Comparação](docs/screenshots/comparacao.png)

---

## 🤝 Contribuição

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👨‍💻 Autor

**Seu Nome**
- GitHub: [@seu-usuario](https://github.com/seu-usuario)
- LinkedIn: [Seu Nome](https://linkedin.com/in/seu-perfil)
- Email: seu.email@exemplo.com

---

## 🙏 Agradecimentos

- Instituto Federal Catarinense (IFC)
- Orientador(a): [Nome do Orientador]
- Google Gemini AI
- Comunidade Open Source

---

## 📞 Suporte

Para suporte, entre em contato:
- 📧 Email: seu.email@exemplo.com
- 📱 WhatsApp: (49) 91358163
- 🐛 Issues: [GitHub Issues](https://github.com/seu-usuario/sana-sistema-academico/issues)

---

<div align="center">

**Desenvolvido com ❤️ para o TCC do IFC**

⭐ Se este projeto foi útil, considere dar uma estrela!

</div>

