"""
Entrega 3 — analise semantica.

Tabela de simbolos, escopos aninhados e verificacao de tipos.

Tres coisas que costumam ser esquecidas e valem nota:
  - o corpo de uma funcao abre DOIS escopos (o dos parametros e o do bloco);
  - uma funcao pode ser chamada antes de aparecer no arquivo, entao a
    primeira passada so coleta assinaturas;
  - funcao com retorno declarado precisa garantir o retorno em TODOS os
    caminhos.

Leiam antes: LINGUAGEM.md secoes 3 a 5, e CONTRATOS.md secao 4.
"""
from mplc.erros import ErroMPL

NUMERICOS = ('inteiro', 'real')
RELACIONAIS = ('<', '<=', '>', '>=')
IGUALDADE = ('==', '!=')
ARITMETICOS = ('+', '-', '*', '/')


class Simbolo:
    def __init__(self, nome, categoria, tipo, linha, parametros=None):
        self.nome = nome
        self.categoria = categoria    # 'funcao', 'parametro' ou 'variavel'
        self.tipo = tipo
        self.linha = linha
        self.parametros = parametros or []


class Escopo:
    def __init__(self, numero, descricao, pai):
        self.numero = numero
        self.descricao = descricao
        self.pai = pai
        self.simbolos = []
        self.por_nome = {}


class Analisador:
    def __init__(self):
        self.escopos = []
        self.pilha = []
        self.funcoes = {}
        self.retorno = None

    def erro(self, linha, coluna, mensagem):
        raise ErroMPL('semantico', linha or 1, coluna or 1, mensagem)

    def abrir(self, descricao):
        pai = self.pilha[-1].numero if self.pilha else None
        escopo = Escopo(len(self.escopos), descricao, pai)
        self.escopos.append(escopo)
        self.pilha.append(escopo)
        return escopo

    def fechar(self):
        self.pilha.pop()

    def declarar(self, nome, categoria, tipo, linha, coluna, parametros=None):
        escopo = self.pilha[-1]
        if nome in escopo.por_nome:
            self.erro(linha, coluna, f'{nome} ja foi declarado neste escopo')
        simbolo = Simbolo(nome, categoria, tipo, linha, parametros)
        escopo.por_nome[nome] = simbolo
        escopo.simbolos.append(simbolo)
        return simbolo

    def buscar_variavel(self, nome):
        for escopo in reversed(self.pilha):
            simbolo = escopo.por_nome.get(nome)
            if simbolo is not None and simbolo.categoria != 'funcao':
                return simbolo
        return None

    def compativel(self, esperado, obtido):
        if esperado == obtido:
            return True
        return esperado == 'real' and obtido == 'inteiro'

    def analisar(self, arvore):
        self.abrir('global')
        self.coletar_assinaturas(arvore)
        for funcao in arvore.filhos:
            self.analisar_funcao(funcao)
        if 'principal' not in self.funcoes:
            self.erro(1, 1, 'falta a funcao principal')
        return self.escopos

    def coletar_assinaturas(self, arvore):
        for funcao in arvore.filhos:
            nome, tipo = _rotulo(funcao.rotulo)
            params = []
            for parametro in funcao.filhos[0].filhos:
                _, tipo_param = _rotulo(parametro.rotulo)
                params.append(tipo_param)
            if nome in self.funcoes:
                self.erro(funcao.linha, funcao.coluna, f'funcao {nome} redeclarada')
            simbolo = self.declarar(
                nome, 'funcao', tipo, funcao.linha, funcao.coluna, params,
            )
            self.funcoes[nome] = simbolo

    def analisar_funcao(self, no):
        nome, tipo = _rotulo(no.rotulo)
        parametros = no.filhos[0].filhos
        if nome == 'principal' and (tipo != 'vazio' or parametros):
            self.erro(no.linha, no.coluna, 'principal deve ser vazio e sem parametros')
        self.retorno = tipo
        self.abrir(f'funcao {nome}')
        for parametro in parametros:
            nome_param, tipo_param = _rotulo(parametro.rotulo)
            self.declarar(
                nome_param, 'parametro', tipo_param,
                parametro.linha, parametro.coluna,
            )
        self.bloco(no.filhos[1])
        self.fechar()
        if tipo != 'vazio' and not self.garante(no.filhos[1]):
            self.erro(no.linha, no.coluna, 'ha caminho sem retorne')

    def bloco(self, no):
        self.abrir('bloco')
        for comando in no.filhos:
            self.comando(comando)
        self.fechar()

    def comando(self, no):
        rotulo = no.rotulo
        if rotulo.startswith('declaracao '):
            self.declaracao(no)
        elif rotulo.startswith('atribuicao '):
            self.atribuicao(no)
        elif rotulo.startswith('chamada '):
            self.chamada(no, em_expressao=False)
        elif rotulo == 'se':
            self.condicional(no)
        elif rotulo == 'enquanto':
            self.repeticao(no)
        elif rotulo == 'escreva':
            self.escrita(no)
        elif rotulo == 'retorne':
            self.retorno_cmd(no)
        elif rotulo == 'bloco':
            self.bloco(no)
        else:
            self.erro(no.linha, no.coluna, 'comando invalido')

    def declaracao(self, no):
        nome, tipo = _rotulo(no.rotulo)
        if no.filhos:
            obtido = self.expr(no.filhos[0])
            if not self.compativel(tipo, obtido):
                self.erro(no.linha, no.coluna, 'tipo incompativel na declaracao')
        self.declarar(nome, 'variavel', tipo, no.linha, no.coluna)

    def atribuicao(self, no):
        nome = no.rotulo.split(' ', 1)[1]
        simbolo = self.buscar_variavel(nome)
        if simbolo is None:
            self.erro(no.linha, no.coluna, f'{nome} nao foi declarada')
        obtido = self.expr(no.filhos[0])
        if not self.compativel(simbolo.tipo, obtido):
            self.erro(no.linha, no.coluna, 'tipo incompativel na atribuicao')

    def condicional(self, no):
        if self.expr(no.filhos[0]) != 'logico':
            self.erro(no.linha, no.coluna, 'a condicao do se precisa ser logico')
        self.bloco(no.filhos[1])
        if len(no.filhos) == 3:
            self.bloco(no.filhos[2])

    def repeticao(self, no):
        if self.expr(no.filhos[0]) != 'logico':
            self.erro(no.linha, no.coluna, 'a condicao do enquanto precisa ser logico')
        self.bloco(no.filhos[1])

    def escrita(self, no):
        if self.expr(no.filhos[0]) == 'vazio':
            self.erro(no.linha, no.coluna, 'escreva nao aceita vazio')

    def retorno_cmd(self, no):
        if self.retorno == 'vazio':
            if no.filhos:
                self.erro(no.linha, no.coluna, 'funcao vazio nao retorna valor')
            return
        if not no.filhos:
            self.erro(no.linha, no.coluna, 'retorne sem valor')
        obtido = self.expr(no.filhos[0])
        if not self.compativel(self.retorno, obtido):
            self.erro(no.linha, no.coluna, 'tipo de retorno incompativel')

    def chamada(self, no, em_expressao):
        nome = no.rotulo.split(' ', 1)[1]
        funcao = self.funcoes.get(nome)
        if funcao is None:
            self.erro(no.linha, no.coluna, f'funcao {nome} nao existe')
        if len(no.filhos) != len(funcao.parametros):
            self.erro(no.linha, no.coluna, 'quantidade de argumentos errada')
        for arg, esperado in zip(no.filhos, funcao.parametros):
            obtido = self.expr(arg)
            if not self.compativel(esperado, obtido):
                self.erro(no.linha, no.coluna, 'tipo de argumento incompativel')
        if em_expressao and funcao.tipo == 'vazio':
            self.erro(no.linha, no.coluna, 'funcao vazio nao pode aparecer numa expressao')
        return funcao.tipo

    def expr(self, no):
        rotulo = no.rotulo
        if rotulo.startswith('literal '):
            return rotulo.split(' ', 2)[1]
        if rotulo.startswith('variavel '):
            nome = rotulo.split(' ', 1)[1]
            simbolo = self.buscar_variavel(nome)
            if simbolo is None:
                self.erro(no.linha, no.coluna, f'{nome} nao foi declarada')
            return simbolo.tipo
        if rotulo.startswith('chamada '):
            return self.chamada(no, em_expressao=True)
        if rotulo.startswith('binario '):
            return self.binario(no)
        if rotulo.startswith('unario '):
            return self.unario(no)
        self.erro(no.linha, no.coluna, 'expressao invalida')

    def binario(self, no):
        op = no.rotulo.split(' ', 1)[1]
        esquerda = self.expr(no.filhos[0])
        direita = self.expr(no.filhos[1])
        if op == '+':
            if esquerda == 'texto' and direita == 'texto':
                return 'texto'
            if esquerda == 'texto' or direita == 'texto':
                self.erro(no.linha, no.coluna, 'nao da para somar texto com outro tipo')
        if op == '%':
            if esquerda != 'inteiro' or direita != 'inteiro':
                self.erro(no.linha, no.coluna, 'resto so aceita inteiro')
            return 'inteiro'
        if op in ARITMETICOS:
            if esquerda not in NUMERICOS or direita not in NUMERICOS:
                self.erro(no.linha, no.coluna, f'operando invalido para {op}')
            if esquerda == 'inteiro' and direita == 'inteiro':
                return 'inteiro'
            return 'real'
        if op in IGUALDADE:
            iguais = esquerda == direita
            numerico = {esquerda, direita} <= set(NUMERICOS) and esquerda in NUMERICOS and direita in NUMERICOS
            if iguais or numerico:
                return 'logico'
            self.erro(no.linha, no.coluna, f'tipos incompativeis em {op}')
        if op in RELACIONAIS:
            if esquerda not in NUMERICOS or direita not in NUMERICOS:
                self.erro(no.linha, no.coluna, f'{op} so compara numeros')
            return 'logico'
        if op in ('e', 'ou'):
            if esquerda != 'logico' or direita != 'logico':
                self.erro(no.linha, no.coluna, f'{op} so aceita logico')
            return 'logico'
        self.erro(no.linha, no.coluna, f'operador desconhecido {op}')

    def unario(self, no):
        op = no.rotulo.split(' ', 1)[1]
        tipo = self.expr(no.filhos[0])
        if op == 'nao':
            if tipo != 'logico':
                self.erro(no.linha, no.coluna, 'nao so aceita logico')
            return 'logico'
        if op == '-':
            if tipo not in NUMERICOS:
                self.erro(no.linha, no.coluna, 'menos unario so aceita numero')
            return tipo
        self.erro(no.linha, no.coluna, f'operador desconhecido {op}')

    def garante(self, no):
        """Olha so a estrutura: um se sem senao nunca garante retorno."""
        if no.rotulo == 'bloco':
            return any(self.garante(filho) for filho in no.filhos)
        if no.rotulo == 'retorne':
            return True
        if no.rotulo == 'se' and len(no.filhos) == 3:
            return self.garante(no.filhos[1]) and self.garante(no.filhos[2])
        return False


def _rotulo(rotulo):
    """'funcao nome tipo' / 'parametro nome tipo' / 'declaracao nome tipo'."""
    partes = rotulo.split(' ', 2)
    return partes[1], partes[2]


def analisar(arvore):
    """Percorre a arvore, monta a tabela e confere os tipos. Devolve a tabela."""
    return Analisador().analisar(arvore)


def despejar(tabela):
    """Devolve as linhas do --tabela, no formato da secao 4 do contrato."""
    linhas = []
    for escopo in tabela:
        if escopo.numero == 0:
            linhas.append('escopo 0 global')
        else:
            linhas.append(f'escopo {escopo.numero} {escopo.descricao} pai {escopo.pai}')
        for simbolo in escopo.simbolos:
            if simbolo.categoria == 'funcao':
                params = ','.join(simbolo.parametros)
                linhas.append(
                    f'  {simbolo.nome}|funcao|{simbolo.tipo}({params})|{simbolo.linha}'
                )
            else:
                linhas.append(
                    f'  {simbolo.nome}|{simbolo.categoria}|{simbolo.tipo}|{simbolo.linha}'
                )
    return linhas
