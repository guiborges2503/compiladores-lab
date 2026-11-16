"""
Entrega 4, primeira metade — codigo de tres enderecos.

A propriedade que define a representacao, e a unica que o verificador mede:
cada linha de operacao tem NO MAXIMO UM OPERADOR. Uma expressao como
a + b * c vira duas linhas, com um temporario no meio.

O formato do despejo e de voces. A propriedade nao e.

Leiam antes: CONTRATOS.md secao 5.
"""
from mplc.erros import ErroMPL


class Nome:
    """Um nome no quadro da funcao: variavel, parametro ou temporario."""

    def __init__(self, texto, slot, tipo):
        self.texto = texto
        self.slot = slot
        self.tipo = tipo

    def __str__(self):
        return self.texto


class Ins:
    def __init__(self, kind, linha=0, **kw):
        self.kind = kind
        self.linha = linha
        for chave, valor in kw.items():
            setattr(self, chave, valor)

    def texto(self):
        k = self.kind
        if k == 'rotulo':
            return f'{self.nome}:'
        if k == 'va_para':
            return f'va_para {self.nome}'
        if k == 'se_falso':
            return f'se_falso {self.cond} va_para {self.nome}'
        if k == 'const':
            return f'{self.dest} = {self.literal}'
        if k == 'bin':
            return f'{self.dest} = {self.esq} {self.op} {self.dir}'
        if k == 'un':
            return f'{self.dest} = {self.op} {self.src}'
        if k == 'conv':
            return f'{self.dest} = para_real {self.src}'
        if k == 'copia':
            return f'{self.dest} = {self.src}'
        if k == 'chama':
            args = ' '.join(str(a) for a in self.args)
            if self.dest is None:
                return f'chama {self.nome} {args}'.rstrip()
            return f'{self.dest} = chama {self.nome} {args}'.rstrip()
        if k == 'retorne':
            if self.src is None:
                return 'retorne'
            return f'retorne {self.src}'
        if k == 'escreva':
            return f'escreva {self.src}'
        return k


class Funcao:
    def __init__(self, nome, tipo, params, nslots, corpo):
        self.nome = nome
        self.tipo = tipo
        self.params = params
        self.nslots = nslots
        self.corpo = corpo


class GeradorIR:
    def __init__(self, tabela):
        self.assinaturas = {s.nome: s for s in tabela[0].simbolos}
        self.funcoes = []
        self.n_rotulo = 0

    def gerar(self, arvore):
        for no in arvore.filhos:
            self.funcao(no)
        return self.funcoes

    def funcao(self, no):
        nome, tipo = _partir(no.rotulo)
        self.escopos = []
        self.usados = set()
        self.nslots = 0
        self.n_temp = 0
        self.corpo = []
        self.tipo_ret = tipo
        self.linha = no.linha or 1
        self.escopos.append({})
        params = []
        for parametro in no.filhos[0].filhos:
            pn, pt = _partir(parametro.rotulo)
            params.append(self.declarar(pn, pt))
        self.bloco(no.filhos[1])
        if tipo == 'vazio':
            self.linha = 0
            self.emitir(Ins('retorne', src=None))
        self.funcoes.append(Funcao(nome, tipo, params, self.nslots, self.corpo))

    def declarar(self, nome, tipo):
        self.usados.add(nome)
        slot = self.nslots
        self.nslots += 1
        ent = Nome(nome, slot, tipo)
        self.escopos[-1][nome] = ent
        return ent

    def novo(self, tipo):
        while f't{self.n_temp}' in self.usados:
            self.n_temp += 1
        texto = f't{self.n_temp}'
        self.n_temp += 1
        self.usados.add(texto)
        slot = self.nslots
        self.nslots += 1
        return Nome(texto, slot, tipo)

    def buscar(self, nome):
        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
        raise ErroMPL('semantico', self.linha, 1, f'{nome} nao foi declarada')

    def emitir(self, ins):
        ins.linha = self.linha
        self.corpo.append(ins)
        return ins

    def rotulo(self):
        nome = f'L{self.n_rotulo}'
        self.n_rotulo += 1
        return nome

    def bloco(self, no):
        self.escopos.append({})
        for comando in no.filhos:
            self.comando(comando)
        self.escopos.pop()

    def comando(self, no):
        rotulo = no.rotulo
        self.linha = no.linha or self.linha
        if rotulo.startswith('declaracao '):
            self.declaracao(no)
        elif rotulo.startswith('atribuicao '):
            self.atribuicao(no)
        elif rotulo.startswith('chamada '):
            self.chamada(no, como_expr=False)
        elif rotulo == 'se':
            self.condicional(no)
        elif rotulo == 'enquanto':
            self.repeticao(no)
        elif rotulo == 'escreva':
            self.escrita(no)
        elif rotulo == 'retorne':
            self.retorno(no)
        elif rotulo == 'bloco':
            self.bloco(no)
        else:
            raise ErroMPL('semantico', self.linha, 1, 'comando invalido')

    def declaracao(self, no):
        nome, tipo = _partir(no.rotulo)
        destino = self.declarar(nome, tipo)
        if no.filhos:
            valor, obtido = self.expr(no.filhos[0])
            if tipo == 'real' and obtido == 'inteiro':
                valor = self.para_real(valor)
        else:
            valor = self.padrao(tipo)
        self.emitir(Ins('copia', dest=destino, src=valor))

    def atribuicao(self, no):
        nome = no.rotulo.split(' ', 1)[1]
        destino = self.buscar(nome)
        valor, obtido = self.expr(no.filhos[0])
        if destino.tipo == 'real' and obtido == 'inteiro':
            valor = self.para_real(valor)
        self.emitir(Ins('copia', dest=destino, src=valor))

    def condicional(self, no):
        cond, _ = self.expr(no.filhos[0])
        fim = self.rotulo()
        if len(no.filhos) == 3:
            senao = self.rotulo()
            self.emitir(Ins('se_falso', cond=cond, nome=senao))
            self.bloco(no.filhos[1])
            self.linha = no.linha or self.linha
            self.emitir(Ins('va_para', nome=fim))
            self.emitir(Ins('rotulo', nome=senao))
            self.bloco(no.filhos[2])
        else:
            self.emitir(Ins('se_falso', cond=cond, nome=fim))
            self.bloco(no.filhos[1])
        self.linha = no.linha or self.linha
        self.emitir(Ins('rotulo', nome=fim))

    def repeticao(self, no):
        inicio = self.rotulo()
        fim = self.rotulo()
        self.emitir(Ins('rotulo', nome=inicio))
        cond, _ = self.expr(no.filhos[0])
        self.emitir(Ins('se_falso', cond=cond, nome=fim))
        self.bloco(no.filhos[1])
        self.linha = no.linha or self.linha
        self.emitir(Ins('va_para', nome=inicio))
        self.emitir(Ins('rotulo', nome=fim))

    def escrita(self, no):
        valor, _ = self.expr(no.filhos[0])
        self.emitir(Ins('escreva', src=valor))

    def retorno(self, no):
        if not no.filhos:
            self.emitir(Ins('retorne', src=None))
            return
        valor, obtido = self.expr(no.filhos[0])
        if self.tipo_ret == 'real' and obtido == 'inteiro':
            valor = self.para_real(valor)
        self.emitir(Ins('retorne', src=valor))

    def chamada(self, no, como_expr):
        nome = no.rotulo.split(' ', 1)[1]
        assinatura = self.assinaturas[nome]
        args = []
        for arg, esperado in zip(no.filhos, assinatura.parametros):
            valor, obtido = self.expr(arg)
            if esperado == 'real' and obtido == 'inteiro':
                valor = self.para_real(valor)
            args.append(valor)
        if assinatura.tipo == 'vazio':
            self.emitir(Ins('chama', dest=None, nome=nome, args=args))
            return None, 'vazio'
        destino = self.novo(assinatura.tipo)
        self.emitir(Ins('chama', dest=destino, nome=nome, args=args))
        return destino, assinatura.tipo

    def expr(self, no):
        rotulo = no.rotulo
        if rotulo.startswith('literal '):
            tipo, resto = rotulo.split(' ', 2)[1:]
            return self.constante(tipo, resto), tipo
        if rotulo.startswith('variavel '):
            nome = rotulo.split(' ', 1)[1]
            ent = self.buscar(nome)
            return ent, ent.tipo
        if rotulo.startswith('chamada '):
            return self.chamada(no, como_expr=True)
        if rotulo.startswith('unario '):
            return self.unario(no)
        if rotulo.startswith('binario '):
            return self.binario(no)
        raise ErroMPL('semantico', self.linha, 1, 'expressao invalida')

    def unario(self, no):
        op = no.rotulo.split(' ', 1)[1]
        src, tipo = self.expr(no.filhos[0])
        destino = self.novo(tipo if op == '-' else 'logico')
        self.emitir(Ins('un', dest=destino, op=op, src=src, tipo=destino.tipo))
        return destino, destino.tipo

    def binario(self, no):
        op = no.rotulo.split(' ', 1)[1]
        esq, te = self.expr(no.filhos[0])
        dire, td = self.expr(no.filhos[1])
        esq, te, dire, td, tr = self.ajustar(op, esq, te, dire, td)
        destino = self.novo(tr)
        self.emitir(Ins('bin', dest=destino, esq=esq, op=op, dir=dire, tipo=tr))
        return destino, tr

    def ajustar(self, op, esq, te, dire, td):
        if op == '+' and te == 'texto' and td == 'texto':
            return esq, te, dire, td, 'texto'
        if op == '%':
            return esq, te, dire, td, 'inteiro'
        if op in ('+', '-', '*', '/'):
            if te == 'inteiro' and td == 'inteiro':
                return esq, te, dire, td, 'inteiro'
            esq, te, dire, td = self.promover(esq, te, dire, td)
            return esq, te, dire, td, 'real'
        if op in ('==', '!='):
            if {te, td} <= {'inteiro', 'real'} and te != td:
                esq, te, dire, td = self.promover(esq, te, dire, td)
            return esq, te, dire, td, 'logico'
        if op in ('<', '<=', '>', '>='):
            if te != td:
                esq, te, dire, td = self.promover(esq, te, dire, td)
            return esq, te, dire, td, 'logico'
        return esq, te, dire, td, 'logico'

    def promover(self, esq, te, dire, td):
        if te == 'inteiro' and td == 'real':
            return self.para_real(esq), 'real', dire, td
        if te == 'real' and td == 'inteiro':
            return esq, te, self.para_real(dire), 'real'
        return esq, te, dire, td

    def para_real(self, src):
        destino = self.novo('real')
        self.emitir(Ins('conv', dest=destino, src=src))
        return destino

    def constante(self, tipo, literal):
        destino = self.novo(tipo)
        self.emitir(Ins('const', dest=destino, tipo=tipo, literal=literal))
        return destino

    def padrao(self, tipo):
        if tipo == 'inteiro':
            return self.constante('inteiro', '0')
        if tipo == 'real':
            return self.constante('real', '0.000000')
        if tipo == 'logico':
            return self.constante('logico', 'falso')
        return self.constante('texto', '""')


def _partir(rotulo):
    partes = rotulo.split(' ', 2)
    return partes[1], partes[2]


def gerar(arvore, tabela):
    """Devolve o codigo de tres enderecos."""
    return GeradorIR(tabela).gerar(arvore)


def despejar(codigo):
    """Devolve as linhas do --ir."""
    linhas = []
    for funcao in codigo:
        linhas.append(f'funcao {funcao.nome} {funcao.tipo}')
        for param in funcao.params:
            linhas.append(f'param {param.texto} {param.tipo}')
        for ins in funcao.corpo:
            linhas.append(ins.texto())
        linhas.append('fim')
    return linhas
