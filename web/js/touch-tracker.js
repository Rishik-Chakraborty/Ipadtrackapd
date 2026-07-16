export class TouchTracker {
  constructor(element) {
    this.element = element;
    this.touches = new Map();
    this.callbacks = [];

    const opts = { passive: false };
    element.addEventListener("touchstart", (e) => this._handleStart(e), opts);
    element.addEventListener("touchmove", (e) => this._handleMove(e), opts);
    element.addEventListener("touchend", (e) => this._handleEnd(e), opts);
    element.addEventListener("touchcancel", (e) => this._handleEnd(e), opts);
  }

  onChange(callback) {
    this.callbacks.push(callback);
  }

  _fireChange(eventType) {
    const activeTouches = Array.from(this.touches.values());
    for (const cb of this.callbacks) {
      cb(activeTouches, eventType);
    }
  }

  _handleStart(e) {
    e.preventDefault();
    const t = performance.now();
    for (let i = 0; i < e.changedTouches.length; i++) {
      const touch = e.changedTouches[i];
      this.touches.set(touch.identifier, {
        id: touch.identifier,
        x: touch.clientX,
        y: touch.clientY,
        startX: touch.clientX,
        startY: touch.clientY,
        startT: t
      });
    }
    this._fireChange("start");
  }

  _handleMove(e) {
    e.preventDefault();
    for (let i = 0; i < e.changedTouches.length; i++) {
      const touch = e.changedTouches[i];
      if (this.touches.has(touch.identifier)) {
        const state = this.touches.get(touch.identifier);
        state.x = touch.clientX;
        state.y = touch.clientY;
      }
    }
    this._fireChange("move");
  }

  _handleEnd(e) {
    e.preventDefault();
    for (let i = 0; i < e.changedTouches.length; i++) {
      this.touches.delete(e.changedTouches[i].identifier);
    }
    this._fireChange("end");
  }
}
