"""
Entrega 1 — analise lexica.

Transformar o texto do programa numa lista de tokens.

O que voces tem que devolver: uma lista de Token. O ultimo elemento e sempre
um token FIM_ARQUIVO. A regra de posicao dele esta em CONTRATOS.md, secao 7.

Leiam antes: LINGUAGEM.md secao 2, e CONTRATOS.md secao 2.
"""
from mplc.erros import ErroMPL

PALAVRAS = {
    'funcao': 'FUNCAO',
    'retorne': 'RETORNE',
    'se': 'SE',
    'senao': 'SENAO',
    'enquanto': 'ENQUANTO',
    'escreva': 'ESCREVA',
    'inteiro': 'TIPO_INTEIRO',
    'real': 'TIPO_REAL',
    'logico': 'TIPO_LOGICO',
    'texto': 'TIPO_TEXTO',
    'vazio': 'TIPO_VAZIO',
    'verdadeiro': 'LOGICO',
    'falso': 'LOGICO',
    'e': 'E',
    'ou': 'OU',
    'nao': 'NAO',
}

DOIS_CHARS = {
    '==': 'IGUAL',
    '!=': 'DIFERENTE',
    '<=': 'MENOR_IGUAL',
    '>=': 'MAIOR_IGUAL',
}

UM_CHAR = {
    '+': 'MAIS',
    '-': 'MENOS',
    '*': 'VEZES',
    '/': 'DIVIDE',
    '%': 'RESTO',
    '<': 'MENOR',
    '>': 'MAIOR',
    '=': 'ATRIBUI',
    '(': 'ABRE_PAR',
    ')': 'FECHA_PAR',
    '{': 'ABRE_CHAVE',
    '}': 'FECHA_CHAVE',
    ',': 'VIRGULA',
    ';': 'PONTO_VIRGULA',
}

ESCAPES_VALIDOS = set('nt"\\')


class Token:
    __slots__ = ('tipo', 'lexema', 'linha', 'coluna')

    def __init__(self, tipo, lexema, linha, coluna):
        self.tipo = tipo          # 'ID', 'INTEIRO', 'MAIS', ... (a lista esta no contrato)
        self.lexema = lexema      # o texto exato como apareceu no fonte
        self.linha = linha
        self.coluna = coluna      # a coluna do PRIMEIRO caractere do token

    def __str__(self):
        # esta e a linha que o --tokens imprime; nao mexam no formato
        return f"{self.linha},{self.coluna},{self.tipo},{self.lexema}"


def analisar(fonte):
    """Recebe o texto do programa. Devolve a lista de Token."""
    tokens = []
    i = 0
    n = len(fonte)
    linha = 1
    coluna = 1

    def olhar(k=0):
        pos = i + k
        if pos >= n:
            return None
        return fonte[pos]

    def avancar():
        nonlocal i, linha, coluna
        if i >= n:
            return
        c = fonte[i]
        i += 1
        if c == '\r':
            if i < n and fonte[i] == '\n':
                i += 1
            linha += 1
            coluna = 1
        elif c == '\n':
            linha += 1
            coluna = 1
        else:
            coluna += 1

    def pular_espaco():
        while i < n and fonte[i] in ' \t\r\n':
            avancar()

    def emitir(tipo, lexema, l, c):
        tokens.append(Token(tipo, lexema, l, c))

    def erro_lexico(l, c, mensagem):
        raise ErroMPL('lexico', l, c, mensagem)

    while True:
        pular_espaco()
        if i >= n:
            break

        inicio_linha = linha
        inicio_coluna = coluna
        c = fonte[i]

        if c == '/' and olhar(1) == '/':
            while i < n and fonte[i] not in '\r\n':
                avancar()
            continue

        if c == '/' and olhar(1) == '*':
            com_linha, com_coluna = inicio_linha, inicio_coluna
            avancar()
            avancar()
            fechou = False
            while i < n:
                if fonte[i] == '*' and olhar(1) == '/':
                    avancar()
                    avancar()
                    fechou = True
                    break
                avancar()
            if not fechou:
                erro_lexico(com_linha, com_coluna, 'comentario de bloco nao fechado')
            continue

        if c == '"':
            texto_linha, texto_coluna = inicio_linha, inicio_coluna
            inicio = i
            avancar()
            while i < n and fonte[i] not in '"\r\n':
                if fonte[i] == '\\':
                    if olhar(1) not in ESCAPES_VALIDOS:
                        erro_lexico(linha, coluna, 'escape invalido')
                    avancar()
                    avancar()
                else:
                    avancar()
            if i >= n or fonte[i] in '\r\n':
                erro_lexico(texto_linha, texto_coluna, 'texto nao fechado')
            avancar()
            emitir('TEXTO', fonte[inicio:i], texto_linha, texto_coluna)
            continue

        if c.isalpha() or c == '_':
            inicio = i
            while i < n and (fonte[i].isalnum() or fonte[i] == '_'):
                avancar()
            lexema = fonte[inicio:i]
            tipo = PALAVRAS.get(lexema, 'ID')
            emitir(tipo, lexema, inicio_linha, inicio_coluna)
            continue

        if c.isdigit():
            inicio = i
            while i < n and fonte[i].isdigit():
                avancar()
            if i < n and fonte[i] == '.':
                ponto_linha, ponto_coluna = linha, coluna
                avancar()
                if i >= n or not fonte[i].isdigit():
                    erro_lexico(ponto_linha, ponto_coluna, 'real mal formado')
                while i < n and fonte[i].isdigit():
                    avancar()
                emitir('REAL', fonte[inicio:i], inicio_linha, inicio_coluna)
            else:
                emitir('INTEIRO', fonte[inicio:i], inicio_linha, inicio_coluna)
            continue

        if i + 1 < n:
            par = fonte[i:i + 2]
            if par in DOIS_CHARS:
                emitir(DOIS_CHARS[par], par, inicio_linha, inicio_coluna)
                avancar()
                avancar()
                continue

        if c in UM_CHAR:
            emitir(UM_CHAR[c], c, inicio_linha, inicio_coluna)
            avancar()
            continue

        erro_lexico(inicio_linha, inicio_coluna, 'caractere invalido')

    pular_espaco()
    tokens.append(Token('FIM_ARQUIVO', '', linha, coluna))
    return tokens
