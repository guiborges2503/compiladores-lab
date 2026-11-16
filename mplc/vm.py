"""
Entrega 4, terceira metade (sim, sao tres) — a maquina virtual.

Le o .mplb e executa. Precisa de:
  - uma pilha de operandos;
  - um registro de ativacao por chamada, com os locais e o ponto de volta;
  - deteccao de divisao por zero e de estouro de pilha, com codigo de saida 2.

Essa e a materia da aula 11 virando codigo: sem registro de ativacao, a
recursao nao funciona.
"""
from mplc.erros import ErroMPL

LIMITE_QUADROS = 10000


class Quadro:
    def __init__(self, funcao):
        self.funcao = funcao
        self.slots = [('inteiro', 0) for _ in range(funcao.nslots)]
        self.ip = 0


class FuncaoVM:
    def __init__(self, nome, tipo):
        self.nome = nome
        self.tipo = tipo
        self.nslots = 0
        self.nparams = 0
        self.codigo = []
        self.rotulos = {}


class Maquina:
    def __init__(self, texto, saida):
        self.saida = saida
        self.funcoes, self.inicio = _analisar(texto)
        self.pilha = []
        self.quadros = []
        self.linha = 1

    def rodar(self):
        self.chamar(self.inicio, 0)
        while self.quadros:
            quadro = self.quadros[-1]
            codigo = quadro.funcao.codigo
            if quadro.ip >= len(codigo):
                if quadro.funcao.tipo == 'vazio':
                    self.quadros.pop()
                    continue
                self.falha('funcao acabou sem retorne')
            op, arg = codigo[quadro.ip]
            quadro.ip += 1
            self.executar(op, arg)

    def executar(self, op, arg):
        if op == 'linha':
            self.linha = int(arg)
        elif op == 'rotulo':
            pass
        elif op == 'empilha_int':
            self.pilha.append(('inteiro', int(arg)))
        elif op == 'empilha_real':
            self.pilha.append(('real', float(arg)))
        elif op == 'empilha_logico':
            self.pilha.append(('logico', arg == 'verdadeiro'))
        elif op == 'empilha_texto':
            self.pilha.append(('texto', _decodificar(arg)))
        elif op == 'carrega':
            self.pilha.append(self.quadros[-1].slots[int(arg)])
        elif op == 'guarda':
            self.quadros[-1].slots[int(arg)] = self.pilha.pop()
        elif op == 'para_real':
            tipo, valor = self.pilha.pop()
            self.pilha.append(('real', float(valor)))
        elif op == 'soma_int':
            self._bin_int(lambda a, b: a + b)
        elif op == 'soma_real':
            self._bin_real(lambda a, b: a + b)
        elif op == 'soma_texto':
            b = self.pilha.pop()
            a = self.pilha.pop()
            self.pilha.append(('texto', a[1] + b[1]))
        elif op == 'sub_int':
            self._bin_int(lambda a, b: a - b)
        elif op == 'sub_real':
            self._bin_real(lambda a, b: a - b)
        elif op == 'mul_int':
            self._bin_int(lambda a, b: a * b)
        elif op == 'mul_real':
            self._bin_real(lambda a, b: a * b)
        elif op == 'div_int':
            self._div_int()
        elif op == 'div_real':
            self._div_real()
        elif op == 'resto':
            self._resto()
        elif op == 'igual':
            self._cmp(lambda x, y: x == y)
        elif op == 'diferente':
            self._cmp(lambda x, y: x != y)
        elif op == 'menor':
            self._cmp(lambda x, y: x < y)
        elif op == 'menor_igual':
            self._cmp(lambda x, y: x <= y)
        elif op == 'maior':
            self._cmp(lambda x, y: x > y)
        elif op == 'maior_igual':
            self._cmp(lambda x, y: x >= y)
        elif op == 'e_logico':
            b = self.pilha.pop()
            a = self.pilha.pop()
            self.pilha.append(('logico', bool(a[1]) and bool(b[1])))
        elif op == 'ou_logico':
            b = self.pilha.pop()
            a = self.pilha.pop()
            self.pilha.append(('logico', bool(a[1]) or bool(b[1])))
        elif op == 'nao':
            a = self.pilha.pop()
            self.pilha.append(('logico', not a[1]))
        elif op == 'neg_int':
            a = self.pilha.pop()
            self.pilha.append(('inteiro', -a[1]))
        elif op == 'neg_real':
            a = self.pilha.pop()
            self.pilha.append(('real', -a[1]))
        elif op == 'escreva':
            tipo, valor = self.pilha.pop()
            self.saida.write(_formatar(tipo, valor) + '\n')
        elif op == 'desvie':
            self.quadros[-1].ip = self.quadros[-1].funcao.rotulos[arg]
        elif op == 'desvie_falso':
            valor = self.pilha.pop()
            if not valor[1]:
                self.quadros[-1].ip = self.quadros[-1].funcao.rotulos[arg]
        elif op == 'chama':
            nome, nargs = arg.split()
            self.chamar(nome, int(nargs))
        elif op == 'retorne':
            valor = self.pilha.pop()
            self.quadros.pop()
            self.pilha.append(valor)
        elif op == 'retorne_vazio':
            self.quadros.pop()
        else:
            self.falha(f'instrucao desconhecida {op}')

    def chamar(self, nome, nargs):
        if len(self.quadros) >= LIMITE_QUADROS:
            self.falha('estouro de pilha')
        args = [self.pilha.pop() for _ in range(nargs)]
        args.reverse()
        funcao = self.funcoes[nome]
        quadro = Quadro(funcao)
        for i, valor in enumerate(args):
            quadro.slots[i] = valor
        self.quadros.append(quadro)

    def _bin_int(self, op):
        b = self.pilha.pop()
        a = self.pilha.pop()
        self.pilha.append(('inteiro', op(a[1], b[1])))

    def _bin_real(self, op):
        b = self.pilha.pop()
        a = self.pilha.pop()
        self.pilha.append(('real', op(float(a[1]), float(b[1]))))

    def _div_int(self):
        b = self.pilha.pop()[1]
        a = self.pilha.pop()[1]
        if b == 0:
            self.falha('divisao por zero')
        quociente = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            quociente = -quociente
        self.pilha.append(('inteiro', quociente))

    def _div_real(self):
        b = float(self.pilha.pop()[1])
        a = float(self.pilha.pop()[1])
        if b == 0.0:
            self.falha('divisao por zero')
        self.pilha.append(('real', a / b))

    def _resto(self):
        b = self.pilha.pop()[1]
        a = self.pilha.pop()[1]
        if b == 0:
            self.falha('divisao por zero')
        quociente = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            quociente = -quociente
        self.pilha.append(('inteiro', a - quociente * b))

    def _cmp(self, op):
        b = self.pilha.pop()
        a = self.pilha.pop()
        if a[0] in ('inteiro', 'real') and b[0] in ('inteiro', 'real'):
            if a[0] == 'real' or b[0] == 'real':
                esquerda, direita = float(a[1]), float(b[1])
            else:
                esquerda, direita = a[1], b[1]
        else:
            esquerda, direita = a[1], b[1]
        self.pilha.append(('logico', op(esquerda, direita)))

    def falha(self, mensagem):
        raise ErroMPL('execucao', self.linha, 1, mensagem)


def _analisar(texto):
    funcoes = {}
    atual = None
    inicio = 'principal'
    for bruta in texto.splitlines():
        linha = bruta.strip()
        if not linha:
            continue
        if linha.startswith('empilha_texto '):
            op, arg = 'empilha_texto', linha[len('empilha_texto '):]
        elif ' ' in linha:
            op, arg = linha.split(' ', 1)
        else:
            op, arg = linha, ''
        if op == 'funcao':
            nome, tipo = arg.split()
            atual = FuncaoVM(nome, tipo)
            funcoes[nome] = atual
        elif op == 'quadro':
            atual.nslots = int(arg)
        elif op == 'parametros':
            atual.nparams = int(arg)
        elif op == 'fim':
            atual = None
        elif op == 'inicio':
            inicio = arg
        elif op == 'rotulo':
            atual.rotulos[arg] = len(atual.codigo)
            atual.codigo.append((op, arg))
        else:
            atual.codigo.append((op, arg))
    return funcoes, inicio


def _decodificar(lexema):
    if len(lexema) >= 2 and lexema[0] == '"' and lexema[-1] == '"':
        corpo = lexema[1:-1]
    else:
        corpo = lexema
    saida = []
    i = 0
    while i < len(corpo):
        if corpo[i] == '\\' and i + 1 < len(corpo):
            saida.append({'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(corpo[i + 1], corpo[i + 1]))
            i += 2
        else:
            saida.append(corpo[i])
            i += 1
    return ''.join(saida)


def _formatar(tipo, valor):
    if tipo == 'inteiro':
        return str(int(valor))
    if tipo == 'real':
        return f'{float(valor):.6f}'
    if tipo == 'logico':
        return 'verdadeiro' if valor else 'falso'
    return valor


def executar(texto_mplb, saida):
    """Executa o bytecode. Escreve o que o programa imprimir em `saida`."""
    Maquina(texto_mplb, saida).rodar()
