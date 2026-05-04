type StockLinkProps = {
  stockCode?: string | null;
  stockName?: string | null;
  showCode?: boolean;
  className?: string;
};

export function toXueqiuUrl(stockCode?: string | null) {
  if (!stockCode) return "";
  const normalized = stockCode.trim().toUpperCase();
  if (!normalized) return "";
  if (/^(SH|SZ|BJ)\d{6}$/.test(normalized)) {
    return `http://xueqiu.com/S/${normalized}`;
  }
  const match = normalized.match(/^(\d{6})\.(SH|SZ|BJ)$/);
  if (match) {
    return `http://xueqiu.com/S/${match[2]}${match[1]}`;
  }
  return "";
}

export function StockLink({ stockCode, stockName, showCode = true, className }: StockLinkProps) {
  const url = toXueqiuUrl(stockCode);
  const label = [stockName || stockCode, showCode && stockCode ? stockCode : ""].filter(Boolean).join(" ");
  if (!url) {
    return <span className={className}>{label || "-"}</span>;
  }
  return (
    <a className={className || "stock-link"} href={url} target="_blank" rel="noreferrer">
      {label}
    </a>
  );
}
