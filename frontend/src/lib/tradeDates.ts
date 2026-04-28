export function dateToString(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function stringToDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function todayString() {
  return dateToString(new Date());
}

export function shiftTradeDate(current: string, step: -1 | 1) {
  const next = stringToDate(current);
  next.setDate(next.getDate() + step);
  return dateToString(next);
}
