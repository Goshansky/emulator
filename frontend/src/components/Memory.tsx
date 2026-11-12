import { useState } from 'react';
import { hex } from '../format';
import type { SessionSnapshot } from '../model/session';

const CODE_SIZE = 1024;
const DATA_SIZE = 4096;

function parseAddress(text: string, maximum: number): number | null {
  if (!/^(?:0x[0-9a-f]+|[0-9]+)$/i.test(text.trim())) return null;
  const value = Number(text.trim());
  return Number.isInteger(value) && value >= 0 && value < maximum ? value : null;
}

export function Memory({ session, onLine }: { session: SessionSnapshot; onLine: (line: number) => void }) {
  const [tab, setTab] = useState<'code' | 'data'>('code');
  const [codeAddress, setCodeAddress] = useState('0');
  const [dataAddress, setDataAddress] = useState('0x0300');
  const text = tab === 'code' ? codeAddress : dataAddress;
  const maximum = tab === 'code' ? CODE_SIZE : DATA_SIZE;
  const base = parseAddress(text, maximum);
  const setAddress = tab === 'code' ? setCodeAddress : setDataAddress;
  const size = tab === 'code' ? 8 : 16;
  return <section className="panel memory-panel" aria-labelledby="memory-title">
    <div className="panel-heading"><h2 id="memory-title">Память</h2><div className="segmented" aria-label="Адресное пространство">
      <button type="button" aria-pressed={tab === 'code'} onClick={() => setTab('code')}>Команды</button>
      <button type="button" aria-pressed={tab === 'data'} onClick={() => setTab('data')}>Данные</button>
    </div></div>
    <div className="memory-controls"><label>Адрес <input aria-label="Адрес просмотра" value={text} onChange={event => setAddress(event.target.value)} spellCheck={false} /></label>
      <button type="button" className="text-button" onClick={() => setAddress(tab === 'code' ? String(Math.min(session.cpu.pc, maximum - 1)) : '0x0100')}>{tab === 'code' ? 'К PC' : 'К данным'}</button>
      {tab === 'data' && <button type="button" className="text-button" onClick={() => setDataAddress('0x0300')}>К результату</button>}
      <span className="muted">{maximum} × {tab === 'code' ? 32 : 16} бит</span>
    </div>
    {base === null ? <p role="alert" className="inline-error">Адрес должен быть от 0 до {maximum - 1}, в десятичном или hex-виде.</p> : tab === 'code' ?
      <div className="table-scroll"><table className="code-memory"><thead><tr><th>Адрес</th><th>Машинное слово</th><th>Инструкция</th><th>Исходник</th></tr></thead><tbody>
        {Array.from({ length: Math.min(size, maximum - base) }, (_, index) => {
          const address = base + index;
          const loaded = address < session.cpu.loadedInstructions;
          const word = session.memory.instructions[address] ?? 0;
          const line = session.assembly?.sourceMap[address]?.line;
          const disassembly = session.assembly?.disassembly[address];
          return <tr key={address} className={session.cpu.instructionAddress === address ? 'current-row' : ''}>
            <td><span className="pc-marker" aria-label={session.cpu.pc === address ? 'Следующая инструкция' : undefined}>{session.cpu.pc === address ? '→' : ''}</span>{hex(address)}</td>
            <td>{hex(word, 8)}</td><td>{loaded ? disassembly ?? '—' : <span className="muted">Не загружено</span>}</td>
            <td>{line === undefined ? '—' : <button type="button" className="text-button" disabled={session.dirty} onClick={() => onLine(line)}>Строка {line}</button>}</td>
          </tr>;
        })}
      </tbody></table></div> :
      <div className="data-grid">{Array.from({ length: Math.min(size, maximum - base) }, (_, index) => {
        const address = base + index;
        const value = session.memory.data[address] ?? 0;
        return <div key={address} data-testid={`data-${address}`} className={`data-cell ${session.changedData.includes(address) ? 'changed' : ''}`}>
          <small>0x{hex(address)}</small><strong>{hex(value)}</strong><span>{value >= 32768 ? value - 65536 : value}</span>
        </div>;
      })}</div>}
    <div className="memory-footer"><span className="muted">{tab === 'code' ? '→ следующий PC · синий фон — выбранная команда' : 'HEX · знаковое DEC · адреса слов'}</span>
      <div><button type="button" aria-label="Предыдущие ячейки" disabled={base === null || base === 0} onClick={() => setAddress(String(Math.max(0, (base ?? 0) - size)))}>←</button>
        <button type="button" aria-label="Следующие ячейки" disabled={base === null || base + size >= maximum} onClick={() => setAddress(String((base ?? 0) + size))}>→</button></div>
    </div>
  </section>;
}
