import { act, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  micStart: vi.fn(async (_onFrame?: (frame: ArrayBuffer) => void) => undefined),
  micStop: vi.fn(),
  micPrime: vi.fn(),
  playerResume: vi.fn(async () => undefined),
  playerPush: vi.fn(),
  playerStop: vi.fn(),
  playerPrime: vi.fn(),
  refresh: vi.fn(async () => "token"),
  ensureAccessToken: vi.fn(async () => "token"),
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    refresh: mocks.refresh,
    ensureAccessToken: mocks.ensureAccessToken,
  }),
}))

vi.mock("@/hooks/useMicCapture", () => {
  const value = {
    prime: mocks.micPrime,
    start: mocks.micStart,
    stop: mocks.micStop,
  }
  return { useMicCapture: () => value }
})

vi.mock("@/hooks/usePcmPlayer", () => {
  const value = {
    prime: mocks.playerPrime,
    resume: mocks.playerResume,
    push: mocks.playerPush,
    stop: mocks.playerStop,
  }
  return { usePcmPlayer: () => value }
})

import { useVoiceConversation } from "@/hooks/useVoiceConversation"

class MockWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3
  static instances: MockWebSocket[] = []

  readyState: number = MockWebSocket.CONNECTING
  binaryType = ""
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string | ArrayBuffer }) => void) | null = null
  onclose: ((event: { code: number }) => void) | null = null
  onerror: (() => void) | null = null
  readonly sent: unknown[] = []

  readonly url: string

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  send = vi.fn((data: unknown) => {
    this.sent.push(data)
  })

  close = vi.fn((code = 1000) => {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({ code })
  })

  open() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.()
  }
}

function Probe() {
  const { phase, connected, start, stop, sendText } = useVoiceConversation()
  const [, setTick] = useState(0)
  return (
    <div>
      <span data-testid="phase">{phase}</span>
      <span data-testid="connected">{String(connected)}</span>
      <button type="button" onClick={start}>
        start
      </button>
      <button type="button" onClick={stop}>
        stop
      </button>
      <button type="button" onClick={() => void sendText("hello")}>
        send
      </button>
      <button type="button" onClick={() => setTick((tick) => tick + 1)}>
        rerender
      </button>
    </div>
  )
}

describe("useVoiceConversation", () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.clearAllMocks()
    window.localStorage.setItem("sarjy.conversation_id", "conv-1")
    vi.stubGlobal("WebSocket", MockWebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("keeps the socket open across rerenders and forwards frames and text", async () => {
    render(<Probe />)
    fireEvent.click(screen.getByRole("button", { name: "start" }))

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))
    const socket = MockWebSocket.instances[0]
    expect(socket.url).toContain("/ws/audio?token=token")
    expect(socket.url).toContain("conversation_id=conv-1")

    // Reuses the cached token and primes audio during the click gesture.
    expect(mocks.ensureAccessToken).toHaveBeenCalled()
    expect(mocks.refresh).not.toHaveBeenCalled()
    expect(mocks.micPrime).toHaveBeenCalled()
    expect(mocks.playerPrime).toHaveBeenCalled()

    await act(async () => {
      socket.open()
    })

    await waitFor(() =>
      expect(screen.getByTestId("connected")).toHaveTextContent("true")
    )
    await waitFor(() =>
      expect(screen.getByTestId("phase")).toHaveTextContent("live")
    )
    expect(socket.sent[0]).toContain('"event":"start"')

    // Rerendering must not run the teardown cleanup and close the socket.
    fireEvent.click(screen.getByRole("button", { name: "rerender" }))
    fireEvent.click(screen.getByRole("button", { name: "rerender" }))
    expect(socket.close).not.toHaveBeenCalled()

    const onFrame = mocks.micStart.mock.calls[0]?.[0]
    const frame = new Int16Array(480).buffer
    act(() => onFrame?.(frame))
    expect(socket.send).toHaveBeenCalledWith(frame)

    fireEvent.click(screen.getByRole("button", { name: "send" }))
    expect(socket.send).toHaveBeenCalledWith(
      JSON.stringify({ event: "user_transcript", text: "hello" })
    )

    fireEvent.click(screen.getByRole("button", { name: "stop" }))
    expect(socket.close).toHaveBeenCalled()
  })

  it("opens the socket even if audio setup never finishes", async () => {
    mocks.playerResume.mockImplementation(
      () => new Promise<undefined>(() => undefined)
    )

    render(<Probe />)
    fireEvent.click(screen.getByRole("button", { name: "start" }))

    await waitFor(
      () => expect(MockWebSocket.instances).toHaveLength(1),
      { timeout: 3000 }
    )

    mocks.playerResume.mockImplementation(async () => undefined)
  })
})
