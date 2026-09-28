"""
Entrega 2 — analise sintatica.

Transformar a lista de tokens numa arvore.

Sugestao forte: descida recursiva, uma funcao por nivel de precedencia, na
ordem da secao 3.3 da especificacao. E como voces vao enxergar a precedencia
virar formato de arvore.

Gerador de parser (ANTLR, PLY, yacc) esta proibido nesta entrega e na
anterior — o objetivo e entender, e o gerador esconde exatamente a parte
que esta sendo ensinada.

Leiam antes: LINGUAGEM.md secoes 3 a 5, e CONTRATOS.md secao 3.
"""
from mplc.erros import ErroMPL

TIPOS_RETORNO = {
    'TIPO_INTEIRO', 'TIPO_REAL', 'TIPO_LOGICO', 'TIPO_TEXTO', 'TIPO_VAZIO',
}
TIPOS_VAR = {
    'TIPO_INTEIRO', 'TIPO_REAL', 'TIPO_LOGICO', 'TIPO_TEXTO',
}

OPS_OU = {'OU'}
OPS_E = {'E'}
OPS_IGUALDADE = {'IGUAL', 'DIFERENTE'}
OPS_RELACIONAL = {'MENOR', 'MENOR_IGUAL', 'MAIOR', 'MAIOR_IGUAL'}
OPS_ADITIVO = {'MAIS', 'MENOS'}
OPS_MULTIPLICATIVO = {'VEZES', 'DIVIDE', 'RESTO'}


class No:
    """Um no da arvore. O rotulo e o que sai no --ast."""

    def __init__(self, rotulo, filhos=None, linha=0, coluna=0, **extra):
        self.rotulo = rotulo      # 'binario +', 'literal inteiro 1', 'bloco', ...
        self.filhos = filhos or []
        self.linha = linha
        self.coluna = coluna
        self.extra = extra        # o que a semantica quiser pendurar depois


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def atual(self):
        return self.tokens[self.i]

    def combinar(self, *tipos):
        return self.atual().tipo in tipos

    def consumir(self, tipo=None):
        tok = self.atual()
        if tipo is not None and tok.tipo != tipo:
            esperado = tipo
            raise ErroMPL(
                'sintatico', tok.linha, tok.coluna,
                f'esperado {esperado}, veio {tok.tipo}',
            )
        self.i += 1
        return tok

    def erro(self, mensagem):
        tok = self.atual()
        raise ErroMPL('sintatico', tok.linha, tok.coluna, mensagem)

    def programa(self):
        funcoes = []
        while self.combinar('FUNCAO'):
            funcoes.append(self.funcao())
        if not self.combinar('FIM_ARQUIVO'):
            self.erro('esperado fim do arquivo ou outra funcao')
        self.consumir('FIM_ARQUIVO')
        return No('programa', funcoes)

    def funcao(self):
        inicio = self.consumir('FUNCAO')
        if not self.combinar(*TIPOS_RETORNO):
            self.erro('esperado tipo de retorno apos funcao')
        tipo = self.consumir().lexema
        nome = self.consumir('ID')
        self.consumir('ABRE_PAR')
        params = self.parametros()
        self.consumir('FECHA_PAR')
        corpo = self.bloco()
        return No(
            f'funcao {nome.lexema} {tipo}',
            [params, corpo],
            inicio.linha, inicio.coluna,
        )

    def parametros(self):
        filhos = []
        if self.combinar(*TIPOS_VAR):
            filhos.append(self.parametro())
            while self.combinar('VIRGULA'):
                self.consumir('VIRGULA')
                filhos.append(self.parametro())
        return No('parametros', filhos)

    def parametro(self):
        if not self.combinar(*TIPOS_VAR):
            self.erro('esperado tipo de parametro')
        tipo = self.consumir().lexema
        nome = self.consumir('ID')
        return No(f'parametro {nome.lexema} {tipo}', [], nome.linha, nome.coluna)

    def bloco(self):
        abre = self.consumir('ABRE_CHAVE')
        cmds = []
        while not self.combinar('FECHA_CHAVE', 'FIM_ARQUIVO'):
            cmds.append(self.comando())
        self.consumir('FECHA_CHAVE')
        return No('bloco', cmds, abre.linha, abre.coluna)

    def comando(self):
        if self.combinar(*TIPOS_VAR):
            return self.declaracao()
        if self.combinar('SE'):
            return self.condicional()
        if self.combinar('ENQUANTO'):
            return self.repeticao()
        if self.combinar('ESCREVA'):
            return self.escrita()
        if self.combinar('RETORNE'):
            return self.retorno()
        if self.combinar('ABRE_CHAVE'):
            return self.bloco()
        if self.combinar('ID'):
            return self.atribuicao_ou_chamada()
        self.erro('comando invalido')

    def declaracao(self):
        tipo_tok = self.consumir()
        nome = self.consumir('ID')
        filhos = []
        if self.combinar('ATRIBUI'):
            self.consumir('ATRIBUI')
            filhos.append(self.expressao())
        self.consumir('PONTO_VIRGULA')
        return No(
            f'declaracao {nome.lexema} {tipo_tok.lexema}',
            filhos,
            tipo_tok.linha, tipo_tok.coluna,
        )

    def atribuicao_ou_chamada(self):
        nome = self.consumir('ID')
        if self.combinar('ATRIBUI'):
            self.consumir('ATRIBUI')
            expr = self.expressao()
            self.consumir('PONTO_VIRGULA')
            return No(f'atribuicao {nome.lexema}', [expr], nome.linha, nome.coluna)
        if self.combinar('ABRE_PAR'):
            chamada = self.terminar_chamada(nome)
            self.consumir('PONTO_VIRGULA')
            return chamada
        self.erro('esperado = ou ( apos identificador')

    def condicional(self):
        inicio = self.consumir('SE')
        self.consumir('ABRE_PAR')
        cond = self.expressao()
        self.consumir('FECHA_PAR')
        entao = self.bloco()
        filhos = [cond, entao]
        if self.combinar('SENAO'):
            self.consumir('SENAO')
            filhos.append(self.bloco())
        return No('se', filhos, inicio.linha, inicio.coluna)

    def repeticao(self):
        inicio = self.consumir('ENQUANTO')
        self.consumir('ABRE_PAR')
        cond = self.expressao()
        self.consumir('FECHA_PAR')
        corpo = self.bloco()
        return No('enquanto', [cond, corpo], inicio.linha, inicio.coluna)

    def escrita(self):
        inicio = self.consumir('ESCREVA')
        self.consumir('ABRE_PAR')
        expr = self.expressao()
        self.consumir('FECHA_PAR')
        self.consumir('PONTO_VIRGULA')
        return No('escreva', [expr], inicio.linha, inicio.coluna)

    def retorno(self):
        inicio = self.consumir('RETORNE')
        filhos = []
        if not self.combinar('PONTO_VIRGULA'):
            filhos.append(self.expressao())
        self.consumir('PONTO_VIRGULA')
        return No('retorne', filhos, inicio.linha, inicio.coluna)

    # --- expressoes: um metodo por nivel (esquerda -> direita = fraco -> forte) ---

    def expressao(self):
        return self.ou()

    def _binario_esq(self, seguinte, tipos_op):
        """Nivel binario associativo a esquerda: chama o nivel mais forte a direita."""
        esq = seguinte()
        while self.atual().tipo in tipos_op:
            op = self.consumir()
            dir_ = seguinte()
            esq = No(
                f'binario {op.lexema}',
                [esq, dir_],
                op.linha, op.coluna,
            )
        return esq

    def ou(self):
        return self._binario_esq(self.e, OPS_OU)

    def e(self):
        return self._binario_esq(self.igualdade, OPS_E)

    def igualdade(self):
        return self._binario_esq(self.relacional, OPS_IGUALDADE)

    def relacional(self):
        return self._binario_esq(self.aditivo, OPS_RELACIONAL)

    def aditivo(self):
        return self._binario_esq(self.multiplicativo, OPS_ADITIVO)

    def multiplicativo(self):
        return self._binario_esq(self.unario, OPS_MULTIPLICATIVO)

    def unario(self):
        if self.combinar('NAO'):
            op = self.consumir('NAO')
            return No(f'unario {op.lexema}', [self.unario()], op.linha, op.coluna)
        if self.combinar('MENOS'):
            op = self.consumir('MENOS')
            return No('unario -', [self.unario()], op.linha, op.coluna)
        return self.primaria()

    def primaria(self):
        if self.combinar('INTEIRO'):
            tok = self.consumir('INTEIRO')
            return No(
                f'literal inteiro {tok.lexema}',
                [], tok.linha, tok.coluna,
            )
        if self.combinar('REAL'):
            tok = self.consumir('REAL')
            valor = f'{float(tok.lexema):.6f}'
            return No(
                f'literal real {valor}',
                [], tok.linha, tok.coluna,
            )
        if self.combinar('LOGICO'):
            tok = self.consumir('LOGICO')
            return No(
                f'literal logico {tok.lexema}',
                [], tok.linha, tok.coluna,
            )
        if self.combinar('TEXTO'):
            tok = self.consumir('TEXTO')
            return No(
                f'literal texto {tok.lexema}',
                [], tok.linha, tok.coluna,
            )
        if self.combinar('ID'):
            nome = self.consumir('ID')
            if self.combinar('ABRE_PAR'):
                return self.terminar_chamada(nome)
            return No(f'variavel {nome.lexema}', [], nome.linha, nome.coluna)
        if self.combinar('ABRE_PAR'):
            self.consumir('ABRE_PAR')
            expr = self.expressao()
            self.consumir('FECHA_PAR')
            return expr
        self.erro('esperada expressao')

    def terminar_chamada(self, nome):
        self.consumir('ABRE_PAR')
        args = []
        if not self.combinar('FECHA_PAR'):
            args.append(self.expressao())
            while self.combinar('VIRGULA'):
                self.consumir('VIRGULA')
                args.append(self.expressao())
        self.consumir('FECHA_PAR')
        return No(f'chamada {nome.lexema}', args, nome.linha, nome.coluna)


def analisar(tokens):
    """Recebe a lista de Token. Devolve a raiz da arvore (um No 'programa')."""
    return Parser(tokens).programa()


def despejar(no, nivel=0, saida=None):
    """Imprime a arvore no formato do --ast. Ja esta pronto: dois espacos por nivel."""
    saida = saida if saida is not None else []
    saida.append('  ' * nivel + no.rotulo)
    for f in no.filhos:
        despejar(f, nivel + 1, saida)
    return saida
