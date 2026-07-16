let seq = 0;

export function makeMessage(type, payload = {}) {
  return {
    v: 1,
    seq: seq++,
    t: performance.now(),
    type,
    ...payload
  };
}

export const helloMsg = () => makeMessage("hello", { client: "web" });
export const moveMsg = (dx, dy) => makeMessage("move", { dx, dy });
export const clickMsg = () => makeMessage("click", { button: "left" });
export const rightClickMsg = () => makeMessage("right_click");
export const dragStartMsg = (fingers) => makeMessage("drag_start", { fingers });
export const dragMoveMsg = (dx, dy, fingers) => makeMessage("drag_move", { dx, dy, fingers });
export const dragEndMsg = (fingers) => makeMessage("drag_end", { fingers });
export const scrollMsg = (dx, dy, phase) => makeMessage("scroll", { dx, dy, phase });
export const zoomMsg = (scale, phase) => makeMessage("zoom", { scale, phase });
export const swipeMsg = (fingers, direction) => makeMessage(`swipe${fingers}`, { direction });
