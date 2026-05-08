type StockLinkProps = {
  stockCode?: string | null;
  stockName?: string | null;
  showCode?: boolean;
  className?: string;
};

function normalizeXueqiuCode(stockCode: string): string {
  const normalized = stockCode.trim().toUpperCase();
  if (/^(SH|SZ|BJ)\d{6}$/.test(normalized)) {
    return normalized;
  }
  const match = normalized.match(/^(\d{6})\.(SH|SZ|BJ)$/);
  if (match) {
    return `${match[2]}${match[1]}`;
  }
  return "";
}

export function toXueqiuUrl(stockCode?: string | null) {
  if (!stockCode) return "";
  const code = normalizeXueqiuCode(stockCode);
  return code ? `https://xueqiu.com/S/${code}` : "";
}

export function StockLink({ stockCode, stockName, showCode = true, className }: StockLinkProps) {
  const url = toXueqiuUrl(stockCode);
  const label = [stockName || stockCode, showCode && stockCode ? stockCode : ""].filter(Boolean).join(" ");
  if (!url) {
    return <span className={className}>{label || "-"}</span>;
  }
  return (
    <a
      className={className || "stock-link"}
      href={url}
      onClick={(e) => {
        e.preventDefault();
        // Direct location change triggers Universal Links (iOS) / App Links (Android)
        // which opens the Xueqiu app if installed, otherwise falls back to browser
        window.location.href = url;
      }}
    >
      {label}
    </a>
  );
}
