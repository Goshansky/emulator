import { api, ApiError } from '../api/client';
import type {
  AssemblyResult,
  CpuSnapshot,
  MemoryView,
  WriteEvent,
} from '../types';

export type Schedule = (callback: () => void, delay: number) => () => void;
export type Speed = 'slow' | 'normal' | 'fast';

export interface Notice {
  readonly kind: 'info' | 'success' | 'error';
  readonly text: string;
  readonly target?: 'source' | 'data';
  readonly line?: number;
  readonly column?: number;
}

export interface SessionSnapshot {
  readonly source: string;
  readonly dataText: string;
  readonly assembly: AssemblyResult | null;
  readonly cpu: CpuSnapshot;
  readonly memory: MemoryView;
  readonly running: boolean;
  readonly building: boolean;
  readonly live: boolean;
  readonly dirty: boolean;
  readonly notice: Notice | null;
  readonly changedRegisters: readonly number[];
  readonly changedData: readonly number[];
  readonly runSteps: number;
}

const EMPTY_FLAGS = { zf: false, nf: false, cf: false, of: false } as const;

const EMPTY_CPU: CpuSnapshot = {
  registers: [],
  pc: 0,
  ir: 0,
  instructionAddress: null,
  decoded: null,
  flags: EMPTY_FLAGS,
  status: 'ready',
  steps: 0,
  loadedInstructions: 0,
  fault: null,
};

const EMPTY_MEMORY: MemoryView = { instructions: [], data: [] };

function changedAddresses(writes: readonly WriteEvent[], kind: WriteEvent['kind']): number[] {
  return [...new Set(writes.filter(write => write.kind === kind).map(write => write.address))];
}

/** Сеанс эмуляции поверх REST API. Планировщик внедряется, модель не зависит от DOM. */
export class EmulatorSession {
  #sessionId: string | null = null;
  #listeners = new Set<() => void>();
  #source: string;
  #dataText: string;
  #compiledSource: string | null = null;
  #compiledData: string | null = null;
  #assembly: AssemblyResult | null = null;
  #cpu: CpuSnapshot = EMPTY_CPU;
  #memory: MemoryView = EMPTY_MEMORY;
  #running = false;
  #building = false;
  #executing = false;
  #cancel: (() => void) | null = null;
  #generation = 0;
  #runSteps = 0;
  #snapshot: SessionSnapshot;

  constructor(
    source: string,
    dataText: string,
    private readonly schedule: Schedule,
  ) {
    this.#source = source;
    this.#dataText = dataText;
    this.#snapshot = this.#makeSnapshot(null, [], []);
  }

  // React useSyncExternalStore требует стабильный снимок до следующего изменения.
  getSnapshot = (): SessionSnapshot => this.#snapshot;

  subscribe = (listener: () => void): (() => void) => {
    this.#listeners.add(listener);
    return () => { this.#listeners.delete(listener); };
  };

  setDraft(source: string, dataText: string): void {
    this.#stop();
    this.#source = source;
    this.#dataText = dataText;
    this.#publish({
      kind: 'info',
      text: this.#dirty()
        ? 'Есть изменения. Соберите программу перед выполнением.'
        : 'Исходник соответствует загруженной программе.',
    });
  }

  async build(): Promise<boolean> {
    this.#stop();
    const generation = this.#generation;
    this.#building = true;
    this.#publish({ kind: 'info', text: 'Сборка программы…' });
    try {
      const response = await api.createSession(this.#source, this.#dataText);
      if (generation !== this.#generation) return false; // пришла новая сборка/сброс
      this.#sessionId = response.sessionId;
      this.#assembly = response.assembly;
      this.#cpu = response.state;
      this.#memory = {
        instructions: [...response.memory.instructions],
        data: [...response.memory.data],
      };
      this.#compiledSource = this.#source;
      this.#compiledData = this.#dataText;
      this.#runSteps = 0;
      this.#building = false;
      this.#publish({
        kind: 'success',
        text: `Собрано инструкций: ${response.assembly.instructions.length}. Программа готова к запуску.`,
      });
      return true;
    } catch (error) {
      if (generation !== this.#generation) return false;
      this.#building = false;
      if (error instanceof ApiError && error.diagnostic !== null) {
        const d = error.diagnostic;
        this.#publish({
          kind: 'error',
          text: d.message,
          target: d.target === 'machine' ? undefined : d.target,
          line: d.line ?? undefined,
          column: d.column ?? undefined,
        });
      } else {
        this.#publish({ kind: 'error', text: 'Не удалось собрать программу.' });
      }
      return false;
    }
  }

  async step(): Promise<void> {
    if (this.#running || this.#building || this.#executing || !this.#canExecute()) return;
    this.#executing = true;
    try {
      const response = await api.steps(this.#sessionId!, 1);
      this.#applyExecution(response.state, response.writes);
      this.#publish(this.#executionNotice(response.state), response.writes);
    } catch (error) {
      this.#publish(this.#apiNotice(error));
    } finally {
      this.#executing = false;
    }
  }

  run(speed: Speed, maxSteps: number): void {
    if (this.#running || this.#building || !this.#canExecute()) return;
    if (!Number.isSafeInteger(maxSteps) || maxSteps < 1 || maxSteps > 1_000_000) {
      this.#publish({ kind: 'error', text: 'Лимит должен быть целым числом от 1 до 1000000.' });
      return;
    }
    const size = speed === 'fast' ? 250 : 1;
    const delay = speed === 'slow' ? 1000 : speed === 'normal' ? 100 : 16;
    this.#runSteps = 0;
    this.#running = true;
    const generation = ++this.#generation;
    this.#publish({ kind: 'info', text: 'Программа выполняется.' });

    const tick = () => {
      if (!this.#running || generation !== this.#generation) return;
      this.#cancel = null;
      const remaining = Math.min(size, maxSteps - this.#runSteps);
      void this.#runBatch(remaining).then(({ state, writes }) => {
        if (!this.#running || generation !== this.#generation) return;
        if (state.status !== 'ready') {
          this.#running = false;
          this.#publish(this.#executionNotice(state), writes);
        } else if (this.#runSteps >= maxSteps) {
          this.#running = false;
          this.#publish(
            { kind: 'info', text: `Пауза: достигнут лимит ${maxSteps} команд. Можно продолжить выполнение.` },
            writes,
          );
        } else {
          this.#publish({ kind: 'info', text: 'Программа выполняется.' }, writes);
          if (this.#running && generation === this.#generation) this.#cancel = this.schedule(tick, delay);
        }
      }).catch((error: unknown) => {
        if (!this.#running || generation !== this.#generation) return;
        this.#running = false;
        this.#publish(this.#apiNotice(error));
      });
    };
    this.#cancel = this.schedule(tick, delay);
  }

  pause(): void {
    if (!this.#running) return;
    this.#stop();
    this.#publish({ kind: 'info', text: 'Выполнение приостановлено.' });
  }

  async reset(): Promise<void> {
    this.#stop();
    if (this.#sessionId === null) return;
    try {
      const response = await api.reset(this.#sessionId);
      this.#cpu = response.state;
      this.#memory = {
        instructions: [...response.memory.instructions],
        data: [...response.memory.data],
      };
      this.#runSteps = 0;
      this.#publish({
        kind: 'info',
        text: this.#dirty()
          ? 'Загруженная программа сброшена. Изменения редактора ещё не собраны.'
          : 'Регистры и память восстановлены из начального образа.',
      });
    } catch (error) {
      this.#publish(this.#apiNotice(error));
    }
  }

  dispose(): void {
    this.#stop();
    this.#listeners.clear();
  }

  async #runBatch(count: number): Promise<{ state: CpuSnapshot; writes: WriteEvent[] }> {
    const response = await api.steps(this.#sessionId!, count);
    this.#runSteps += response.executedCount;
    this.#applyExecution(response.state, response.writes);
    return { state: response.state, writes: [...response.writes] };
  }

  #applyExecution(state: CpuSnapshot, writes: readonly WriteEvent[]): void {
    const data = [...this.#memory.data];
    for (const write of writes) {
      if (write.kind === 'data') data[write.address] = write.after;
    }
    this.#cpu = state;
    this.#memory = { instructions: this.#memory.instructions, data };
  }

  #dirty(): boolean {
    return this.#source !== this.#compiledSource || this.#dataText !== this.#compiledData;
  }

  #canExecute(): boolean {
    return (
      this.#sessionId !== null &&
      this.#assembly !== null &&
      !this.#dirty() &&
      this.#cpu.status === 'ready'
    );
  }

  #stop(): void {
    this.#running = false;
    this.#generation += 1;
    this.#cancel?.();
    this.#cancel = null;
  }

  #executionNotice(state: CpuSnapshot): Notice {
    if (state.fault !== null) {
      return {
        kind: 'error',
        text: `Адрес 0x${state.fault.address.toString(16).toUpperCase()}: ${state.fault.message}`,
      };
    }
    if (state.status === 'halted') {
      return { kind: 'success', text: `Программа остановлена командой HALT. Выполнено команд: ${state.steps}.` };
    }
    return { kind: 'info', text: `Выполнен шаг ${state.steps}.` };
  }

  #apiNotice(error: unknown): Notice {
    if (error instanceof ApiError) {
      if (error.diagnostic?.code === 'SESSION_NOT_FOUND') {
        this.#sessionId = null;
        return { kind: 'error', text: error.diagnostic.message };
      }
      return { kind: 'error', text: error.diagnostic?.message ?? 'Ошибка запроса к серверу.' };
    }
    return { kind: 'error', text: 'Неизвестная ошибка выполнения.' };
  }

  #publish(notice: Notice | null, writes: readonly WriteEvent[] = []): void {
    this.#snapshot = this.#makeSnapshot(notice, changedAddresses(writes, 'register'), changedAddresses(writes, 'data'));
    for (const listener of this.#listeners) listener();
  }

  #makeSnapshot(notice: Notice | null, changedRegisters: number[], changedData: number[]): SessionSnapshot {
    return {
      source: this.#source,
      dataText: this.#dataText,
      assembly: this.#assembly,
      cpu: this.#cpu,
      memory: this.#memory,
      running: this.#running,
      building: this.#building,
      live: this.#sessionId !== null,
      dirty: this.#dirty(),
      notice,
      changedRegisters,
      changedData,
      runSteps: this.#runSteps,
    };
  }
}
