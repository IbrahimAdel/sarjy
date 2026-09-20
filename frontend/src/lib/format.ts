const RELATIVE_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 60 * 60 * 24 * 365],
  ["month", 60 * 60 * 24 * 30],
  ["week", 60 * 60 * 24 * 7],
  ["day", 60 * 60 * 24],
  ["hour", 60 * 60],
  ["minute", 60],
  ["second", 1],
]

const relativeFormatter = new Intl.RelativeTimeFormat(undefined, {
  numeric: "auto",
})

export function formatRelativeTime(iso: string): string {
  const timestamp = Date.parse(iso)
  if (Number.isNaN(timestamp)) {
    return ""
  }

  const diffSeconds = Math.round((timestamp - Date.now()) / 1000)
  for (const [unit, seconds] of RELATIVE_UNITS) {
    if (Math.abs(diffSeconds) >= seconds || unit === "second") {
      return relativeFormatter.format(Math.round(diffSeconds / seconds), unit)
    }
  }
  return ""
}
