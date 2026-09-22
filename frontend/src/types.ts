// Native engine records retain their backend schema; UI fields have explicit contracts.
export type Fields = Record<string, any>
export interface Tensor { name: string; role: string; shape: (number | null)[] | null; dtype: string }
export interface Configuration extends Fields { operator_id: string; operator: string; inputs: Tensor[]; options: Fields; domain?: string }
export interface Fact { label: string; value: string; known: boolean }
export interface Section { key: string; title: string; facts: Fact[]; metadata_facts: Fact[]; extra: string }
export interface Result extends Fields {
  id: string; hardware: string; method: string; available: boolean; synthetic: boolean;
  latency: string; latency_us: number | null; reason: string | null; deviation_percent: number | null;
  matrix: Fields; execution: Fields; details: Record<string, string>; sections: Record<string, Section[]>;
}
export interface Payload extends Fields {
  results: Result[]; pending_results: Result[]; hardware: Fields[]; methods: Fields[];
  catalog: Fields; matrix: Fields; synthetic: boolean;
}
export interface ConfigAPI {
  clone<T>(value: T): T;
  from_operator(op: Fields): Configuration;
  parse_shape(text: string): number[] | null;
  validate(config: Configuration, op: Fields, dtypes: string[]): {field: string; message: string}[];
  matches_demo(config: Configuration, demo: Configuration): boolean;
  workload(config: Configuration): Fields;
  project(config: Configuration, baseline: Result[], templates: Result[], demo: Configuration): Result[];
  public_export(payload: Fields, catalog: Fields): Fields;
}
