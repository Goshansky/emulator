import { hex, signedResult } from '../format';
import type { SessionSnapshot } from '../model/session';
import type { ProgramExample } from '../types';

export function ProgramResult({ session, example }: { session: SessionSnapshot; example: ProgramExample | undefined }) {
  // Назначение памяти известно только для неизменённого исходника этого примера.
  if (!example?.resultWords || session.dirty || session.source !== example.source) return null;
  const width = example.resultWords;
  const words = Array.from({ length: width }, (_, i) => session.memory.data[0x300 + i] ?? 0);
  const complete = session.cpu.status === 'halted';
  const invalidLength = complete && width === 3 && (session.memory.data[0x303] ?? 0) !== 0;
  return <section className="panel" aria-labelledby="result-title">
    <div className="panel-heading"><h2 id="result-title">Результат программы</h2><span className="subtle-tag">{width * 16} бит</span></div>
    <p className="panel-description">{example.description}</p>
    <div className="assembly-line" data-testid="program-result">{invalidLength
      ? 'Неверная длина: оба массива должны содержать 10 элементов. Статус 1; результат не записан.'
      : complete ? <><strong>{signedResult(words).toString()}</strong><br /><span>Слова от младшего к старшему: {words.map(word => hex(word)).join(' · ')}</span></>
        : 'Итог появится после HALT. Промежуточные значения доступны в регистрах.'}</div>
    <p className="panel-footnote">{width === 3 ? 'Статус в 0x0303: 0 — успех, 1 — неверная длина. ' : 'Длина массива: 0…15; заголовок не входит в сумму. '}Число прочитано из памяти данных с адреса 0x0300.</p>
  </section>;
}
