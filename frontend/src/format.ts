/** Форматирование слов и интерпретация длинных результатов. */

export function hex(value: number, width = 4): string {
  return value.toString(16).toUpperCase().padStart(width, '0');
}

const WORD_BITS = 16;

/** Слова результата от младшего к старшему → знаковое число (bigint). */
export function signedResult(words: readonly number[]): bigint {
  if (words.length !== 2 && words.length !== 3) {
    throw new Error('Результат должен содержать два или три слова.');
  }
  let value = 0n;
  for (const [index, word] of words.entries()) {
    if (!Number.isInteger(word) || word < 0 || word > 0xffff) {
      throw new Error('Слово результата должно быть целым числом 0…65535.');
    }
    value |= BigInt(word) << BigInt(index * WORD_BITS);
  }
  return BigInt.asIntN(words.length * WORD_BITS, value);
}
