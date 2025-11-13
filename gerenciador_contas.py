#!/usr/bin/env python3
"""
Gerenciador de Contas de Coordenadores
Desenvolvido para TCC - Sistema de Análise de Notas Acadêmicas
"""

import json
import hashlib
import os
from typing import Dict, List, Optional
from datetime import datetime

class GerenciadorContas:
    """Gerencia contas de coordenadores do sistema"""
    
    def __init__(self, arquivo_contas: str = 'contas_coordenadores.json'):
        self.arquivo_contas = arquivo_contas
        self.contas = {}
        self.carregar_contas()
    
    def carregar_contas(self):
        """Carrega contas do arquivo JSON"""
        if os.path.exists(self.arquivo_contas):
            try:
                with open(self.arquivo_contas, 'r', encoding='utf-8') as f:
                    self.contas = json.load(f)
            except Exception as e:
                print(f"Erro ao carregar contas: {e}")
                self.contas = {}
        else:
            # Criar conta padrão se não existir
            self.contas = {
                'coordenador': {
                    'password_hash': hashlib.sha256('123'.encode()).hexdigest(),
                    'role': 'coordenador',
                    'name': 'Coordenador Principal',
                    'email': 'coordenador@ifc.edu.br',
                    'created_at': datetime.now().isoformat(),
                    'is_admin': True
                }
            }
            self.salvar_contas()
    
    def salvar_contas(self):
        """Salva contas no arquivo JSON"""
        try:
            with open(self.arquivo_contas, 'w', encoding='utf-8') as f:
                json.dump(self.contas, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erro ao salvar contas: {e}")
            return False
    
    def listar_contas(self) -> List[Dict]:
        """Lista todas as contas (sem senhas)"""
        contas_lista = []
        for username, dados in self.contas.items():
            conta = {
                'username': username,
                'name': dados.get('name', ''),
                'email': dados.get('email', ''),
                'role': dados.get('role', 'coordenador'),
                'created_at': dados.get('created_at', ''),
                'is_admin': dados.get('is_admin', False)
            }
            contas_lista.append(conta)
        return contas_lista
    
    def obter_conta(self, username: str) -> Optional[Dict]:
        """Obtém dados de uma conta específica (sem senha)"""
        if username in self.contas:
            dados = self.contas[username].copy()
            dados.pop('password_hash', None)
            dados['username'] = username
            return dados
        return None
    
    def criar_conta(self, username: str, password: str, name: str, email: str, is_admin: bool = False) -> bool:
        """Cria uma nova conta de coordenador"""
        if username in self.contas:
            return False
        
        self.contas[username] = {
            'password_hash': hashlib.sha256(password.encode()).hexdigest(),
            'role': 'coordenador',
            'name': name,
            'email': email,
            'created_at': datetime.now().isoformat(),
            'is_admin': is_admin
        }
        
        return self.salvar_contas()
    
    def atualizar_conta(self, username: str, name: str = None, email: str = None, 
                       password: str = None, is_admin: bool = None) -> bool:
        """Atualiza dados de uma conta"""
        if username not in self.contas:
            return False
        
        if name is not None:
            self.contas[username]['name'] = name
        if email is not None:
            self.contas[username]['email'] = email
        if password is not None:
            self.contas[username]['password_hash'] = hashlib.sha256(password.encode()).hexdigest()
        if is_admin is not None:
            self.contas[username]['is_admin'] = is_admin
        
        return self.salvar_contas()
    
    def remover_conta(self, username: str) -> bool:
        """Remove uma conta"""
        if username not in self.contas:
            return False
        
        # Não permitir remover a última conta admin
        if self.contas[username].get('is_admin', False):
            admins = [u for u, d in self.contas.items() if d.get('is_admin', False)]
            if len(admins) <= 1:
                return False
        
        del self.contas[username]
        return self.salvar_contas()
    
    def verificar_credenciais(self, username: str, password: str) -> bool:
        """Verifica se as credenciais são válidas"""
        if username not in self.contas:
            return False
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.contas[username]['password_hash']
    
    def obter_dados_usuario(self, username: str) -> Optional[Dict]:
        """Obtém dados completos do usuário para autenticação"""
        return self.contas.get(username)
    
    def total_contas(self) -> int:
        """Retorna total de contas cadastradas"""
        return len(self.contas)
    
    def total_admins(self) -> int:
        """Retorna total de administradores"""
        return sum(1 for d in self.contas.values() if d.get('is_admin', False))

