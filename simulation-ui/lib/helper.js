export function calculateDistance(point1X, point1Y, point2X, point2Y) {
  const dx = point2X - point1X;
  const dy = point2Y - point1Y;
  return Math.sqrt(dx * dx + dy * dy);
}
export const formatNumber = (num) => {
  if (num === 0) return "0";
  if (num < 1) return num.toFixed(3);
  if (num < 100) return num.toFixed(2);
  return Math.round(num).toLocaleString();
};

export const formatMs = (ms) => {
  if (ms < 1000) return `${formatNumber(ms)}ms`;
  return `${formatNumber(ms / 1000)}s`;
};

export default {
  calculateDistance,
  formatNumber,
  formatMs,
};
