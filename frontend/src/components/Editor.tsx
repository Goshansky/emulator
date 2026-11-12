import { useRef, useState } from 'react';
import type { RefObject } from 'react';

export function focusLine(ref: RefObject<HTMLTextAreaElement>, line: number, column = 1) {
  const editor = ref.current;
  if (editor === null) return;
  const lines = editor.value.split('\n');
  const start = lines.slice(0, line - 1).reduce((offset, text) => offset + text.length + 1, 0) + column - 1;
  editor.focus();
  editor.setSelectionRange(start, Math.max(start + 1, start + (lines[line - 1]?.length ?? 0) - column + 1));
  editor.scrollTop = Math.max(0, (line - 4) * 26);
}

export function Editor({ value, onChange, activeLine, errorLine, readOnly, editorRef }: {
  value: string; onChange: (value: string) => void; activeLine: number | undefined;
  errorLine: number | undefined; readOnly: boolean; editorRef: RefObject<HTMLTextAreaElement>;
}) {
  const [scrollTop, setScrollTop] = useState(0);
  const gutter = useRef<HTMLDivElement>(null);
  return <div className="code-editor">
    <div className="line-gutter" aria-hidden="true"><div ref={gutter} style={{ transform: `translateY(-${scrollTop}px)` }}>
      {value.split('\n').map((_, index) => <div key={index} className={errorLine === index + 1 ? 'error-line' : activeLine === index + 1 ? 'active-line' : ''} data-active={activeLine === index + 1 || undefined}>{index + 1}</div>)}
    </div></div>
    <textarea ref={editorRef} aria-label="Исходный код" value={value} readOnly={readOnly} onChange={event => onChange(event.target.value)}
      spellCheck={false} autoCapitalize="off" autoCorrect="off" wrap="off"
      onScroll={event => setScrollTop(event.currentTarget.scrollTop)} />
  </div>;
}
