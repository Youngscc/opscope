// A new configuration invalidates every response belonging to the previous request.
export class EvaluationSession {
  private controller?: AbortController
  begin() { this.cancel(); this.controller = new AbortController(); return this.controller.signal }
  cancel() { this.controller?.abort() }
  current(signal: AbortSignal) { return this.controller?.signal === signal && !signal.aborted }
}
