/** Типы контракта REST API эмулятора (camelCase, как в ответах бэкенда). */

export interface Flags {
  readonly zf: boolean;
  readonly nf: boolean;
  readonly cf: boolean;
  readonly of: boolean;
}

export type CpuStatus = 'ready' | 'halted' | 'faulted';

export interface DecodedInstruction {
  readonly word: number;
  readonly format: 'R' | 'S' | 'X' | 'J' | 'H';
  readonly fields: Readonly<Record<string, number>>;
  readonly instruction: Readonly<Record<string, string | number>>;
  readonly assembly: string;
}

export interface CpuFault {
  readonly code: string;
  readonly message: string;
  readonly address: number;
  readonly word?: number;
}

export interface CpuSnapshot {
  readonly registers: readonly number[];
  readonly pc: number;
  readonly ir: number;
  readonly instructionAddress: number | null;
  readonly decoded: DecodedInstruction | null;
  readonly flags: Flags;
  readonly status: CpuStatus;
  readonly steps: number;
  readonly loadedInstructions: number;
  readonly fault: CpuFault | null;
}

export interface WriteEvent {
  readonly kind: 'register' | 'data';
  readonly address: number;
  readonly before: number;
  readonly after: number;
}

export interface SourceMapEntry {
  readonly address: number;
  readonly line: number;
  readonly column: number;
  readonly text: string;
}

export interface AssemblyResult {
  readonly instructions: readonly number[];
  readonly labels: Readonly<Record<string, number>>;
  readonly sourceMap: readonly SourceMapEntry[];
  readonly disassembly: readonly string[];
}

export interface MemoryView {
  readonly instructions: readonly number[];
  readonly data: readonly number[];
}

export interface MemoryResponse extends MemoryView {
  readonly codeSize: number;
  readonly dataSize: number;
}

export interface SessionResponse {
  readonly sessionId: string;
  readonly assembly: AssemblyResult;
  readonly state: CpuSnapshot;
  readonly memory: MemoryResponse;
}

export interface StateResponse {
  readonly state: CpuSnapshot;
  readonly memory: MemoryResponse;
}

export interface StepResponse {
  readonly executed: boolean;
  readonly executedCount: number;
  readonly state: CpuSnapshot;
  readonly writes: readonly WriteEvent[];
}

export interface ErrorDiagnostic {
  readonly code: string;
  readonly message: string;
  readonly target: 'source' | 'data' | 'machine';
  readonly line?: number | null;
  readonly column?: number | null;
}

export interface ProgramExample {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly source: string;
  readonly data: string;
  readonly resultWords?: number | null;
}
