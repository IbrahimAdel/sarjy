// Capture worklet: resamples microphone audio to 16 kHz mono PCM16 and posts
// batched frames to the main thread (one WebSocket message per interval).
const TARGET_RATE = 16000
const SEND_INTERVAL_MS = 500
const FRAME_SAMPLES = (TARGET_RATE * SEND_INTERVAL_MS) / 1000

class CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.ratio = sampleRate / TARGET_RATE
    this.pending = new Float32Array(0)
    this.readPos = 0
    this.out = new Int16Array(FRAME_SAMPLES)
    this.outCount = 0
  }

  _append(chunk) {
    const merged = new Float32Array(this.pending.length + chunk.length)
    merged.set(this.pending)
    merged.set(chunk, this.pending.length)
    this.pending = merged
  }

  _emit(sample) {
    const clamped = Math.max(-1, Math.min(1, sample))
    this.out[this.outCount] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
    this.outCount += 1
    if (this.outCount === FRAME_SAMPLES) {
      const buffer = this.out.buffer.slice(0)
      this.port.postMessage(buffer, [buffer])
      this.out = new Int16Array(FRAME_SAMPLES)
      this.outCount = 0
    }
  }

  _resample() {
    while (this.readPos + 1 < this.pending.length) {
      const index = Math.floor(this.readPos)
      const frac = this.readPos - index
      this._emit(this.pending[index] * (1 - frac) + this.pending[index + 1] * frac)
      this.readPos += this.ratio
    }

    const consumed = Math.floor(this.readPos)
    if (consumed > 0) {
      this.pending = this.pending.slice(consumed)
      this.readPos -= consumed
    }
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (channel) {
      this._append(channel)
      this._resample()
    }
    return true
  }
}

registerProcessor("capture-processor", CaptureProcessor)
