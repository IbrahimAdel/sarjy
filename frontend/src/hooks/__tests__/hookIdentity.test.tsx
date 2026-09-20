import { fireEvent, render, screen } from "@testing-library/react"
import { useState } from "react"
import { beforeEach, describe, expect, it } from "vitest"

import { useMicCapture } from "@/hooks/useMicCapture"
import { usePcmPlayer } from "@/hooks/usePcmPlayer"

let micValues: Array<ReturnType<typeof useMicCapture>> = []
let playerValues: Array<ReturnType<typeof usePcmPlayer>> = []

function Probe() {
  const mic = useMicCapture()
  const player = usePcmPlayer()
  const [, setTick] = useState(0)
  micValues.push(mic)
  playerValues.push(player)
  return (
    <button type="button" onClick={() => setTick((tick) => tick + 1)}>
      rerender
    </button>
  )
}

describe("audio hook identity", () => {
  beforeEach(() => {
    micValues = []
    playerValues = []
  })

  it("keeps a stable object identity across rerenders (regression: socket teardown)", () => {
    const view = render(<Probe />)
    view.rerender(<Probe />)
    view.rerender(<Probe />)

    expect(micValues.length).toBeGreaterThanOrEqual(3)
    expect(micValues.every((value) => value === micValues[0])).toBe(true)
    expect(playerValues.every((value) => value === playerValues[0])).toBe(true)
  })

  it("keeps identity when rerendering from a state update", () => {
    render(<Probe />)
    fireEvent.click(screen.getByRole("button", { name: "rerender" }))
    fireEvent.click(screen.getByRole("button", { name: "rerender" }))

    expect(micValues.length).toBeGreaterThanOrEqual(3)
    expect(micValues.every((value) => value === micValues[0])).toBe(true)
    expect(playerValues.every((value) => value === playerValues[0])).toBe(true)
  })
})
