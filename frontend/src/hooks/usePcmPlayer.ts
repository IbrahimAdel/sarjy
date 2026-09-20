import { useCallback, useMemo, useRef } from "react"

const WORKLET_URL = `${import.meta.env.BASE_URL}worklets/player-processor.js`

export function usePcmPlayer() {
  const contextRef = useRef<AudioContext | null>(null)
  const nodeRef = useRef<AudioWorkletNode | null>(null)
  const readyRef = useRef<Promise<void> | null>(null)

  // Must be called during a user gesture so the context is allowed to run.
  const prime = useCallback(() => {
    try {
      if (contextRef.current === null) {
        contextRef.current = new AudioContext({ sampleRate: 16000 })
      }
      void contextRef.current.resume().catch(() => undefined)
    } catch {
      // Audio output unsupported; playback stays disabled.
    }
  }, [])

  const ensure = useCallback((): Promise<void> => {
    if (readyRef.current === null) {
      readyRef.current = (async () => {
        const context =
          contextRef.current ?? new AudioContext({ sampleRate: 16000 })
        contextRef.current = context
        await context.audioWorklet.addModule(WORKLET_URL)
        const node = new AudioWorkletNode(context, "player-processor")
        node.connect(context.destination)
        nodeRef.current = node
      })()
    }
    return readyRef.current
  }, [])

  const resume = useCallback(async () => {
    await ensure()
    const context = contextRef.current
    if (context?.state === "suspended") {
      // Fire-and-forget: resume() can stay pending under autoplay policies.
      void context.resume().catch(() => undefined)
    }
  }, [ensure])

  const push = useCallback((data: ArrayBuffer) => {
    nodeRef.current?.port.postMessage(data, [data])
  }, [])

  const stop = useCallback(() => {
    nodeRef.current?.disconnect()
    nodeRef.current = null
    if (contextRef.current) {
      void contextRef.current.close()
    }
    contextRef.current = null
    readyRef.current = null
  }, [])

  return useMemo(
    () => ({ prime, resume, push, stop }),
    [prime, resume, push, stop]
  )
}
