import { useCallback, useMemo, useRef } from "react"

const WORKLET_URL = `${import.meta.env.BASE_URL}worklets/capture-processor.js`

export type FrameHandler = (frame: ArrayBuffer) => void

export function useMicCapture() {
  const contextRef = useRef<AudioContext | null>(null)
  const moduleRef = useRef<Promise<void> | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const nodeRef = useRef<AudioWorkletNode | null>(null)

  const getContext = useCallback((): AudioContext => {
    if (contextRef.current === null) {
      contextRef.current = new AudioContext()
    }
    return contextRef.current
  }, [])

  const loadModule = useCallback((): Promise<void> => {
    if (moduleRef.current === null) {
      moduleRef.current = getContext().audioWorklet.addModule(WORKLET_URL)
    }
    return moduleRef.current
  }, [getContext])

  // Must be called during a user gesture so the context is allowed to run.
  const prime = useCallback(() => {
    try {
      const context = getContext()
      void context.resume().catch(() => undefined)
      void loadModule().catch(() => undefined)
    } catch {
      // Audio input unsupported; mic capture stays disabled.
    }
  }, [getContext, loadModule])

  const start = useCallback(
    async (onFrame: FrameHandler) => {
      const context = getContext()
      await loadModule()

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      const source = context.createMediaStreamSource(stream)
      const node = new AudioWorkletNode(context, "capture-processor")
      node.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        onFrame(event.data)
      }

      source.connect(node)
      // The processor emits silence; connecting it keeps the graph rendering.
      node.connect(context.destination)

      if (context.state === "suspended") {
        void context.resume().catch(() => undefined)
      }

      streamRef.current = stream
      sourceRef.current = source
      nodeRef.current = node
    },
    [getContext, loadModule]
  )

  const stop = useCallback(() => {
    nodeRef.current?.disconnect()
    nodeRef.current = null
    sourceRef.current?.disconnect()
    sourceRef.current = null
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (contextRef.current) {
      void contextRef.current.close()
    }
    contextRef.current = null
    moduleRef.current = null
  }, [])

  return useMemo(() => ({ prime, start, stop }), [prime, start, stop])
}
