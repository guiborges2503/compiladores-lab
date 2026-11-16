// Torres de Hanoi. Cada chamada tem o seu proprio quadro:
// os discos de n-1 andam antes do disco n, e a recursao
// nao mistura a origem, o destino e o auxiliar.

funcao texto algarismo(inteiro n) {
  se (n == 1) {
    retorne "1";
  }
  se (n == 2) {
    retorne "2";
  }
  retorne "3";
}

funcao vazio mover(inteiro n, texto origem, texto destino, texto auxiliar) {
  se (n > 0) {
    mover(n - 1, origem, auxiliar, destino);
    escreva("mova o disco " + algarismo(n) + " de " + origem + " para " + destino);
    mover(n - 1, auxiliar, destino, origem);
  }
}

funcao vazio principal() {
  escreva("Torres de Hanoi com 3 discos");
  mover(3, "A", "C", "B");
}
