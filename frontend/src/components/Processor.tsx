import { hex } from '../format';
import type { SessionSnapshot } from '../model/session';

const signed = (word: number) => word >= 32768 ? word - 65536 : word;
const flagNames = { zf: 'Нулевой результат', nf: 'Знак', cf: 'Перенос / заём', of: 'Знаковое переполнение' } as const;

export function Processor({ session }: { session: SessionSnapshot }) {
  const { cpu, changedRegisters } = session;
  return <>
    <section className="panel instruction-panel" aria-labelledby="instruction-title">
      <div className="panel-heading"><div><p className="eyebrow">Выборка → декодирование → исполнение</p><h2 id="instruction-title">Текущая инструкция</h2></div><span className="subtle-tag">32 бита</span></div>
      <div className="instruction-summary">
        <div><span className="metric-label">Адрес инструкции</span><strong data-testid="instruction-address">{cpu.instructionAddress === null ? '—' : `0x${hex(cpu.instructionAddress)}`}</strong></div>
        <div><span className="metric-label">IR · машинное слово</span><strong data-testid="ir">{cpu.instructionAddress === null ? '—' : hex(cpu.ir, 8)}</strong></div>
        <div><span className="metric-label">PC · следующий адрес</span><strong data-testid="pc">0x{hex(cpu.pc)}</strong></div>
      </div>
      <div className="assembly-line" data-testid="current-instruction">{cpu.decoded?.assembly ?? (cpu.instructionAddress === null ? 'Нажмите «Шаг», чтобы выбрать инструкцию' : 'Ошибка декодирования')}</div>
      {cpu.decoded && <div className="instruction-fields" aria-label="Поля инструкции">
        <span className="format-label">Формат {cpu.decoded.format}</span>
        {Object.entries(cpu.decoded.fields).map(([name, value]) => <span key={name}><small>{name === 'reserved' ? 'Резерв' : name}</small><code>{name === 'OP' ? `0x${hex(value, 2)}` : value}</code></span>)}
      </div>}
      <div className="flag-row">{Object.entries(flagNames).map(([key, title]) => {
        const enabled = cpu.flags[key as keyof typeof flagNames];
        return <div key={key} title={title} className={`flag ${enabled ? 'enabled' : ''}`} data-testid={`flag-${key}`}><span>{key.toUpperCase()}</span><strong>{Number(enabled)}</strong><small>{title}</small></div>;
      })}</div>
    </section>
    <section className="panel registers-panel" aria-labelledby="registers-title">
      <div className="panel-heading"><h2 id="registers-title">Регистры</h2><span className="muted">HEX · знаковое DEC</span></div>
      <div className="register-grid">{cpu.registers.map((value, index) => <div key={index} data-testid={`register-${index}`} className={`register ${changedRegisters.includes(index) ? 'changed' : ''}`}>
        <div><span className="register-name">R{index}</span>{index === 0 ? <small>Аккумулятор</small> : index === 3 ? <small>Счётчик</small> : null}</div>
        <strong>{hex(value)}</strong><span className="signed-value">{signed(value)}</span>
      </div>)}</div>
      <p className="panel-footnote">Подсвечены изменённые регистры. R0 и R3 имеют обычные права; подписи обозначают соглашение примера.</p>
    </section>
  </>;
}
