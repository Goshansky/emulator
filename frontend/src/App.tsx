import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { api } from './api/client';
import { EmulatorSession } from './model/session';
import type { Speed } from './model/session';
import type { ProgramExample } from './types';
import { Editor, focusLine } from './components/Editor';
import { Icon } from './components/Icon';
import { Memory } from './components/Memory';
import { ProgramResult } from './components/ProgramResult';
import { Processor } from './components/Processor';

function initialTheme(): 'light' | 'dark' {
  try {
    const saved = localStorage.getItem('emulator-theme');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch { /* Тема работает и без доступа к хранилищу. */ }
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function App() {
  const [model] = useState(() => new EmulatorSession('', '', (callback, delay) => {
    const timer = window.setTimeout(callback, delay);
    return () => window.clearTimeout(timer);
  }));
  const session = useSyncExternalStore(model.subscribe, model.getSnapshot);
  const [theme, setTheme] = useState(initialTheme);
  const [examples, setExamples] = useState<readonly ProgramExample[]>([]);
  const [exampleId, setExampleId] = useState<string>('');
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [speed, setSpeed] = useState<Speed>('normal');
  const [limit, setLimit] = useState('100000');
  const sourceRef = useRef<HTMLTextAreaElement>(null);
  const dataRef = useRef<HTMLTextAreaElement>(null);
  const example = examples.find(item => item.id === exampleId);
  const nextLine = session.assembly?.sourceMap[session.cpu.pc]?.line;
  const activeLine = !session.dirty && session.cpu.instructionAddress !== null
    ? session.assembly?.sourceMap[session.cpu.instructionAddress]?.line : undefined;
  const ready = session.assembly !== null && session.live && !session.dirty && session.cpu.status === 'ready';
  const status = session.running ? 'Выполняется' : session.building ? 'Собирается' : session.dirty ? 'Нужна сборка' : session.cpu.status === 'halted' ? 'Остановлен' : session.cpu.status === 'faulted' ? 'Ошибка CPU' : session.assembly ? 'Готов' : 'Нет программы';

  useEffect(() => () => model.dispose(), [model]);
  useEffect(() => {
    let cancelled = false;
    void api.programs().then(list => {
      if (cancelled || list.length === 0) return;
      setExamples(list);
      setExampleId(list[0]!.id);
      model.setDraft(list[0]!.source, list[0]!.data);
      void model.build();
    }).catch((error: unknown) => {
      if (!cancelled) setCatalogError(error instanceof Error ? error.message : 'Не удалось загрузить каталог программ.');
    });
    return () => { cancelled = true; };
  }, [model]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('emulator-theme', theme); } catch { /* Не влияет на исполнение. */ }
  }, [theme]);
  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && !session.running) {
        event.preventDefault(); void model.build();
      }
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, [model, session.running]);
  useEffect(() => {
    const editor = sourceRef.current;
    if (editor === null || activeLine === undefined) return;
    const y = (activeLine - 1) * 26;
    if (y < editor.scrollTop || y > editor.scrollTop + editor.clientHeight - 52) editor.scrollTop = Math.max(0, y - 78);
  }, [activeLine]);

  return <>
    <a className="skip-link" href="#workspace">К рабочей области</a>
    <header className="app-header"><span className="brand"><span className="brand-icon"><Icon name="chip" /></span>emulator<span className="brand-divider" /><span className="brand-caption">Лаборатория процессора</span></span>
      <nav aria-label="Ссылки приложения"><span className="nav-note">FastAPI · Python + React · TypeScript</span>
        <button className="icon-button" type="button" aria-label={theme === 'light' ? 'Включить тёмную тему' : 'Включить светлую тему'} onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}><Icon name={theme === 'light' ? 'moon' : 'sun'} /></button></nav>
    </header>
    <main id="workspace" className="workspace">
      <div className="workspace-heading"><div><p className="eyebrow">16 бит · Гарвардская архитектура · трёхадресные команды</p><h1>От команды к результату.</h1><p className="intro">Собирайте программу, выполняйте шаги и наблюдайте за состоянием процессора.</p></div>
        <div className="machine-status"><span className={`status-dot ${session.running ? 'running' : session.cpu.status}`} /><span data-testid="status">{status}</span><span className="step-count"><strong data-testid="step-count">{session.cpu.steps}</strong> команд</span></div>
      </div>
      <section className="control-bar" aria-label="Управление выполнением">
        <div className="primary-controls">
          <button type="button" className="button primary" disabled={session.running || session.building} onClick={() => void model.build()} title="Ctrl/⌘ + Enter"><Icon name="build" />Собрать</button>
          <button type="button" className="button" disabled={!ready || session.running || session.building} onClick={() => void model.step()}><Icon name="step" />Шаг</button>
          {session.running ? <button type="button" className="button" onClick={() => model.pause()}><Icon name="pause" />Пауза</button> : <button type="button" className="button" disabled={!ready || session.building} onClick={() => model.run(speed, Number(limit))}><Icon name="play" />Запуск</button>}
          <button type="button" className="button quiet" disabled={session.assembly === null} onClick={() => void model.reset()}><Icon name="reset" />Сброс</button>
        </div>
        <div className="run-settings"><label>Скорость<select value={speed} onChange={event => setSpeed(event.target.value as Speed)} disabled={session.running}><option value="slow">1 команда/с</option><option value="normal">10 команд/с</option><option value="fast">Быстро</option></select></label>
          <label>Лимит команд<input aria-label="Лимит команд" type="number" min="1" max="1000000" step="1" value={limit} disabled={session.running} onChange={event => setLimit(event.target.value)} /></label></div>
      </section>
      {catalogError && <div className="notice error" role="alert">
        <span className="notice-symbol" aria-hidden="true">!</span><span>{catalogError}</span>
      </div>}
      {session.notice && <div className={`notice ${session.notice.kind}`} role={session.notice.kind === 'error' ? 'alert' : 'status'}>
        <span className="notice-symbol" aria-hidden="true">{session.notice.kind === 'error' ? '!' : session.notice.kind === 'success' ? '✓' : 'i'}</span><span>{session.notice.text}</span>
        {session.notice.target && session.notice.line && <button type="button" className="text-button" onClick={() => focusLine(session.notice?.target === 'data' ? dataRef : sourceRef, session.notice?.line ?? 1, session.notice?.column ?? 1)}>К ошибке</button>}
      </div>}
      <div className="workspace-grid">
        <aside className="editor-column" aria-label="Программа и начальные данные">
          <section className="panel source-panel" aria-labelledby="source-title">
            <div className="panel-heading"><h2 id="source-title">Программа</h2><span className={`subtle-tag ${session.dirty ? 'pending' : ''}`}>{session.dirty ? 'Изменено' : `${session.cpu.loadedInstructions} инструкций`}</span></div>
            <div className="example-picker"><label htmlFor="example">Пример</label><select id="example" value={exampleId} disabled={session.running || examples.length === 0} onChange={event => {
              const item = examples.find(entry => entry.id === event.target.value)!;
              setExampleId(item.id); model.setDraft(item.source, item.data); void model.build();
            }}>{examples.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
            <Editor value={session.source} onChange={source => model.setDraft(source, session.dataText)} activeLine={activeLine}
              errorLine={session.notice?.target === 'source' ? session.notice.line : undefined} readOnly={session.running} editorRef={sourceRef} />
            <div className="editor-footer"><span>{!session.dirty && nextLine !== undefined && session.cpu.status === 'ready' ? `Следующая строка: ${nextLine}` : 'Ассемблер · UTF-8'}</span><span>Ctrl / ⌘ + Enter — собрать</span></div>
          </section>
          <section className="panel initial-data-panel" aria-labelledby="initial-data-title">
            <div className="panel-heading"><h2 id="initial-data-title">Начальные данные</h2><span className="subtle-tag">16 бит</span></div>
            <p className="panel-description" id="data-help">Адрес и значения через запятую. Например: <code>0x0100: -7, 12</code></p>
            <textarea ref={dataRef} aria-label="Начальные данные" aria-describedby="data-help" spellCheck={false} value={session.dataText} readOnly={session.running}
              onChange={event => model.setDraft(session.source, event.target.value)} placeholder="0x0100: -7, 12" />
            <p className="panel-footnote">Применяются при сборке. Сброс восстанавливает данные последнего успешно загруженного образа.</p>
          </section>
          <div className="local-note"><Icon name="chip" /><p>Вычисления выполняются на сервере: каждый шаг — запрос к API. Сеанс эмуляции живёт в памяти бэкенда до перезапуска.</p></div>
        </aside>
        <div className="state-column"><Processor session={session} /><ProgramResult session={session} example={example} /><Memory session={session} onLine={line => focusLine(sourceRef, line)} /></div>
      </div>
      <footer className="app-footer"><span>Emulator · пошаговая модель процессора</span><span>17 инструкций · 16 регистров · два блока памяти</span></footer>
    </main>
  </>;
}
