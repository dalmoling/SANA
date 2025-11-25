from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import os
from analises_academicas import AnalisadorAcademico
from gerenciador_turmas import GerenciadorTurmas
from gerenciador_contas import GerenciadorContas

import plotly.graph_objs as go
import plotly.utils
import json
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity, get_jwt
from datetime import timedelta
import hashlib
import time

# Carrega as variáveis de ambiente e configura a API Key
load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Cache para respostas do Gemini
gemini_cache = {}
CACHE_EXPIRATION = 3600  # 1 hora em segundos

# Flag para desabilitar Gemini temporariamente se houver problemas de quota
GEMINI_ENABLED = True
GEMINI_ERROR_MESSAGE = None

app = Flask(__name__)

# Configuração Flask
app.config['SECRET_KEY'] = 'sua-chave-secreta-super-segura-aqui'  # Para sessões

# Configuração JWT
app.config['JWT_SECRET_KEY'] = 'sua-chave-secreta-super-segura-aqui-2024'  # Mude em produção
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
app.config['JWT_COOKIE_SECURE'] = False  # True em produção com HTTPS
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Simplificar para desenvolvimento
jwt = JWTManager(app)

# Inicializar gerenciadores
gerenciador_turmas = GerenciadorTurmas()
gerenciador_contas = GerenciadorContas()

# Variável global para armazenar o analisador da turma ativa
analisador = None
contexto = ""

def obter_analisador_turma(nome_turma=None):
    """Obtém o analisador para uma turma específica"""
    global analisador, contexto

    if nome_turma:
        # Carregar turma específica
        arquivo = gerenciador_turmas.obter_arquivo_turma(nome_turma)
        if arquivo:
            try:
                analisador = AnalisadorAcademico(arquivo)
                df = analisador.df
                contexto = df.to_string(index=False)

                # Criar contexto enriquecido com análises
                relatorio = analisador.relatorio_geral_turma()
                ranking_dificuldade = analisador.ranking_disciplinas_dificeis()

                contexto_enriquecido = f"""
DADOS DA PLANILHA:
{contexto}

ANÁLISES ESTATÍSTICAS:
- Total de alunos: {relatorio['total_alunos']}
- Total de disciplinas: {relatorio['total_disciplinas']}
- Média geral da turma: {relatorio['media_geral_turma']:.2f}
- Percentual com dificuldade: {relatorio['percentual_dificuldade']:.1f}%
- Disciplina mais difícil: {relatorio['disciplina_mais_dificil']}
- Disciplina mais fácil: {relatorio['disciplina_mais_facil']}

RANKING DE DIFICULDADE (Top 5):
"""
                for i, (disciplina, percentual, total) in enumerate(ranking_dificuldade[:5], 1):
                    nome_disciplina = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina
                    contexto_enriquecido += f"{i}. {nome_disciplina}: {percentual:.1f}% ({total} alunos com dificuldade)\n"

                contexto = contexto_enriquecido
                return analisador
            except Exception as e:
                print(f"Erro ao carregar turma {nome_turma}: {e}")
                return None

    return analisador

def fazer_pergunta_gemini(pergunta, contexto):
    try:
        # Criar hash da pergunta para cache
        cache_key = hashlib.md5(pergunta.encode()).hexdigest()

        # Verificar se a resposta está em cache e ainda é válida
        if cache_key in gemini_cache:
            cached_data = gemini_cache[cache_key]
            if time.time() - cached_data['timestamp'] < CACHE_EXPIRATION:
                print(f"✅ Resposta recuperada do cache para: {pergunta[:50]}...")
                return cached_data['response']
            else:
                # Cache expirado, remover
                del gemini_cache[cache_key]

        # Usar modelo mais rápido e configurar para respostas otimizadas
        model = genai.GenerativeModel(
            'gemini-2.5-flash-lite',
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 1024,  # Limitar tamanho da resposta
            }
        )

        # Criar resumo do contexto ao invés de enviar tudo
        if analisador:
            relatorio = analisador.relatorio_geral_turma()

            # Calcular estatísticas de aprovação/reprovação
            aprovados = 0
            recuperacao = 0
            reprovados = 0

            for aluno in analisador.alunos:
                for disciplina in analisador.disciplinas:
                    media = analisador.calcular_media_aluno(aluno, disciplina)
                    if media >= 6.0:
                        aprovados += 1
                    elif media >= 4.0:
                        recuperacao += 1
                    else:
                        reprovados += 1

            # Obter ranking dos melhores alunos (calcular manualmente)
            ranking_alunos = []
            for aluno in analisador.alunos:
                medias = []
                aprovacoes = 0
                for disciplina in analisador.disciplinas:
                    media = analisador.calcular_media_aluno(aluno, disciplina)
                    if media > 0:
                        medias.append(media)
                        if media >= 6.0:
                            aprovacoes += 1

                if medias:
                    media_geral = sum(medias) / len(medias)
                    ranking_alunos.append({
                        'nome': aluno,
                        'media': media_geral,
                        'aprovacoes': aprovacoes
                    })

            # Ordenar por média decrescente
            ranking_alunos.sort(key=lambda x: x['media'], reverse=True)

            # Top 5 melhores
            ranking_melhores = "\n".join([
                f"  {i+1}. {aluno['nome']}: média {aluno['media']:.2f} ({aluno['aprovacoes']} aprovações)"
                for i, aluno in enumerate(ranking_alunos[:5])
            ])

            # Obter alunos que precisam de atenção
            alunos_atencao = analisador.alunos_precisam_atencao(min_reprovacoes=2)
            lista_atencao = "\n".join([
                f"  - {aluno['nome']}: média {aluno['media_geral']:.2f} ({aluno['total_reprovacoes']} reprovações, prioridade {aluno['prioridade']})"
                for aluno in alunos_atencao[:5]  # Limitar a 5
            ])

            # Obter desempenho por disciplina COM alunos com dificuldade
            disciplinas_info = []
            alunos_dificuldade_por_disc = analisador.identificar_alunos_dificuldade()

            for disciplina in analisador.disciplinas:
                nome_disc = disciplina.replace('Disciplina - ', '')
                medias_disc = [analisador.calcular_media_aluno(aluno, disciplina) for aluno in analisador.alunos]
                medias_validas = [m for m in medias_disc if m > 0]

                if medias_validas:
                    media_disc = sum(medias_validas) / len(medias_validas)

                    # Obter alunos com dificuldade nesta disciplina
                    alunos_dif = alunos_dificuldade_por_disc.get(disciplina, [])
                    qtd_dif = len(alunos_dif)

                    if qtd_dif > 0:
                        # Mostrar apenas os 3 primeiros alunos para não sobrecarregar
                        nomes_dif = ", ".join(alunos_dif[:3])
                        if qtd_dif > 3:
                            nomes_dif += f" e mais {qtd_dif - 3}"
                        disciplinas_info.append(f"  - {nome_disc}: média {media_disc:.2f} ({qtd_dif} alunos com dificuldade: {nomes_dif})")
                    else:
                        disciplinas_info.append(f"  - {nome_disc}: média {media_disc:.2f} (sem alunos com dificuldade)")

            disciplinas_texto = "\n".join(disciplinas_info[:10])  # Limitar a 10

            # Obter evolução por trimestre (calcular média geral de cada trimestre)
            desempenho_por_disc = analisador.desempenho_por_trimestre()

            # Calcular média geral de cada trimestre
            trim1_valores = []
            trim2_valores = []
            trim3_valores = []

            for disciplina, trimestres in desempenho_por_disc.items():
                if trimestres['1º Trimestre'] > 0:
                    trim1_valores.append(trimestres['1º Trimestre'])
                if trimestres['2º Trimestre'] > 0:
                    trim2_valores.append(trimestres['2º Trimestre'])
                if trimestres['3º Trimestre'] > 0:
                    trim3_valores.append(trimestres['3º Trimestre'])

            trim1 = sum(trim1_valores) / len(trim1_valores) if trim1_valores else 0.0
            trim2 = sum(trim2_valores) / len(trim2_valores) if trim2_valores else 0.0
            trim3 = sum(trim3_valores) / len(trim3_valores) if trim3_valores else 0.0

            # Criar texto de evolução baseado nos dados disponíveis
            if trim3 > 0:  # Tem todos os 3 trimestres
                evolucao_texto = f"""  - 1º Trimestre: média {trim1:.2f}
  - 2º Trimestre: média {trim2:.2f}
  - 3º Trimestre: média {trim3:.2f}"""
            elif trim2 > 0:  # Tem apenas 1º e 2º
                evolucao_texto = f"""  - 1º Trimestre: média {trim1:.2f}
  - 2º Trimestre: média {trim2:.2f}
  - 3º Trimestre: não disponível (ainda não concluído)"""
            else:  # Tem apenas 1º
                evolucao_texto = f"""  - 1º Trimestre: média {trim1:.2f}
  - 2º Trimestre: não disponível (ainda não concluído)
  - 3º Trimestre: não disponível (ainda não concluído)"""

            if trim3 > 0:  # Se tem 3º trimestre
                if trim3 > trim2 > trim1:
                    tendencia = "📈 Melhora constante ao longo do ano"
                elif trim3 < trim2 < trim1:
                    tendencia = "📉 Queda constante ao longo do ano"
                elif trim3 > trim1:
                    tendencia = "📈 Melhora geral (3º > 1º)"
                elif trim3 < trim1:
                    tendencia = "📉 Queda geral (3º < 1º)"
                else:
                    tendencia = "➡️ Desempenho estável"
            elif trim2 > 0:  # Se tem apenas 1º e 2º trimestre
                if trim2 > trim1:
                    tendencia = "📈 Melhora do 1º para o 2º trimestre"
                elif trim2 < trim1:
                    tendencia = "📉 Queda do 1º para o 2º trimestre"
                else:
                    tendencia = "➡️ Desempenho estável"
            else:
                tendencia = "Apenas 1º trimestre disponível"

            contexto_resumido = f"""
DADOS DA TURMA ATUAL:
- Total de alunos: {relatorio['total_alunos']}
- Total de disciplinas: {relatorio['total_disciplinas']}
- Média geral da turma: {relatorio['media_geral_turma']:.2f}
- Aprovações: {aprovados}
- Em recuperação: {recuperacao}
- Reprovações: {reprovados}
- Disciplina mais difícil: {relatorio['disciplina_mais_dificil'].replace('Disciplina - ', '')}
- Disciplina mais fácil: {relatorio['disciplina_mais_facil'].replace('Disciplina - ', '')}

EVOLUÇÃO AO LONGO DOS TRIMESTRES:
{evolucao_texto}
Tendência: {tendencia}

TOP 5 MELHORES ALUNOS:
{ranking_melhores}

ALUNOS QUE PRECISAM DE ATENÇÃO:
{lista_atencao if lista_atencao else "  Nenhum aluno com 2+ reprovações"}

DESEMPENHO POR DISCIPLINA:
{disciplinas_texto}
"""
        else:
            contexto_resumido = "Dados da turma não disponíveis no momento."

        # Criar o prompt especializado para análise acadêmica
        prompt = f"""Você é um assistente especializado em análise de dados acadêmicos do IFC.

{contexto_resumido}

INSTRUÇÕES:
- Você TEM ACESSO COMPLETO aos dados acima, incluindo:
  * Estatísticas gerais da turma
  * Evolução por trimestre
  * Ranking dos melhores alunos (com nomes)
  * Alunos que precisam de atenção (com nomes)
  * Desempenho por disciplina (com nomes dos alunos com dificuldade em cada disciplina)
- As notas variam de 0 a 10
- Média mínima para aprovação: 6.0
- Recuperação: 4.0 a 5.9
- Reprovação: abaixo de 4.0
- Quando perguntarem sobre alunos com dificuldade em uma disciplina específica, USE os dados de "DESEMPENHO POR DISCIPLINA" que mostram os nomes dos alunos
- Você pode analisar a evolução das notas ao longo dos trimestres
- Seja CONCISO e DIRETO nas respostas (máximo 3 parágrafos curtos)
- SEMPRE cite nomes específicos de alunos quando disponíveis nos dados
- Se a pergunta for sobre um aluno específico que não está na lista, informe que precisa de mais detalhes

PERGUNTA: {pergunta}

RESPOSTA:"""

        # Gerar resposta com retry automático
        print(f"🔄 Chamando API Gemini para: {pergunta[:50]}...")

        max_retries = 3
        retry_delay = 2  # segundos

        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)

                # Armazenar no cache
                resposta_texto = response.text.strip()
                gemini_cache[cache_key] = {
                    'response': resposta_texto,
                    'timestamp': time.time()
                }
                print(f"✅ Resposta armazenada em cache")

                return resposta_texto

            except Exception as api_error:
                error_msg = str(api_error)

                # Verificar se é erro de quota
                if "429" in error_msg or "quota" in error_msg.lower():
                    # Extrair tempo de espera se disponível
                    import re
                    wait_match = re.search(r'retry in (\d+\.?\d*)', error_msg)
                    if wait_match:
                        wait_time = float(wait_match.group(1))
                    else:
                        wait_time = retry_delay * (2 ** attempt)  # Backoff exponencial

                    if attempt < max_retries - 1:
                        print(f"⏳ Quota excedida. Aguardando {wait_time:.1f}s antes de tentar novamente... (tentativa {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        return f"⚠️ Limite de requisições da API Gemini atingido. Por favor, aguarde alguns segundos e tente novamente. O sistema usa cache para evitar chamadas repetidas."
                else:
                    # Outro tipo de erro
                    raise api_error

        return "Erro: Não foi possível processar a pergunta após várias tentativas."

    except Exception as e:
        return f"Erro ao processar a pergunta: {str(e)}"

# Rotas de Autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    # POST - Processar login
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Todos os campos são obrigatórios'}), 400

    # Verificar credenciais usando gerenciador de contas
    if not gerenciador_contas.verificar_credenciais(username, password):
        return jsonify({'message': 'Credenciais inválidas'}), 401

    # Obter dados do usuário
    user = gerenciador_contas.obter_dados_usuario(username)
    if not user:
        return jsonify({'message': 'Credenciais inválidas'}), 401

    # Criar token JWT
    access_token = create_access_token(
        identity=username,
        additional_claims={
            'role': user['role'],
            'name': user['name'],
            'is_admin': user.get('is_admin', False)
        }
    )

    # Criar resposta e definir cookie
    response = jsonify({
        'access_token': access_token,
        'user': {
            'username': username,
            'name': user['name'],
            'role': user['role']
        }
    })

    # Adicionar role à sessão para uso nos templates
    session['user_role'] = user['role']

    # Definir cookie JWT
    from flask_jwt_extended import set_access_cookies
    set_access_cookies(response, access_token)

    return response

@app.route('/logout', methods=['POST'])
def logout():
    from flask_jwt_extended import unset_jwt_cookies
    response = jsonify({'message': 'Logout realizado com sucesso'})
    unset_jwt_cookies(response)
    return response

@app.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    current_user = get_jwt_identity()
    return jsonify({'valid': True, 'user': current_user})

# Rota principal - Dashboard
@app.route('/')
def index():
    try:
        # Tentar verificar se há token JWT válido
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        current_user = get_jwt_identity()
        print(f"Dashboard acessado - Usuário: {current_user}")

        if not current_user:
            print("Usuário não autenticado, redirecionando para login")
            return redirect(url_for('login'))

        print("Usuário autenticado, carregando dashboard")
        return render_template('dashboard.html')
    except Exception as e:
        print(f"Erro na verificação JWT: {e}")
        return redirect(url_for('login'))

# Rota para o chatbot
@app.route('/chatbot')
@jwt_required()
def chatbot():
    return render_template('chatbot.html')

# Rota para consulta de alunos
@app.route('/consulta')
@jwt_required()
def consulta():
    return render_template('consulta.html')

# Rota para consulta por disciplina
@app.route('/consulta-disciplina')
@jwt_required()
def consulta_disciplina():
    return render_template('consulta_disciplina.html')

# Rota para gerenciamento de turmas (coordenador)
@app.route('/gerenciar-turmas')
@jwt_required()
def gerenciar_turmas():
    current_user = get_jwt_identity()
    claims = get_jwt()

    # Verificar se é coordenador
    if claims.get('role') != 'coordenador':
        return redirect('/')

    return render_template('gerenciar_turmas.html')

# Rota para comparação de turmas (coordenador)
@app.route('/comparar-turmas')
@jwt_required()
def comparar_turmas():
    current_user = get_jwt_identity()
    claims = get_jwt()

    # Verificar se é coordenador
    if claims.get('role') != 'coordenador':
        return redirect('/')

    return render_template('comparar_turmas.html')

# Rota para o manual do usuário
@app.route('/manual')
@jwt_required()
def manual():
    return render_template('manual.html')

# Endpoint para receber a pergunta e retornar a resposta
@app.route('/pergunta', methods=['POST'])
@jwt_required()
def pergunta():
    data = request.get_json()
    pergunta_usuario = data.get('pergunta')
    resposta = fazer_pergunta_gemini(pergunta_usuario, contexto)
    return jsonify({'resposta': resposta})

# APIs para os gráficos e dados
@app.route('/api/relatorio-geral')
@jwt_required()
def api_relatorio_geral():
    """API para dados do relatório geral"""
    claims = get_jwt()
    # Somente coordenador pode ver estatísticas globais
    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    relatorio = analisador.relatorio_geral_turma()
    return jsonify(relatorio)

@app.route('/api/info-trimestre')
@jwt_required()
def api_info_trimestre():
    """API para informações sobre o trimestre atual da turma"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    info_trimestre = analisador.detectar_trimestre_atual()
    return jsonify(info_trimestre)

@app.route('/api/grafico-dificuldade')
@jwt_required()
def api_grafico_dificuldade():
    """API para gráfico de disciplinas com dificuldade"""
    claims = get_jwt()
    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    dados = analisador.dados_para_graficos()

    # Criar gráfico de barras
    fig = go.Figure(data=[
        go.Bar(
            x=dados['disciplinas'],
            y=dados['percentual_dificuldade'],
            text=[f"{p:.1f}%" for p in dados['percentual_dificuldade']],
            textposition='auto',
            marker_color='rgba(99, 102, 241, 0.8)',
            name='% Alunos com Dificuldade'
        )
    ])

    fig.update_layout(
        title='Disciplinas com Maior Dificuldade',
        xaxis_title='Disciplinas',
        yaxis_title='Percentual de Alunos com Dificuldade (%)',
        template='plotly_white',
        height=400,
        font=dict(size=12),
        xaxis=dict(
            tickangle=-45,
            tickmode='linear',
            automargin=True
        ),
        margin=dict(l=50, r=50, t=80, b=120)
    )

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    response = app.response_class(
        response=graphJSON,
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/api/grafico-pizza-desempenho')
def api_grafico_pizza_desempenho():
    """API para gráfico de pizza do desempenho geral"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    alunos_dificuldade = analisador.identificar_alunos_dificuldade()
    alunos_destaque = analisador.alunos_destaque()

    total_avaliacoes = len(analisador.alunos) * len(analisador.disciplinas)
    com_dificuldade = sum(len(alunos) for alunos in alunos_dificuldade.values())
    com_destaque = sum(len(alunos) for alunos in alunos_destaque.values())
    intermediario = total_avaliacoes - com_dificuldade - com_destaque

    fig = go.Figure(data=[go.Pie(
        labels=['Com Dificuldade (< 6.0)', 'Intermediário (6.0-7.9)', 'Destaque (≥ 8.0)'],
        values=[com_dificuldade, intermediario, com_destaque],
        hole=.3,
        marker_colors=['#ef4444', '#f59e0b', '#10b981']
    )])

    fig.update_layout(
        title='Distribuição do Desempenho da Turma',
        template='plotly_white',
        height=400,
        font=dict(size=12)
    )

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    response = app.response_class(
        response=graphJSON,
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/api/dados-trimestres')
@jwt_required()
def api_dados_trimestres():
    """API para dados das disciplinas por trimestre (para filtros)"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    desempenho = analisador.desempenho_por_trimestre()

    # Preparar dados estruturados
    dados = {
        'trimestres': ['1º Trimestre', '2º Trimestre', '3º Trimestre'],
        'disciplinas': [],
        'cores': [
            '#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b',
            '#ef4444', '#8b5a2b', '#6b7280', '#ec4899', '#84cc16'
        ]
    }

    for i, (disciplina_completa, notas_trimestre) in enumerate(desempenho.items()):
        disciplina = disciplina_completa.split(' - ')[1] if ' - ' in disciplina_completa else disciplina_completa

        dados['disciplinas'].append({
            'nome': disciplina,
            'nome_completo': disciplina_completa,
            'cor': dados['cores'][i % len(dados['cores'])],
            'valores': [
                float(notas_trimestre['1º Trimestre']),
                float(notas_trimestre['2º Trimestre']),
                float(notas_trimestre['3º Trimestre'])
            ]
        })

    return jsonify(dados)

@app.route('/api/grafico-trimestres')
def api_grafico_trimestres():
    """API para gráfico de desempenho por trimestre (todas as disciplinas)"""
    claims = get_jwt()
    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    desempenho = analisador.desempenho_por_trimestre()

    # Preparar dados para o gráfico - Trimestres no eixo X, disciplinas como linhas
    trimestres = ['1º Trimestre', '2º Trimestre', '3º Trimestre']

    # Cores para as disciplinas
    cores = [
        '#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b',
        '#ef4444', '#8b5a2b', '#6b7280', '#ec4899', '#84cc16'
    ]

    fig = go.Figure()

    # Adicionar uma linha para cada disciplina
    for i, (disciplina_completa, notas_trimestre) in enumerate(desempenho.items()):
        disciplina = disciplina_completa.split(' - ')[1] if ' - ' in disciplina_completa else disciplina_completa

        # Valores das notas para cada trimestre
        valores = [
            notas_trimestre['1º Trimestre'],
            notas_trimestre['2º Trimestre'],
            notas_trimestre['3º Trimestre']
        ]

        fig.add_trace(go.Scatter(
            x=trimestres,
            y=valores,
            mode='lines+markers',
            name=disciplina,
            line=dict(color=cores[i % len(cores)], width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Trimestre: %{x}<br>' +
                         'Nota Média: %{y:.1f}<br>' +
                         '<extra></extra>'
        ))

    fig.update_layout(
        title='Evolução das Notas por Trimestre',
        xaxis_title='Trimestres',
        yaxis_title='Nota Média',
        template='plotly_white',
        height=400,
        font=dict(size=12),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    response = app.response_class(
        response=graphJSON,
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/api/ranking-disciplinas')
@jwt_required()
def api_ranking_disciplinas():
    """API para ranking de disciplinas"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    ranking = analisador.ranking_disciplinas_dificeis()

    dados = []
    for i, (disciplina, percentual, total) in enumerate(ranking, 1):
        nome_disciplina = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina
        dados.append({
            'posicao': i,
            'disciplina': nome_disciplina,
            'percentual_dificuldade': round(percentual, 1),
            'alunos_com_dificuldade': total,
            'total_alunos': len(analisador.alunos)
        })

    return jsonify(dados)

@app.route('/api/consulta-aluno')
def api_consulta_aluno():
    """API para consulta de aluno específico"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    nome_aluno = request.args.get('nome', '')
    disciplina_filtro = request.args.get('disciplina')

    if not nome_aluno:
        return jsonify({'erro': 'Nome do aluno não fornecido'})

    if nome_aluno not in analisador.alunos:
        return jsonify({'erro': 'Aluno não encontrado'})

    # Calcular dados do aluno
    dados_aluno = []
    for disciplina in analisador.disciplinas:
        # Se filtro de disciplina foi informado, aplicar
        if disciplina_filtro:
            nome_simples = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina
            if nome_simples.upper() != disciplina_filtro.upper():
                continue

        dados_disciplina = analisador.df[
            (analisador.df['Nome'] == nome_aluno) &
            (analisador.df['Disciplina'] == disciplina)
        ].iloc[0]

        media = analisador.calcular_media_aluno(nome_aluno, disciplina)
        nome_disciplina = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina

        # Validar notas antes de converter para float
        nota_1t = dados_disciplina['Nota 1º trimestre']
        nota_2t = dados_disciplina['Nota 2º trimestre']
        nota_3t = dados_disciplina['Nota 3º trimestre']

        # Converter para float ou None se for NaN/vazio
        nota_1t = float(nota_1t) if pd.notna(nota_1t) and nota_1t != '' and nota_1t != 0 else None
        nota_2t = float(nota_2t) if pd.notna(nota_2t) and nota_2t != '' and nota_2t != 0 else None
        nota_3t = float(nota_3t) if pd.notna(nota_3t) and nota_3t != '' and nota_3t != 0 else None

        dados_aluno.append({
            'disciplina': nome_disciplina,
            'nota_1t': nota_1t,
            'nota_2t': nota_2t,
            'nota_3t': nota_3t,
            'media': round(media, 2),
            'situacao': 'Aprovado' if media >= 6.0 else 'Recuperação' if media >= 4.0 else 'Reprovado'
        })

    # Calcular média geral do aluno
    media_geral = sum(item['media'] for item in dados_aluno) / len(dados_aluno)

    # Preparar dados para resposta
    dados_resposta = {
        'nome': nome_aluno,
        'media_geral': round(media_geral, 2),
        'disciplinas': dados_aluno,
        'total_disciplinas': len(dados_aluno),
        'aprovado_em': len([d for d in dados_aluno if d['situacao'] == 'Aprovado']),
        'recuperacao_em': len([d for d in dados_aluno if d['situacao'] == 'Recuperação']),
        'reprovado_em': len([d for d in dados_aluno if d['situacao'] == 'Reprovado'])
    }

    # Gerar relatório IA (com cache para evitar chamadas repetidas)
    try:
        relatorio_gemini = gerar_relatorio_aluno_gemini(dados_resposta)
        dados_resposta['relatorio_ia'] = relatorio_gemini
    except Exception as e:
        print(f"Erro ao gerar relatório IA: {e}")
        dados_resposta['relatorio_ia'] = f"Erro ao gerar relatório: {str(e)}"

    return jsonify(dados_resposta)

def gerar_relatorio_aluno_gemini(dados_aluno):
    """Gera relatório do aluno usando Gemini com cache"""

    nome = dados_aluno['nome']
    media_geral = dados_aluno['media_geral']
    aprovado = dados_aluno['aprovado_em']
    recuperacao = dados_aluno['recuperacao_em']
    reprovado = dados_aluno['reprovado_em']
    total = dados_aluno['total_disciplinas']

    # Criar hash baseado nos dados do aluno para cache
    cache_key = hashlib.md5(f"{nome}_{media_geral}_{aprovado}_{recuperacao}_{reprovado}".encode()).hexdigest()

    # Verificar cache
    if cache_key in gemini_cache:
        cached_data = gemini_cache[cache_key]
        if time.time() - cached_data['timestamp'] < CACHE_EXPIRATION:
            print(f"✅ Relatório recuperado do cache para: {nome}")
            return cached_data['response']
        else:
            del gemini_cache[cache_key]

    # Encontrar melhor e pior disciplina
    disciplinas = dados_aluno['disciplinas']
    if not disciplinas:
        return "Erro: Nenhuma disciplina encontrada para o aluno."

    melhor_disciplina = max(disciplinas, key=lambda x: x['media'] if x['media'] is not None else 0)
    pior_disciplina = min(disciplinas, key=lambda x: x['media'] if x['media'] is not None else 0)

    # Analisar evolução (comparar trimestres disponíveis)
    evolucoes = []
    for disc in disciplinas:
        # Verificar se há notas válidas para comparar
        nota_1t = disc.get('nota_1t')
        nota_2t = disc.get('nota_2t')
        nota_3t = disc.get('nota_3t')

        # Comparar 3º com 1º se ambos existirem
        if nota_3t is not None and nota_1t is not None:
            if nota_3t > nota_1t:
                evolucoes.append(f"📈 {disc['disciplina']}: melhorou de {nota_1t} para {nota_3t}")
            elif nota_3t < nota_1t:
                evolucoes.append(f"📉 {disc['disciplina']}: caiu de {nota_1t} para {nota_3t}")
        # Se não tem 3º, comparar 2º com 1º
        elif nota_2t is not None and nota_1t is not None:
            if nota_2t > nota_1t:
                evolucoes.append(f"📈 {disc['disciplina']}: melhorou de {nota_1t} para {nota_2t}")
            elif nota_2t < nota_1t:
                evolucoes.append(f"📉 {disc['disciplina']}: caiu de {nota_1t} para {nota_2t}")

    # Criar lista de disciplinas com status
    disciplinas_detalhes = []
    for disc in disciplinas:
        status_emoji = "✅" if disc['situacao'] == 'Aprovado' else "⚠️" if disc['situacao'] == 'Recuperação' else "❌"
        disciplinas_detalhes.append(f"{status_emoji} {disc['disciplina']}: {disc['media']} ({disc['situacao']})")

    prompt = f"""
Gere um relatório pedagógico CONCISO e OBJETIVO para:

ALUNO: {nome} | MÉDIA: {media_geral}
SITUAÇÃO: {aprovado} aprovado, {recuperacao} recuperação, {reprovado} reprovado
MELHOR: {melhor_disciplina['disciplina']} ({melhor_disciplina['media']})
PIOR: {pior_disciplina['disciplina']} ({pior_disciplina['media']})

EVOLUÇÃO: {chr(10).join(evolucoes[:2]) if evolucoes else "Desempenho estável"}

Gere um relatório de APENAS 2 parágrafos curtos:
1. Análise geral + pontos fortes/fracos
2. Recomendações práticas simples

Seja direto, objetivo e construtivo. Máximo 150 palavras.
"""

    try:
        # Usar o modelo Gemini já configurado globalmente
        print(f"🔄 Gerando relatório IA para: {nome}")
        gemini_model = genai.GenerativeModel('gemini-2.5-flash-lite')

        response = gemini_model.generate_content(prompt)
        resposta_texto = response.text.strip()

        # Armazenar no cache
        gemini_cache[cache_key] = {
            'response': resposta_texto,
            'timestamp': time.time()
        }
        print(f"✅ Relatório armazenado em cache")

        return resposta_texto
    except Exception as e:
        return f"Erro ao gerar relatório: {str(e)}"

@app.route('/api/lista-alunos')
def api_lista_alunos():
    """API para listar todos os alunos"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    return jsonify(sorted(analisador.alunos.tolist()))

@app.route('/api/consulta-disciplina')
@jwt_required()
def api_consulta_disciplina():
    """API para consulta de disciplina com todos os alunos"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    nome_disciplina = request.args.get('disciplina', '')

    if not nome_disciplina:
        return jsonify({'erro': 'Nome da disciplina não fornecido'})

    resultado = analisador.consulta_disciplina(nome_disciplina)
    return jsonify(resultado)

@app.route('/api/disciplina/resumo')
@jwt_required()
def api_resumo_disciplina():
    """Resumo estatístico de uma disciplina específica"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    nome_disciplina = request.args.get('disciplina', '')
    if not nome_disciplina:
        return jsonify({'erro': 'Nome da disciplina não fornecido'}), 400

    # Consolidar por nome simples da disciplina (ignorando prefixos)
    total_alunos = 0
    somatorio_medias = 0.0
    contagem_medias = 0
    aprovados = 0
    recuperacao = 0
    reprovados = 0

    for disciplina_completa in analisador.disciplinas:
        nome_simples = disciplina_completa.split(' - ')[1] if ' - ' in disciplina_completa else disciplina_completa
        if nome_simples.upper() != nome_disciplina.upper():
            continue

        stats = analisador.calcular_media_disciplina(disciplina_completa)
        total_alunos += stats.get('total_alunos', 0)
        media_disc = stats.get('media_geral_disciplina', 0)
        if media_disc is not None:
            somatorio_medias += float(media_disc)
            contagem_medias += 1

        # Classificar situação de cada aluno nesta disciplina
        df_disc = analisador.df[analisador.df['Disciplina'] == disciplina_completa]
        for _, row in df_disc.iterrows():
            # Coletar apenas notas válidas
            notas = []
            for col in ['Nota 1º trimestre', 'Nota 2º trimestre', 'Nota 3º trimestre']:
                if pd.notna(row[col]) and row[col] != '' and row[col] != 0:
                    notas.append(float(row[col]))

            if notas:  # Só calcular se houver notas válidas
                m = sum(notas) / len(notas)
                if m >= 6.0:
                    aprovados += 1
                elif m >= 4.0:
                    recuperacao += 1
                else:
                    reprovados += 1

    media_geral = round(somatorio_medias / contagem_medias, 2) if contagem_medias > 0 else 0
    taxa_aprovacao = round((aprovados / (aprovados + recuperacao + reprovados)) * 100, 1) if (aprovados + recuperacao + reprovados) > 0 else 0
    taxa_reprovacao = round((reprovados / (aprovados + recuperacao + reprovados)) * 100, 1) if (aprovados + recuperacao + reprovados) > 0 else 0

    return jsonify({
        'disciplina': nome_disciplina,
        'total_alunos': total_alunos,
        'media_geral': media_geral,
        'aprovados': aprovados,
        'recuperacao': recuperacao,
        'reprovados': reprovados,
        'taxa_aprovacao': taxa_aprovacao,
        'taxa_reprovacao': taxa_reprovacao
    })

@app.route('/api/disciplina/trimestres')
@jwt_required()
def api_trimestres_disciplina():
    """Retorna evolução por trimestre de uma disciplina específica"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    nome_disciplina = request.args.get('disciplina', '')
    if not nome_disciplina:
        return jsonify({'erro': 'Nome da disciplina não fornecido'}), 400

    current_user = get_jwt_identity()
    if not gerenciador_usuarios.verificar_acesso_disciplina(current_user, nome_disciplina):
        return jsonify({'erro': 'Acesso negado a esta disciplina'}), 403

    desempenho = analisador.desempenho_por_trimestre()
    trimestres = ['1º Trimestre', '2º Trimestre', '3º Trimestre']
    valores = None

    for disciplina_completa, notas_trimestre in desempenho.items():
        nome_simples = disciplina_completa.split(' - ')[1] if ' - ' in disciplina_completa else disciplina_completa
        if nome_simples.upper() == nome_disciplina.upper():
            valores = [
                float(notas_trimestre['1º Trimestre']),
                float(notas_trimestre['2º Trimestre']),
                float(notas_trimestre['3º Trimestre'])
            ]
            break

    if valores is None:
        return jsonify({'erro': 'Disciplina não encontrada'}), 404

    return jsonify({
        'trimestres': trimestres,
        'valores': valores
    })

@app.route('/api/lista-disciplinas')
@jwt_required()
def api_lista_disciplinas():
    """API para listar disciplinas"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    # Obter todas as disciplinas disponíveis
    todas_disciplinas = []
    for disciplina in analisador.disciplinas:
        nome_disciplina = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina
        todas_disciplinas.append(nome_disciplina)

    return jsonify(sorted(todas_disciplinas))

# APIs para Gerenciamento de Turmas (Coordenador)
@app.route('/api/turmas')
@jwt_required()
def api_listar_turmas():
    """API para listar todas as turmas com informações detalhadas"""
    claims = get_jwt()

    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403

    nomes_turmas = gerenciador_turmas.listar_turmas()

    # Obter informações detalhadas de cada turma
    turmas_detalhadas = []
    for nome in nomes_turmas:
        analisador_turma = gerenciador_turmas.obter_turma(nome)
        if analisador_turma:
            turmas_detalhadas.append({
                'nome': nome,
                'total_alunos': len(analisador_turma.alunos),
                'total_disciplinas': len(analisador_turma.disciplinas),
                'curso': gerenciador_turmas.extrair_curso_da_turma(nome)
            })

    return jsonify(turmas_detalhadas)

@app.route('/api/turmas/comparar')
@jwt_required()
def api_comparar_turmas():
    """API para comparar turmas"""
    claims = get_jwt()

    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403

    # filtros opcionais
    curso = request.args.get('curso')
    turmas = request.args.getlist('turma')  # pode vir múltiplos
    turmas_decod = [t for t in turmas]

    comparacao = gerenciador_turmas.comparar_turmas(curso=curso, nomes_turmas=turmas_decod if turmas_decod else None)
    return jsonify(comparacao)

@app.route('/api/turmas/estatisticas-gerais')
@jwt_required()
def api_estatisticas_gerais():
    """API para estatísticas gerais da escola"""
    claims = get_jwt()

    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403

    curso = request.args.get('curso')
    turmas = request.args.getlist('turma')
    estatisticas = gerenciador_turmas.obter_estatisticas_gerais(curso=curso, nomes_turmas=turmas if turmas else None)
    return jsonify(estatisticas)

@app.route('/api/turmas/ranking-disciplinas-geral')
@jwt_required()
def api_ranking_disciplinas_geral():
    """API para ranking de disciplinas considerando todas as turmas"""
    claims = get_jwt()

    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403

    curso = request.args.get('curso')
    turmas = request.args.getlist('turma')
    ranking = gerenciador_turmas.obter_ranking_disciplinas_geral(curso=curso, nomes_turmas=turmas if turmas else None)
    return jsonify(ranking)

@app.route('/api/turmas/adicionar', methods=['POST'])
@jwt_required()
def api_adicionar_turma():
    """API para adicionar nova turma"""
    claims = get_jwt()

    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403

    if 'arquivo' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

    arquivo = request.files['arquivo']
    nome_turma = request.form.get('nome_turma', '')

    if arquivo.filename == '' or not nome_turma:
        return jsonify({'erro': 'Nome da turma e arquivo são obrigatórios'}), 400

    if not arquivo.filename.endswith('.xlsx'):
        return jsonify({'erro': 'Apenas arquivos .xlsx são aceitos'}), 400

    sucesso = gerenciador_turmas.adicionar_turma(nome_turma, arquivo)

    if sucesso:
        return jsonify({'sucesso': True, 'mensagem': f'Turma {nome_turma} adicionada com sucesso'})
    else:
        return jsonify({'erro': 'Erro ao adicionar turma'}), 500

@app.route('/api/turmas/remover/<nome_turma>', methods=['DELETE'])
@jwt_required()
def api_remover_turma(nome_turma):
    """API para remover turma"""
    claims = get_jwt()

    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403

    sucesso = gerenciador_turmas.remover_turma(nome_turma)

    if sucesso:
        return jsonify({'sucesso': True, 'mensagem': f'Turma {nome_turma} removida com sucesso'})
    else:
        return jsonify({'erro': 'Erro ao remover turma'}), 500

@app.route('/api/turmas/atualizar/<nome_turma>', methods=['PUT'])
@jwt_required()
def api_atualizar_turma(nome_turma):
    """API para atualizar/substituir planilha de uma turma"""
    claims = get_jwt()

    if claims.get('role') != 'coordenador':
        return jsonify({'erro': 'Acesso negado'}), 403

    if 'arquivo' not in request.files:
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400

    arquivo = request.files['arquivo']

    if arquivo.filename == '':
        return jsonify({'erro': 'Arquivo inválido'}), 400

    if not arquivo.filename.endswith('.xlsx'):
        return jsonify({'erro': 'Apenas arquivos .xlsx são aceitos'}), 400

    # Remover turma antiga e adicionar nova
    gerenciador_turmas.remover_turma(nome_turma)
    sucesso = gerenciador_turmas.adicionar_turma(nome_turma, arquivo)

    if sucesso:
        return jsonify({'sucesso': True, 'mensagem': f'Turma {nome_turma} atualizada com sucesso'})
    else:
        return jsonify({'erro': 'Erro ao atualizar turma'}), 500

@app.route('/api/turmas/selecionar/<nome_turma>', methods=['POST'])
@jwt_required()
def api_selecionar_turma(nome_turma):
    """API para selecionar turma ativa na dashboard"""
    global analisador

    analisador = obter_analisador_turma(nome_turma)

    if analisador:
        return jsonify({
            'sucesso': True,
            'mensagem': f'Turma {nome_turma} selecionada',
            'turma': nome_turma
        })
    else:
        return jsonify({'erro': 'Turma não encontrada'}), 404


# ==================== ROTAS DE GERENCIAMENTO DE CONTAS ====================

@app.route('/gerenciar-contas')
@jwt_required()
def gerenciar_contas():
    """Página de gerenciamento de contas (apenas para admins)"""
    claims = get_jwt()

    # Verificar se é administrador
    if not claims.get('is_admin', False):
        return redirect(url_for('index'))

    return render_template('gerenciar_contas.html')


@app.route('/api/contas')
@jwt_required()
def api_listar_contas():
    """API para listar todas as contas (apenas para admins)"""
    claims = get_jwt()

    if not claims.get('is_admin', False):
        return jsonify({'erro': 'Acesso negado'}), 403

    contas = gerenciador_contas.listar_contas()

    return jsonify({
        'contas': contas,
        'total': gerenciador_contas.total_contas(),
        'total_admins': gerenciador_contas.total_admins()
    })


@app.route('/api/contas/<username>')
@jwt_required()
def api_obter_conta(username):
    """API para obter dados de uma conta específica (apenas para admins)"""
    claims = get_jwt()

    if not claims.get('is_admin', False):
        return jsonify({'erro': 'Acesso negado'}), 403

    conta = gerenciador_contas.obter_conta(username)

    if conta:
        return jsonify(conta)
    else:
        return jsonify({'erro': 'Conta não encontrada'}), 404


@app.route('/api/contas/criar', methods=['POST'])
@jwt_required()
def api_criar_conta():
    """API para criar nova conta (apenas para admins)"""
    claims = get_jwt()

    if not claims.get('is_admin', False):
        return jsonify({'erro': 'Acesso negado'}), 403

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    email = data.get('email')
    is_admin = data.get('is_admin', False)

    # Validações
    if not username or not password or not name or not email:
        return jsonify({'erro': 'Todos os campos são obrigatórios'}), 400

    if len(password) < 6:
        return jsonify({'erro': 'A senha deve ter no mínimo 6 caracteres'}), 400

    # Criar conta
    sucesso = gerenciador_contas.criar_conta(username, password, name, email, is_admin)

    if sucesso:
        return jsonify({
            'sucesso': True,
            'mensagem': f'Conta {username} criada com sucesso'
        })
    else:
        return jsonify({'erro': 'Usuário já existe'}), 400


@app.route('/api/contas/<username>', methods=['PUT'])
@jwt_required()
def api_atualizar_conta(username):
    """API para atualizar uma conta (apenas para admins)"""
    claims = get_jwt()

    if not claims.get('is_admin', False):
        return jsonify({'erro': 'Acesso negado'}), 403

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    is_admin = data.get('is_admin')

    # Validar senha se fornecida
    if password and len(password) < 6:
        return jsonify({'erro': 'A senha deve ter no mínimo 6 caracteres'}), 400

    # Atualizar conta
    sucesso = gerenciador_contas.atualizar_conta(username, name, email, password, is_admin)

    if sucesso:
        return jsonify({
            'sucesso': True,
            'mensagem': f'Conta {username} atualizada com sucesso'
        })
    else:
        return jsonify({'erro': 'Conta não encontrada'}), 404


@app.route('/api/contas/<username>', methods=['DELETE'])
@jwt_required()
def api_remover_conta(username):
    """API para remover uma conta (apenas para admins)"""
    claims = get_jwt()

    if not claims.get('is_admin', False):
        return jsonify({'erro': 'Acesso negado'}), 403

    # Não permitir remover a própria conta
    if username == get_jwt_identity():
        return jsonify({'erro': 'Você não pode remover sua própria conta'}), 400

    # Remover conta
    sucesso = gerenciador_contas.remover_conta(username)

    if sucesso:
        return jsonify({
            'sucesso': True,
            'mensagem': f'Conta {username} removida com sucesso'
        })
    else:
        return jsonify({'erro': 'Não é possível remover esta conta (última conta admin ou conta não encontrada)'}), 400


@app.route('/api/disciplinas-por-curso')
@jwt_required()
def api_disciplinas_por_curso():
    """Agrupa disciplinas por curso com base em TODAS as planilhas de turmas.
    Disciplinas presentes em TODOS os cursos detectados são movidas para 'Geral'.
    """
    # Normalizador de curso
    def norm_curso(nome: str) -> str:
        n = (nome or '').strip().lower()
        if 'agro' in n:
            return 'Agropecuária'
        if 'info' in n:
            return 'Informática'
        if 'eletro' in n or 'eletrot' in n:
            return 'Eletroeletrônica'
        return 'Geral'

    # Construir mapa curso -> {disciplinas}
    mapa: dict = {}
    cursos_detectados: set = set()

    # Percorre todas as turmas carregadas
    for nome_turma, anal in getattr(gerenciador_turmas, 'turmas', {}).items():
        try:
            curso_turma = norm_curso(gerenciador_turmas.extrair_curso_da_turma(nome_turma))
            cursos_detectados.add(curso_turma)
            for disciplina_completa in getattr(anal, 'disciplinas', []):
                if ' - ' in disciplina_completa:
                    curso_prefixo, nome_disc = disciplina_completa.split(' - ', 1)
                    curso = norm_curso(curso_prefixo)
                else:
                    # Sem prefixo: tratar como disciplina geral do EM
                    curso = 'Geral'
                    nome_disc = disciplina_completa

                mapa.setdefault(curso, set()).add(nome_disc.strip())
        except Exception:
            continue

    # Garantir chaves dos cursos conhecidos mesmo se vazias
    for c in ['Agropecuária', 'Informática', 'Eletroeletrônica']:
        mapa.setdefault(c, set())

    # Fallback: se não houver turmas carregadas, tentar deduzir a partir do analisador principal
    if not any(len(v) for v in mapa.values()) and analisador:
        for disciplina_completa in analisador.disciplinas:
            if ' - ' in disciplina_completa:
                curso_prefixo, nome_disc = disciplina_completa.split(' - ', 1)
                curso = norm_curso(curso_prefixo)
            else:
                curso = 'Geral'
                nome_disc = disciplina_completa
            mapa.setdefault(curso, set()).add(nome_disc.strip())

    # Recalcular 'Geral': tudo que foi classificado explicitamente como Geral
    disciplinas_gerais = mapa.get('Geral', set())

    # Além disso, se existir analisador com disciplinas sem prefixo, enriquecer com nomes comuns conhecidos
    if analisador:
        comuns_conhecidas = {'MATEMÁTICA','PORTUGUÊS','HISTÓRIA','GEOGRAFIA','INGLÊS','ARTES','EDUCAÇÃO FÍSICA','FILOSOFIA','SOCIOLOGIA','BIOLOGIA','QUÍMICA','FÍSICA'}
        for disciplina_completa in analisador.disciplinas:
            if ' - ' not in disciplina_completa:
                disciplinas_gerais.add(disciplina_completa.strip())
        # adicionar conhecidas
        disciplinas_gerais = disciplinas_gerais.union({n.title() for n in comuns_conhecidas})
    mapa['Geral'] = disciplinas_gerais

    # Converter sets em listas ordenadas (mantendo cursos mesmo se vazios para aparecerem no seletor)
    resposta = {c: sorted(list(ds)) for c, ds in mapa.items()}
    return jsonify(resposta)

@app.route('/api/alunos-atencao')
@jwt_required()
def api_alunos_atencao():
    """API para alunos que precisam de atenção especial"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    # Parâmetros opcionais
    min_reprovacoes = int(request.args.get('min_reprovacoes', 3))
    limite_nota = float(request.args.get('limite_nota', 6.0))
    disciplina = request.args.get('disciplina')

    # Caso disciplina seja informada, restringe à disciplina (para professor)
    if disciplina:
        current_user = get_jwt_identity()
        if not gerenciador_usuarios.verificar_acesso_disciplina(current_user, disciplina):
            return jsonify({'erro': 'Acesso negado a esta disciplina'}), 403

        # Construir lista de alunos com base apenas na disciplina informada
        df = analisador.df.copy()
        # Normalizar nomes
        def nome_simples(d):
            return d.split(' - ')[1] if ' - ' in d else d
        df = df[df['Disciplina'].apply(lambda d: nome_simples(d).upper() == disciplina.upper())]

        alunos_resposta = []
        for aluno in sorted(df['Nome'].unique().tolist()):
            registros = df[df['Nome'] == aluno]
            # Média da disciplina
            media = float((registros['Nota 1º trimestre'].astype(float) + registros['Nota 2º trimestre'].astype(float) + registros['Nota 3º trimestre'].astype(float)) / 3.0)
            media = round(media, 2)
            # Situação
            if media >= 6.0:
                situacao = 'Aprovado'
            elif media >= 4.0:
                situacao = 'Recuperação'
            else:
                situacao = 'Reprovado'

            alunos_resposta.append({
                'nome': aluno,
                'media_geral': media,
                'prioridade': 'Crítica' if situacao == 'Reprovado' else 'Alta' if situacao == 'Recuperação' else 'Média',
                'total_reprovacoes': 1 if situacao == 'Reprovado' else 0,
                'total_recuperacoes': 1 if situacao == 'Recuperação' else 0,
                'total_aprovacoes': 1 if situacao == 'Aprovado' else 0,
                'disciplinas_reprovado': [disciplina] if situacao == 'Reprovado' else [],
                'disciplinas_recuperacao': [disciplina] if situacao == 'Recuperação' else [],
                'disciplinas_aprovado': [disciplina] if situacao == 'Aprovado' else []
            })

        # Filtrar por limite_nota (alunos abaixo do limite)
        alunos_filtrados = [a for a in alunos_resposta if a['media_geral'] < limite_nota]

        return jsonify({
            'alunos': alunos_filtrados,
            'total': len(alunos_filtrados),
            'criterios': {
                'limite_nota': limite_nota,
                'disciplina': disciplina
            }
        })

    # Caso global (coordenador)
    alunos_atencao = analisador.alunos_precisam_atencao(min_reprovacoes, limite_nota)

    return jsonify({
        'alunos': alunos_atencao,
        'total': len(alunos_atencao),
        'criterios': {
            'min_reprovacoes': min_reprovacoes,
            'limite_nota': limite_nota
        }
    })

@app.route('/api/ranking-melhores-alunos')
@jwt_required()
def api_ranking_melhores_alunos():
    """API para ranking dos melhores alunos"""
    if not analisador:
        return jsonify({'erro': 'Analisador não disponível'})

    # Parâmetro opcional para limitar quantidade
    limite = int(request.args.get('limite', 10))
    disciplina = request.args.get('disciplina')

    # Ranking por disciplina (professor)
    if disciplina:
        current_user = get_jwt_identity()
        if not gerenciador_usuarios.verificar_acesso_disciplina(current_user, disciplina):
            return jsonify({'erro': 'Acesso negado a esta disciplina'}), 403

        # Calcular média da disciplina por aluno
        df = analisador.df.copy()
        def nome_simples(d):
            return d.split(' - ')[1] if ' - ' in d else d
        df = df[df['Disciplina'].apply(lambda d: nome_simples(d).upper() == disciplina.upper())]

        alunos = []
        for aluno in df['Nome'].unique().tolist():
            reg = df[df['Nome'] == aluno]
            media = float((reg['Nota 1º trimestre'].astype(float) + reg['Nota 2º trimestre'].astype(float) + reg['Nota 3º trimestre'].astype(float)) / 3.0)
            alunos.append((aluno, round(media, 2)))

        alunos.sort(key=lambda x: x[1], reverse=True)
        ranking = []
        for i, (nome, media) in enumerate(alunos[:limite], 1):
            ranking.append({
                'posicao': i,
                'nome': nome,
                'media_geral': media,
                'disciplinas_aprovado': 1 if media >= 6 else 0,
                'disciplinas_recuperacao': 1 if 4 <= media < 6 else 0,
                'disciplinas_reprovado': 1 if media < 4 else 0,
                'melhor_disciplina': disciplina,
                'melhor_nota': media,
                'pior_disciplina': disciplina,
                'pior_nota': media,
                'disciplinas': [{'nome': disciplina, 'media': media}]
            })

        return jsonify({
            'ranking': ranking,
            'total': len(ranking),
            'limite': limite,
            'disciplina': disciplina
        })

    # Global (coordenador)
    ranking = analisador.ranking_melhores_alunos(limite)
    return jsonify({
        'ranking': ranking,
        'total': len(ranking),
        'limite': limite
    })

if __name__ == '__main__':
    # Configurar para aceitar conexões externas na porta 8080
    app.run(host='127.0.0.1', port=8080, debug=True)
