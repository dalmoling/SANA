import os
import pandas as pd
from typing import Dict, List, Any, Optional
from analises_academicas import AnalisadorAcademico

class GerenciadorTurmas:
    """Gerencia múltiplas turmas e permite comparações entre elas"""
    
    def __init__(self, diretorio_turmas: str = "turmas"):
        self.diretorio_turmas = diretorio_turmas
        self.turmas = {}
        self.criar_diretorio_se_nao_existe()
        self.carregar_turmas()
    
    def criar_diretorio_se_nao_existe(self):
        """Cria o diretório de turmas se não existir"""
        if not os.path.exists(self.diretorio_turmas):
            os.makedirs(self.diretorio_turmas)
    
    def extrair_curso_da_turma(self, nome_turma: str) -> str:
        """Extrai o nome do curso a partir do nome da turma"""
        nome_turma = nome_turma.lower()
        
        # Mapeamento de padrões para cursos
        if 'agro' in nome_turma or 'agropecuaria' in nome_turma:
            return 'Agropecuária'
        elif 'info' in nome_turma or 'informatica' in nome_turma:
            return 'Informática'
        elif 'eletro' in nome_turma or 'eletrotecnica' in nome_turma:
            return 'Eletrotécnica'
        elif 'principal' in nome_turma:
            return 'Geral'
        else:
            # Tentar extrair a primeira palavra como curso
            primeira_palavra = nome_turma.split()[0] if nome_turma.split() else 'Outros'
            return primeira_palavra.title()
    
    def listar_cursos(self) -> List[str]:
        """Retorna lista de cursos disponíveis"""
        cursos = set()
        for nome_turma in self.turmas.keys():
            curso = self.extrair_curso_da_turma(nome_turma)
            cursos.add(curso)
        return sorted(list(cursos))
    
    def listar_turmas_por_curso(self, curso: str = None) -> Dict[str, List[str]]:
        """Retorna turmas agrupadas por curso ou de um curso específico"""
        turmas_por_curso = {}
        
        for nome_turma in self.turmas.keys():
            curso_turma = self.extrair_curso_da_turma(nome_turma)
            
            if curso and curso_turma != curso:
                continue
                
            if curso_turma not in turmas_por_curso:
                turmas_por_curso[curso_turma] = []
            turmas_por_curso[curso_turma].append(nome_turma)
        
        return turmas_por_curso
    
    def obter_arquivo_turma(self, nome_turma: str) -> Optional[str]:
        """Retorna o caminho do arquivo de uma turma específica"""
        # Normalizar nome da turma
        nome_arquivo = nome_turma.lower().replace(' ', '_') + '.xlsx'
        caminho_arquivo = os.path.join(self.diretorio_turmas, nome_arquivo)

        if os.path.exists(caminho_arquivo):
            return caminho_arquivo

        return None

    def carregar_turmas(self):
        """Carrega todas as turmas disponíveis"""
        self.turmas = {}

        # Carregar turmas do diretório
        if os.path.exists(self.diretorio_turmas):
            for arquivo in os.listdir(self.diretorio_turmas):
                if arquivo.endswith('.xlsx'):
                    nome_turma = arquivo.replace('.xlsx', '').replace('_', ' ').title()
                    caminho_arquivo = os.path.join(self.diretorio_turmas, arquivo)
                    try:
                        self.turmas[nome_turma] = AnalisadorAcademico(caminho_arquivo)
                    except Exception as e:
                        print(f"Erro ao carregar turma {nome_turma}: {e}")
    
    def listar_turmas(self) -> List[str]:
        """Retorna lista de nomes das turmas"""
        return list(self.turmas.keys())
    
    def obter_turma(self, nome_turma: str) -> AnalisadorAcademico:
        """Retorna o analisador de uma turma específica"""
        return self.turmas.get(nome_turma)
    
    def adicionar_turma(self, nome_turma: str, arquivo_excel) -> bool:
        """Adiciona uma nova turma a partir de um arquivo Excel"""
        try:
            # Sanitizar nome do arquivo
            nome_arquivo = nome_turma.lower().replace(' ', '_') + '.xlsx'
            caminho_arquivo = os.path.join(self.diretorio_turmas, nome_arquivo)
            
            # Salvar arquivo
            arquivo_excel.save(caminho_arquivo)
            
            # Carregar analisador
            self.turmas[nome_turma] = AnalisadorAcademico(caminho_arquivo)
            
            return True
        except Exception as e:
            print(f"Erro ao adicionar turma {nome_turma}: {e}")
            return False
    
    def remover_turma(self, nome_turma: str) -> bool:
        """Remove uma turma"""
        try:
            if nome_turma in self.turmas:
                # Remover do dicionário
                del self.turmas[nome_turma]
                
                # Remover arquivo se existir
                nome_arquivo = nome_turma.lower().replace(' ', '_') + '.xlsx'
                caminho_arquivo = os.path.join(self.diretorio_turmas, nome_arquivo)
                if os.path.exists(caminho_arquivo):
                    os.remove(caminho_arquivo)
                
                return True
        except Exception as e:
            print(f"Erro ao remover turma {nome_turma}: {e}")
        return False
    
    def comparar_turmas(self, curso: str = None, nomes_turmas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compara estatísticas entre turmas.
        Pode filtrar por curso e/ou por lista específica de nomes de turmas.
        """
        if not self.turmas:
            return {'erro': 'Nenhuma turma disponível'}
        
        # Filtrar turmas por curso e/ou nomes se especificado
        turmas_filtradas = {}
        base = self.turmas
        if curso:
            base = {n:a for n,a in base.items() if self.extrair_curso_da_turma(n) == curso}
        if nomes_turmas:
            nomes_set = set(nomes_turmas)
            base = {n:a for n,a in base.items() if n in nomes_set}
        turmas_filtradas = base
        
        if not turmas_filtradas:
            return {'erro': f'Nenhuma turma encontrada para o curso {curso}'}
        
        comparacao = {
            'turmas': [],
            'total_turmas': len(turmas_filtradas),
            'melhor_turma': None,
            'pior_turma': None,
            'curso_filtrado': curso
        }
        
        medias_turmas = []
        
        for nome_turma, analisador in turmas_filtradas.items():
            try:
                relatorio = analisador.relatorio_geral_turma()

                # Detectar trimestre atual
                info_trimestre = analisador.detectar_trimestre_atual()

                # Calcular aprovados/reprovados por disciplina
                aprovados = 0
                recuperacao = 0
                reprovados = 0

                for aluno in analisador.alunos:
                    # Contar quantas disciplinas o aluno está reprovado
                    disciplinas_reprovadas = 0
                    disciplinas_recuperacao = 0
                    disciplinas_aprovadas = 0

                    for disciplina in analisador.disciplinas:
                        media_disciplina = analisador.calcular_media_aluno(aluno, disciplina)
                        if media_disciplina >= 6.0:
                            disciplinas_aprovadas += 1
                        elif media_disciplina >= 4.0:
                            disciplinas_recuperacao += 1
                        elif media_disciplina > 0:  # Só conta se tiver nota
                            disciplinas_reprovadas += 1

                    # Classificar o aluno baseado no pior cenário
                    if disciplinas_reprovadas > 0:
                        reprovados += 1
                    elif disciplinas_recuperacao > 0:
                        recuperacao += 1
                    else:
                        aprovados += 1

                turma_info = {
                    'nome': nome_turma,
                    'curso': self.extrair_curso_da_turma(nome_turma),
                    'total_alunos': len(analisador.alunos),
                    'total_disciplinas': len(analisador.disciplinas),
                    'media_geral': relatorio.get('media_geral_turma', 0),
                    'aprovados': aprovados,
                    'recuperacao': recuperacao,
                    'reprovados': reprovados,
                    'taxa_aprovacao': round((aprovados / len(analisador.alunos)) * 100, 1) if len(analisador.alunos) > 0 else 0,
                    'trimestre_atual': info_trimestre.get('trimestre_atual', 1),
                    'status_trimestre': info_trimestre.get('status', '1º Trimestre'),
                    'trimestres_completos': info_trimestre.get('trimestres_completos', [])
                }

                comparacao['turmas'].append(turma_info)
                medias_turmas.append((nome_turma, turma_info['media_geral']))

            except Exception as e:
                print(f"Erro ao processar turma {nome_turma}: {e}")
        
        # Ordenar turmas por média geral
        comparacao['turmas'].sort(key=lambda x: x['media_geral'], reverse=True)
        
        # Identificar melhor e pior turma
        if medias_turmas:
            medias_turmas.sort(key=lambda x: x[1], reverse=True)
            comparacao['melhor_turma'] = medias_turmas[0][0]
            comparacao['pior_turma'] = medias_turmas[-1][0]
        
        return comparacao
    
    def obter_ranking_disciplinas_geral(self, curso: str = None, nomes_turmas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Ranking de disciplinas considerando turmas.
        Pode filtrar por curso e/ou por lista específica de nomes de turmas.
        """
        disciplinas_consolidadas = {}
        
        # Filtrar turmas por curso e/ou nomes
        base = self.turmas
        if curso:
            base = {n:a for n,a in base.items() if self.extrair_curso_da_turma(n) == curso}
        if nomes_turmas:
            nomes_set = set(nomes_turmas)
            base = {n:a for n,a in base.items() if n in nomes_set}
        turmas_filtradas = base
        
        for nome_turma, analisador in turmas_filtradas.items():
            try:
                # CORREÇÃO: Usar o método correto
                ranking_dificeis = analisador.ranking_disciplinas_dificeis()
                
                for disciplina_completa, percentual, total_com_dificuldade in ranking_dificeis:
                    # Extrair nome da disciplina
                    nome_disc = disciplina_completa.split(' - ')[1] if ' - ' in disciplina_completa else disciplina_completa
                    
                    if nome_disc not in disciplinas_consolidadas:
                        disciplinas_consolidadas[nome_disc] = {
                            'disciplina': nome_disc,
                            'percentuais_dificuldade': [],
                            'total_alunos': 0,
                            'total_com_dificuldade': 0
                        }
                    
                    # Calcular estatísticas da disciplina
                    stats_disciplina = analisador.calcular_media_disciplina(disciplina_completa)
                    total_alunos_disciplina = stats_disciplina['total_alunos']
                    
                    disciplinas_consolidadas[nome_disc]['percentuais_dificuldade'].append(percentual)
                    disciplinas_consolidadas[nome_disc]['total_alunos'] += total_alunos_disciplina
                    disciplinas_consolidadas[nome_disc]['total_com_dificuldade'] += total_com_dificuldade
                    
            except Exception as e:
                print(f"Erro ao processar ranking da turma {nome_turma}: {e}")
        
        # Calcular médias consolidadas
        ranking_geral = []
        for nome_disc, dados in disciplinas_consolidadas.items():
            percentual_medio = sum(dados['percentuais_dificuldade']) / len(dados['percentuais_dificuldade']) if dados['percentuais_dificuldade'] else 0
            
            ranking_geral.append({
                'disciplina': nome_disc,
                'percentual_dificuldade': round(percentual_medio, 1),
                'total_alunos': dados['total_alunos'],
                'total_com_dificuldade': dados['total_com_dificuldade']
            })
        
        # Ordenar por percentual de dificuldade (maior dificuldade primeiro)
        ranking_geral.sort(key=lambda x: x['percentual_dificuldade'], reverse=True)
        
        return {
            'disciplinas': ranking_geral,
            'total_disciplinas': len(ranking_geral),
            'turmas_analisadas': len(turmas_filtradas),
            'curso_filtrado': curso
        }
    
    def obter_estatisticas_gerais(self, curso: str = None, nomes_turmas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Estatísticas gerais de turmas.
        Pode filtrar por curso e/ou por lista específica de nomes de turmas.
        """
        # Filtrar turmas por curso e/ou nomes
        base = self.turmas
        if curso:
            base = {n:a for n,a in base.items() if self.extrair_curso_da_turma(n) == curso}
        if nomes_turmas:
            nomes_set = set(nomes_turmas)
            base = {n:a for n,a in base.items() if n in nomes_set}
        turmas_filtradas = base
            
        if not turmas_filtradas:
            return {'erro': f'Nenhuma turma encontrada para o curso {curso}' if curso else 'Nenhuma turma disponível'}
        
        total_alunos = 0
        total_aprovados = 0
        total_recuperacao = 0
        total_reprovados = 0
        medias_gerais = []
        
        for analisador in turmas_filtradas.values():
            try:
                relatorio = analisador.relatorio_geral_turma()
                total_alunos += len(analisador.alunos)
                medias_gerais.append(relatorio.get('media_geral_turma', 0))

                # Calcular aprovados/reprovados por disciplina
                for aluno in analisador.alunos:
                    # Contar quantas disciplinas o aluno está reprovado
                    disciplinas_reprovadas = 0
                    disciplinas_recuperacao = 0

                    for disciplina in analisador.disciplinas:
                        media_disciplina = analisador.calcular_media_aluno(aluno, disciplina)
                        if media_disciplina >= 6.0:
                            pass  # Aprovado nesta disciplina
                        elif media_disciplina >= 4.0:
                            disciplinas_recuperacao += 1
                        elif media_disciplina > 0:  # Só conta se tiver nota
                            disciplinas_reprovadas += 1

                    # Classificar o aluno baseado no pior cenário
                    if disciplinas_reprovadas > 0:
                        total_reprovados += 1
                    elif disciplinas_recuperacao > 0:
                        total_recuperacao += 1
                    else:
                        total_aprovados += 1

            except Exception as e:
                print(f"Erro ao processar estatísticas: {e}")
        
        media_geral_escola = sum(medias_gerais) / len(medias_gerais) if medias_gerais else 0
        
        return {
            'total_turmas': len(turmas_filtradas),
            'total_alunos': total_alunos,
            'total_aprovados': total_aprovados,
            'total_recuperacao': total_recuperacao,
            'total_reprovados': total_reprovados,
            'media_geral_escola': round(media_geral_escola, 2),
            'taxa_aprovacao_escola': round((total_aprovados / total_alunos) * 100, 1) if total_alunos > 0 else 0,
            'curso_filtrado': curso
        }
