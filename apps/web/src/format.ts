export function formatBytesGiB(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "sin datos";
  const gib = bytes / (1024 * 1024 * 1024);
  return `${gib.toFixed(1)} GiB`;
}

export function formatBytesAuto(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return "sin datos";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = -1;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex++;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

export function formatMetric(value: number | null | undefined, unit = ""): string {
  if (value === null || value === undefined) return "sin datos";
  return `${value.toFixed(1)}${unit}`;
}

const dateFormatter = new Intl.DateTimeFormat("es-CL", {
  timeZone: "America/Santiago",
  dateStyle: "short",
  timeStyle: "short",
});

export function formatDateSantiago(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return dateFormatter.format(d);
}
