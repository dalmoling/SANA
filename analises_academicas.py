#!/usr/bin/env python3
"""
Módulo de análises estatísticas para dados acadêmicos
Desenvolvido para TCC - Sistema de Análise de Notas Acadêmicas
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any

class AnalisadorAcademico:
    """Classe para análises estatísticas de dados acadêmicos"""
    
    def __init__(self, caminho_planilha: str = 'notas_certa.xlsx'):
        """Inicializa o analisador com a planilha de notas"""
        self.df = pd.read_excel(caminho_planilha, engine='openpyxl')
        self.disciplinas = self.df['Disciplina'].unique()
        self.alunos = self.df['Nome'].unique()
        
    def calcular_media_aluno(self, nome_aluno: str, disciplina: str = None) -> float:
        """Calcula a média de um aluno específico, ignorando valores vazios/NaN"""
        filtro = self.df['Nome'] == nome_aluno
        if disciplina:
            filtro = filtro & (self.df['Disciplina'] == disciplina)

        dados_aluno = self.df[filtro]
        if dados_aluno.empty:
            return 0.0

        # Coletar notas, ignorando NaN e valores vazios
        notas = []
        for col in ['Nota 1º trimestre', 'Nota 2º trimestre', 'Nota 3º trimestre']:
            valores = dados_aluno[col].values
            for v in valores:
                if pd.notna(v) and v != '' and v != 0:
                    notas.append(float(v))

        if not notas:
            return 0.0

        return np.mean(notas)
    
    def calcular_media_disciplina(self, disciplina: str) -> Dict[str, float]:
        """Calcula estatísticas de uma disciplina específica, ignorando valores vazios"""
        dados_disciplina = self.df[self.df['Disciplina'] == disciplina]

        # Calcular média de cada aluno na disciplina
        medias_alunos = []
        for _, row in dados_disciplina.iterrows():
            notas = []
            for col in ['Nota 1º trimestre', 'Nota 2º trimestre', 'Nota 3º trimestre']:
                if pd.notna(row[col]) and row[col] != '' and row[col] != 0:
                    notas.append(float(row[col]))

            if notas:
                medias_alunos.append(np.mean(notas))

        if not medias_alunos:
            return {
                'media_geral': 0.0,
                'mediana': 0.0,
                'desvio_padrao': 0.0,
                'nota_maxima': 0.0,
                'nota_minima': 0.0,
                'total_alunos': 0
            }

        return {
            'media_geral': np.mean(medias_alunos),
            'mediana': np.median(medias_alunos),
            'desvio_padrao': np.std(medias_alunos),
            'nota_maxima': np.max(medias_alunos),
            'nota_minima': np.min(medias_alunos),
            'total_alunos': len(medias_alunos)
        }
    
    def identificar_alunos_dificuldade(self, limite: float = 6.0) -> Dict[str, List[str]]:
        """Identifica alunos com dificuldades (média abaixo do limite)"""
        alunos_dificuldade = {}

        for disciplina in self.disciplinas:
            dados_disciplina = self.df[self.df['Disciplina'] == disciplina]
            alunos_baixo_rendimento = []

            for _, row in dados_disciplina.iterrows():
                # Coletar apenas notas válidas
                notas = []
                for col in ['Nota 1º trimestre', 'Nota 2º trimestre', 'Nota 3º trimestre']:
                    if pd.notna(row[col]) and row[col] != '' and row[col] != 0:
                        notas.append(float(row[col]))

                if notas:  # Só calcular se houver notas válidas
                    media = np.mean(notas)
                    if media < limite:
                        alunos_baixo_rendimento.append(row['Nome'])

            alunos_dificuldade[disciplina] = alunos_baixo_rendimento

        return alunos_dificuldade

    def alunos_destaque(self, limite: float = 8.0) -> Dict[str, List[str]]:
        """Identifica alunos com destaque (média acima do limite)"""
        alunos_destaque = {}

        for disciplina in self.disciplinas:
            dados_disciplina = self.df[self.df['Disciplina'] == disciplina]
            alunos_alto_rendimento = []

            for _, row in dados_disciplina.iterrows():
                # Coletar apenas notas válidas
                notas = []
                for col in ['Nota 1º trimestre', 'Nota 2º trimestre', 'Nota 3º trimestre']:
                    if pd.notna(row[col]) and row[col] != '' and row[col] != 0:
                        notas.append(float(row[col]))

                if notas:  # Só calcular se houver notas válidas
                    media = np.mean(notas)
                    if media >= limite:
                        alunos_alto_rendimento.append(row['Nome'])

            alunos_destaque[disciplina] = alunos_alto_rendimento

        return alunos_destaque

    def ranking_disciplinas_dificeis(self) -> List[Tuple[str, float, int]]:
        """Retorna ranking das disciplinas mais difíceis (maior % de alunos com dificuldade)"""
        ranking = []
        alunos_dificuldade = self.identificar_alunos_dificuldade()
        
        for disciplina in self.disciplinas:
            total_alunos = len(self.df[self.df['Disciplina'] == disciplina])
            alunos_com_dificuldade = len(alunos_dificuldade[disciplina])
            percentual = (alunos_com_dificuldade / total_alunos) * 100
            
            ranking.append((disciplina, percentual, alunos_com_dificuldade))
        
        # Ordenar por percentual decrescente
        ranking.sort(key=lambda x: x[1], reverse=True)
        return ranking
    
    def desempenho_por_trimestre(self) -> Dict[str, Dict[str, float]]:
        """Analisa o desempenho médio por trimestre, ignorando valores vazios"""
        resultado = {}

        for disciplina in self.disciplinas:
            dados_disciplina = self.df[self.df['Disciplina'] == disciplina]

            # Calcular médias ignorando NaN e valores vazios
            media_1tri = dados_disciplina['Nota 1º trimestre'].replace('', np.nan).replace(0, np.nan).astype(float).mean()
            media_2tri = dados_disciplina['Nota 2º trimestre'].replace('', np.nan).replace(0, np.nan).astype(float).mean()
            media_3tri = dados_disciplina['Nota 3º trimestre'].replace('', np.nan).replace(0, np.nan).astype(float).mean()

            resultado[disciplina] = {
                '1º Trimestre': media_1tri if pd.notna(media_1tri) else 0.0,
                '2º Trimestre': media_2tri if pd.notna(media_2tri) else 0.0,
                '3º Trimestre': media_3tri if pd.notna(media_3tri) else 0.0
            }

        return resultado
    

    
    def relatorio_geral_turma(self) -> Dict[str, Any]:
        """Gera relatório geral da turma"""
        total_alunos = len(self.alunos)
        total_disciplinas = len(self.disciplinas)
        
        # Calcular média geral da turma
        todas_medias = []
        for aluno in self.alunos:
            for disciplina in self.disciplinas:
                media_aluno_disciplina = self.calcular_media_aluno(aluno, disciplina)
                todas_medias.append(media_aluno_disciplina)
        
        alunos_dificuldade = self.identificar_alunos_dificuldade()
        total_com_dificuldade = sum(len(alunos) for alunos in alunos_dificuldade.values())
        
        return {
            'total_alunos': total_alunos,
            'total_disciplinas': total_disciplinas,
            'media_geral_turma': np.mean(todas_medias),
            'total_avaliacoes_com_dificuldade': total_com_dificuldade,
            'percentual_dificuldade': (total_com_dificuldade / (total_alunos * total_disciplinas)) * 100,
            'disciplina_mais_dificil': self.ranking_disciplinas_dificeis()[0][0],
            'disciplina_mais_facil': self.ranking_disciplinas_dificeis()[-1][0]
        }
    
    def alunos_precisam_atencao(self, min_reprovacoes: int = 3, limite_nota: float = 6.0) -> List[Dict[str, Any]]:
        """Identifica alunos que precisam de atenção especial (reprovados em múltiplas disciplinas)"""
        alunos_atencao = []

        for aluno in self.alunos:
            disciplinas_reprovado = []
            disciplinas_recuperacao = []
            disciplinas_aprovado = []
            total_media = 0

            for disciplina in self.disciplinas:
                media = self.calcular_media_aluno(aluno, disciplina)
                total_media += media

                nome_disciplina = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina

                if media < 4.0:
                    disciplinas_reprovado.append(nome_disciplina)
                elif media < limite_nota:
                    disciplinas_recuperacao.append(nome_disciplina)
                else:
                    disciplinas_aprovado.append(nome_disciplina)

            media_geral = total_media / len(self.disciplinas)
            total_problemas = len(disciplinas_reprovado) + len(disciplinas_recuperacao)

            # Critérios para atenção especial
            if (len(disciplinas_reprovado) >= min_reprovacoes or
                total_problemas >= min_reprovacoes or
                media_geral < 5.0):

                # Determinar nível de prioridade
                if len(disciplinas_reprovado) >= 5 or media_geral < 4.0:
                    prioridade = "Crítica"
                elif len(disciplinas_reprovado) >= 3 or media_geral < 5.0:
                    prioridade = "Alta"
                else:
                    prioridade = "Média"

                alunos_atencao.append({
                    'nome': aluno,
                    'media_geral': round(media_geral, 2),
                    'disciplinas_reprovado': disciplinas_reprovado,
                    'disciplinas_recuperacao': disciplinas_recuperacao,
                    'disciplinas_aprovado': disciplinas_aprovado,
                    'total_reprovacoes': len(disciplinas_reprovado),
                    'total_recuperacoes': len(disciplinas_recuperacao),
                    'total_aprovacoes': len(disciplinas_aprovado),
                    'total_problemas': total_problemas,
                    'prioridade': prioridade
                })

        # Ordenar por prioridade, depois por nome (ordem alfabética/numérica)
        prioridade_ordem = {"Crítica": 0, "Alta": 1, "Média": 2}
        alunos_atencao.sort(key=lambda x: (prioridade_ordem[x['prioridade']], x['nome']))

        return alunos_atencao

    def ranking_melhores_alunos(self, limite: int = 10) -> List[Dict[str, Any]]:
        """Gera ranking dos alunos com melhores médias gerais"""
        ranking_alunos = []

        for aluno in self.alunos:
            disciplinas_info = []
            total_media = 0
            disciplinas_aprovado = 0
            disciplinas_recuperacao = 0
            disciplinas_reprovado = 0

            for disciplina in self.disciplinas:
                media = self.calcular_media_aluno(aluno, disciplina)
                total_media += media

                nome_disciplina = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina

                disciplinas_info.append({
                    'nome': nome_disciplina,
                    'media': round(media, 2)
                })

                # Classificar desempenho
                if media >= 6.0:
                    disciplinas_aprovado += 1
                elif media >= 4.0:
                    disciplinas_recuperacao += 1
                else:
                    disciplinas_reprovado += 1

            media_geral = total_media / len(self.disciplinas)

            # Ordenar disciplinas por média (melhores primeiro)
            disciplinas_info.sort(key=lambda x: x['media'], reverse=True)

            ranking_alunos.append({
                'nome': aluno,
                'media_geral': round(media_geral, 2),
                'disciplinas': disciplinas_info,
                'total_disciplinas': len(self.disciplinas),
                'disciplinas_aprovado': disciplinas_aprovado,
                'disciplinas_recuperacao': disciplinas_recuperacao,
                'disciplinas_reprovado': disciplinas_reprovado,
                'melhor_disciplina': disciplinas_info[0]['nome'] if disciplinas_info else None,
                'melhor_nota': disciplinas_info[0]['media'] if disciplinas_info else 0,
                'pior_disciplina': disciplinas_info[-1]['nome'] if disciplinas_info else None,
                'pior_nota': disciplinas_info[-1]['media'] if disciplinas_info else 0
            })

        # Ordenar por média geral (melhores primeiro)
        ranking_alunos.sort(key=lambda x: x['media_geral'], reverse=True)

        # Adicionar posição no ranking
        for i, aluno in enumerate(ranking_alunos[:limite], 1):
            aluno['posicao'] = i

        return ranking_alunos[:limite]

    def consulta_disciplina(self, nome_disciplina: str) -> Dict[str, Any]:
        """Consulta detalhada de uma disciplina com todos os alunos"""

        # Encontrar a disciplina exata
        disciplina_encontrada = None
        for disciplina in self.disciplinas:
            nome_disc = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina
            if nome_disc.upper() == nome_disciplina.upper():
                disciplina_encontrada = disciplina
                break

        if not disciplina_encontrada:
            return {'erro': 'Disciplina não encontrada'}

        # Coletar dados de todos os alunos nesta disciplina
        alunos_disciplina = []
        medias_disciplina = []

        for aluno in self.alunos:
            media = self.calcular_media_aluno(aluno, disciplina_encontrada)
            medias_disciplina.append(media)

            # Buscar notas por trimestre
            notas_trimestres = []
            for trimestre in ['1º trimestre', '2º trimestre', '3º trimestre']:
                col_nota = f'Nota {trimestre}'
                if col_nota in self.df.columns:
                    filtro = (self.df['Nome'] == aluno) & (self.df['Disciplina'] == disciplina_encontrada)
                    if len(self.df[filtro]) > 0:
                        nota = self.df[filtro][col_nota].iloc[0]
                        # Validar se a nota é válida
                        if pd.notna(nota) and nota != '' and nota != 0:
                            notas_trimestres.append(float(nota))
                        else:
                            notas_trimestres.append(None)  # Usar None para indicar ausência de nota
                    else:
                        notas_trimestres.append(None)
                else:
                    notas_trimestres.append(None)

            # Determinar status
            if media >= 6.0:
                status = 'Aprovado'
                cor = 'green'
            elif media >= 4.0:
                status = 'Recuperação'
                cor = 'yellow'
            else:
                status = 'Reprovado'
                cor = 'red'

            alunos_disciplina.append({
                'nome': aluno,
                'media': round(media, 2),
                'notas_trimestres': notas_trimestres,
                'status': status,
                'cor': cor
            })

        # Ordenar alunos por média (melhores primeiro)
        alunos_disciplina.sort(key=lambda x: x['media'], reverse=True)

        # Calcular estatísticas da disciplina
        media_geral_disciplina = sum(medias_disciplina) / len(medias_disciplina) if medias_disciplina else 0
        aprovados = sum(1 for a in alunos_disciplina if a['status'] == 'Aprovado')
        recuperacao = sum(1 for a in alunos_disciplina if a['status'] == 'Recuperação')
        reprovados = sum(1 for a in alunos_disciplina if a['status'] == 'Reprovado')

        # Melhor e pior aluno
        melhor_aluno = alunos_disciplina[0] if alunos_disciplina else None
        pior_aluno = alunos_disciplina[-1] if alunos_disciplina else None

        return {
            'disciplina': nome_disciplina,
            'disciplina_completa': disciplina_encontrada,
            'media_geral': round(media_geral_disciplina, 2),
            'total_alunos': len(alunos_disciplina),
            'aprovados': aprovados,
            'recuperacao': recuperacao,
            'reprovados': reprovados,
            'melhor_aluno': melhor_aluno,
            'pior_aluno': pior_aluno,
            'alunos': alunos_disciplina
        }

    def detectar_trimestre_atual(self) -> Dict[str, Any]:
        """Detecta qual trimestre está em andamento baseado nas notas disponíveis"""
        # Contar quantas notas válidas existem em cada trimestre
        total_registros = len(self.df)

        notas_1tri = 0
        notas_2tri = 0
        notas_3tri = 0

        for _, row in self.df.iterrows():
            if pd.notna(row['Nota 1º trimestre']) and row['Nota 1º trimestre'] != '' and row['Nota 1º trimestre'] != 0:
                notas_1tri += 1
            if pd.notna(row['Nota 2º trimestre']) and row['Nota 2º trimestre'] != '' and row['Nota 2º trimestre'] != 0:
                notas_2tri += 1
            if pd.notna(row['Nota 3º trimestre']) and row['Nota 3º trimestre'] != '' and row['Nota 3º trimestre'] != 0:
                notas_3tri += 1

        # Calcular percentuais
        perc_1tri = (notas_1tri / total_registros * 100) if total_registros > 0 else 0
        perc_2tri = (notas_2tri / total_registros * 100) if total_registros > 0 else 0
        perc_3tri = (notas_3tri / total_registros * 100) if total_registros > 0 else 0

        # Determinar trimestre atual (considera completo se > 80% preenchido)
        trimestre_atual = 1
        trimestres_completos = []

        if perc_1tri > 80:
            trimestres_completos.append(1)
        if perc_2tri > 80:
            trimestres_completos.append(2)
        if perc_3tri > 80:
            trimestres_completos.append(3)

        # Determinar trimestre atual baseado nos trimestres completos
        if 3 in trimestres_completos:
            # Todos os 3 trimestres completos
            trimestre_atual = 3
            status = "Ano Letivo Completo"
        elif 2 in trimestres_completos:
            # Apenas 1º e 2º completos (está no 2º trimestre)
            trimestre_atual = 2
            status = "2º Trimestre em Andamento"
        elif 1 in trimestres_completos:
            # Apenas 1º completo (está no 1º trimestre)
            trimestre_atual = 1
            status = "1º Trimestre em Andamento"
        else:
            # Nenhum trimestre completo
            trimestre_atual = 1
            status = "1º Trimestre em Andamento"

        return {
            'trimestre_atual': trimestre_atual,
            'status': status,
            'trimestres_completos': trimestres_completos,
            'percentuais': {
                '1º Trimestre': round(perc_1tri, 1),
                '2º Trimestre': round(perc_2tri, 1),
                '3º Trimestre': round(perc_3tri, 1)
            }
        }

    def dados_para_graficos(self) -> Dict[str, Any]:
        """Prepara dados estruturados para geração de gráficos"""
        ranking_dificuldade = self.ranking_disciplinas_dificeis()
        desempenho_trimestres = self.desempenho_por_trimestre()

        return {
            'disciplinas': [item[0].split(' - ')[1] if ' - ' in item[0] else item[0] for item in ranking_dificuldade],
            'percentual_dificuldade': [item[1] for item in ranking_dificuldade],
            'alunos_com_dificuldade': [item[2] for item in ranking_dificuldade],
            'desempenho_trimestres': desempenho_trimestres,
            'total_alunos': len(self.alunos)
        }

# Função de conveniência para uso direto
def analisar_dados_academicos(caminho_planilha: str = 'notas_certa.xlsx') -> AnalisadorAcademico:
    """Função de conveniência para criar um analisador"""
    return AnalisadorAcademico(caminho_planilha)

if __name__ == "__main__":
    # Exemplo de uso
    analisador = AnalisadorAcademico()
    
    print("=== RELATÓRIO GERAL DA TURMA ===")
    relatorio = analisador.relatorio_geral_turma()
    for chave, valor in relatorio.items():
        print(f"{chave}: {valor}")
    
    print("\n=== RANKING DISCIPLINAS MAIS DIFÍCEIS ===")
    ranking = analisador.ranking_disciplinas_dificeis()
    for i, (disciplina, percentual, total) in enumerate(ranking[:5], 1):
        nome_disciplina = disciplina.split(' - ')[1] if ' - ' in disciplina else disciplina
        print(f"{i}. {nome_disciplina}: {percentual:.1f}% ({total} alunos)")
