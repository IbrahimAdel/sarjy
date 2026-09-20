// Playback worklet: receives 16 kHz mono PCM16 frames from the main thread,
// resamples them to the context rate and streams them to the speakers.
const SOURCE_RATE = 16000

class PlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.ratio = SOURCE_RATE / sampleRate
    this.pending = new Float32Array(0)
    this.readPos = 0
    this.port.onmessage = (event) => this._enqueue(event.data)
  }

  _enqueue(data) {
    const int16 = new Int16Array(data)
    const floats = new Float32Array(int16.length)
    for (let i = 0; i < int16.length; i += 1) {
      floats[i] = int16[i] / 32768
    }
    const merged = new Float32Array(this.pending.length + floats.length)
    merged.set(this.pending)
    merged.set(floats, this.pending.length)
    this.pending = merged
  }

  process(_inputs, outputs) {
    const channel = outputs[0][0]
    for (let i = 0; i < channel.length; i += 1) {
      if (this.readPos + 1 < this.pending.length) {
        const index = Math.floor(this.readPos)
        const frac = this.readPos - index
        channel[i] =
          this.pending[index] * (1 - frac) + this.pending[index + 1] * frac
        this.readPos += this.ratio
      } else {
        channel[i] = 0
      }
    }

    const consumed = Math.floor(this.readPos)
    if (consumed > 0) {
      this.pending = this.pending.slice(consumed)
      this.readPos -= consumed
    }
    return true
  }
}

registerProcessor("player-processor", PlayerProcessor)
