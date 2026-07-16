const isNative = () => !!(window.webkit?.messageHandlers?.haptics);

export function impact(style = "light") {
  if (isNative()) window.webkit.messageHandlers.haptics.postMessage({ type: "impact", style });
}
export function selection() {
  if (isNative()) window.webkit.messageHandlers.haptics.postMessage({ type: "selection" });
}
export function notification(style) {
  if (isNative()) window.webkit.messageHandlers.haptics.postMessage({ type: "notification", style });
}
export function prepare() {
  if (isNative()) window.webkit.messageHandlers.haptics.postMessage({ type: "prepare" });
}
