"""
Entrega 4, segunda metade — geracao do codigo executavel.

Traduz o codigo de tres enderecos para o formato que a VM de voces executa.
O formato do .mplb e de voces, com uma exigencia: tem que ser TEXTO legivel.
Na apresentacao a gente vai abrir um .mplb e ler junto.

Leiam antes: CONTRATOS.md secao 6.
"""

BIN = {
    ('+', 'inteiro'): 'soma_int',
    ('+', 'real'): 'soma_real',
    ('+', 'texto'): 'soma_texto',
    ('-', 'inteiro'): 'sub_int',
    ('-', 'real'): 'sub_real',
    ('*', 'inteiro'): 'mul_int',
    ('*', 'real'): 'mul_real',
    ('/', 'inteiro'): 'div_int',
    ('/', 'real'): 'div_real',
    ('%', 'inteiro'): 'resto',
    ('==', 'logico'): 'igual',
    ('!=', 'logico'): 'diferente',
    ('<', 'logico'): 'menor',
    ('<=', 'logico'): 'menor_igual',
    ('>', 'logico'): 'maior',
    ('>=', 'logico'): 'maior_igual',
    ('e', 'logico'): 'e_logico',
    ('ou', 'logico'): 'ou_logico',
}

UN = {
    ('-', 'inteiro'): 'neg_int',
    ('-', 'real'): 'neg_real',
    ('nao', 'logico'): 'nao',
}


def gerar(codigo_intermediario):
    """Devolve as linhas do arquivo .mplb."""
    linhas = []
    for funcao in codigo_intermediario:
        linhas.append(f'funcao {funcao.nome} {funcao.tipo}')
        linhas.append(f'quadro {funcao.nslots}')
        linhas.append(f'parametros {len(funcao.params)}')
        ultima = None
        for ins in funcao.corpo:
            if ins.linha and ins.linha != ultima and ins.kind != 'rotulo':
                ultima = ins.linha
                linhas.append(f'linha {ins.linha}')
            linhas.extend(_baixar(ins))
        linhas.append('fim')
    linhas.append('inicio principal')
    return linhas


def _baixar(ins):
    k = ins.kind
    if k == 'rotulo':
        return [f'rotulo {ins.nome}']
    if k == 'va_para':
        return [f'  desvie {ins.nome}']
    if k == 'se_falso':
        return [f'  carrega {ins.cond.slot}', f'  desvie_falso {ins.nome}']
    if k == 'const':
        return [_empilha(ins.tipo, ins.literal), f'  guarda {ins.dest.slot}']
    if k == 'bin':
        op = BIN[(ins.op, ins.tipo)]
        return [
            f'  carrega {ins.esq.slot}',
            f'  carrega {ins.dir.slot}',
            f'  {op}',
            f'  guarda {ins.dest.slot}',
        ]
    if k == 'un':
        op = UN[(ins.op, ins.tipo)]
        return [f'  carrega {ins.src.slot}', f'  {op}', f'  guarda {ins.dest.slot}']
    if k == 'conv':
        return [f'  carrega {ins.src.slot}', '  para_real', f'  guarda {ins.dest.slot}']
    if k == 'copia':
        return [f'  carrega {ins.src.slot}', f'  guarda {ins.dest.slot}']
    if k == 'chama':
        linhas = [f'  carrega {arg.slot}' for arg in ins.args]
        linhas.append(f'  chama {ins.nome} {len(ins.args)}')
        if ins.dest is not None:
            linhas.append(f'  guarda {ins.dest.slot}')
        return linhas
    if k == 'retorne':
        if ins.src is None:
            return ['  retorne_vazio']
        return [f'  carrega {ins.src.slot}', '  retorne']
    if k == 'escreva':
        return [f'  carrega {ins.src.slot}', '  escreva']
    return []


def _empilha(tipo, literal):
    if tipo == 'inteiro':
        return f'  empilha_int {literal}'
    if tipo == 'real':
        return f'  empilha_real {literal}'
    if tipo == 'logico':
        return f'  empilha_logico {literal}'
    return f'  empilha_texto {literal}'
