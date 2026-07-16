import { CONFIG } from "./config.js";

const STATE = {
  IDLE: 0,
  ONE_DOWN: 1,
  MOVING: 2,
  TAP_ARMED: 3,
  DRAGGING: 4,
  TWO_DOWN: 5,
  SCROLLING: 6,
  ZOOMING: 7,
  THREE_DOWN: 8,
  SWIPE_CANDIDATE: 9,
  THREE_DRAG: 10,
  FOUR_DOWN: 11
};

export class GestureRecognizer {
  constructor(onGesture, onHaptic) {
    this.onGesture = onGesture;
    this.onHaptic = onHaptic;
    
    this.state = STATE.IDLE;
    this.tapArmTimer = null;
    this.lastTapTime = 0;
    
    this.prevCentroid = null;
    this.prevDistance = null;
    this.locked = false;
    this.startTouches = [];
  }

  _centroid(touches) {
    if (touches.length === 0) return null;
    let sumX = 0, sumY = 0;
    for (let t of touches) {
      sumX += t.x; sumY += t.y;
    }
    return { x: sumX / touches.length, y: sumY / touches.length };
  }

  _distance(t1, t2) {
    const dx = t1.x - t2.x;
    const dy = t1.y - t2.y;
    return Math.sqrt(dx * dx + dy * dy);
  }
  
  _cumulativeMovement(touches) {
    let max = 0;
    for (let t of touches) {
      const d = Math.sqrt(Math.pow(t.x - t.startX, 2) + Math.pow(t.y - t.startY, 2));
      if (d > max) max = d;
    }
    return max;
  }

  handleTouchesChanged(touches, eventType) {
    if (eventType === "start") {
      this.onHaptic("prepare");
    }

    if (touches.length === 0) {
      this._handleAllUp();
      return;
    }
    
    if (!this.locked || eventType === "start") {
      if (touches.length === 1) this._startSession(STATE.ONE_DOWN, touches);
      else if (touches.length === 2) this._startSession(STATE.TWO_DOWN, touches);
      else if (touches.length === 3) this._startSession(STATE.THREE_DOWN, touches);
      else if (touches.length === 4) this._startSession(STATE.FOUR_DOWN, touches);
    }
    
    if (this.state === STATE.ONE_DOWN || this.state === STATE.MOVING || this.state === STATE.DRAGGING || this.state === STATE.TAP_ARMED) {
      this._handleOneFinger(touches, eventType);
    } else if (this.state === STATE.TWO_DOWN || this.state === STATE.SCROLLING || this.state === STATE.ZOOMING) {
      this._handleTwoFinger(touches, eventType);
    } else if (this.state === STATE.THREE_DOWN || this.state === STATE.THREE_DRAG || this.state === STATE.SWIPE_CANDIDATE) {
      this._handleThreeFinger(touches, eventType);
    } else if (this.state === STATE.FOUR_DOWN) {
      this._handleFourFinger(touches, eventType);
    }
  }

  _startSession(newState, touches) {
    if (this.state === STATE.TAP_ARMED && newState === STATE.ONE_DOWN) {
      // Keep TAP_ARMED but update touches
    } else {
      this.state = newState;
    }
    this.locked = true;
    this.startTouches = JSON.parse(JSON.stringify(touches));
    this.prevCentroid = this._centroid(touches);
    if (touches.length === 2) {
      this.prevDistance = this._distance(touches[0], touches[1]);
    }
  }
  
  _applyAccel(dx, dy) {
    const dist = Math.sqrt(dx*dx + dy*dy);
    if (dist === 0) return { dx: 0, dy: 0 };
    let factor = 1.0 + (dist / CONFIG.ACCEL_DIVISOR);
    if (factor > CONFIG.ACCEL_MAX) factor = CONFIG.ACCEL_MAX;
    const finalFactor = factor * CONFIG.SENSITIVITY;
    return { dx: dx * finalFactor, dy: dy * finalFactor };
  }

  _handleOneFinger(touches, eventType) {
    const t = touches[0];
    const centroid = this._centroid(touches);
    
    if (eventType === "move") {
      if (this.prevCentroid) {
        const dx = centroid.x - this.prevCentroid.x;
        const dy = centroid.y - this.prevCentroid.y;
        
        if (this.state === STATE.ONE_DOWN) {
          if (this._cumulativeMovement(touches) > CONFIG.MOVE_THRESHOLD_PX) {
            this.state = STATE.MOVING;
          }
        }
        
        if (this.state === STATE.TAP_ARMED) {
          this.state = STATE.DRAGGING;
          this.onGesture("drag_start", 1);
          this.onHaptic("selection", null);
        }

        if (this.state === STATE.MOVING || this.state === STATE.ONE_DOWN) {
          const accel = this._applyAccel(dx, dy);
          this.onGesture("move", { dx: accel.dx, dy: accel.dy });
        } else if (this.state === STATE.DRAGGING) {
          const accel = this._applyAccel(dx, dy);
          this.onGesture("drag_move", { dx: accel.dx, dy: accel.dy, fingers: 1 });
        }
      }
    }
    
    this.prevCentroid = centroid;
  }

  _handleTwoFinger(touches, eventType) {
    if (touches.length < 2) return;
    const centroid = this._centroid(touches);
    const dist = this._distance(touches[0], touches[1]);

    if (eventType === "move" && this.prevCentroid && this.prevDistance !== null) {
      const dx = centroid.x - this.prevCentroid.x;
      const dy = centroid.y - this.prevCentroid.y;
      const dDist = dist - this.prevDistance;

      if (this.state === STATE.TWO_DOWN) {
        const moveDist = Math.sqrt(dx*dx + dy*dy);
        const cumMove = this._cumulativeMovement(touches);
        if (Math.abs(dist - this._distance(this.startTouches[0], this.startTouches[1])) > CONFIG.PINCH_THRESHOLD_PX) {
          this.state = STATE.ZOOMING;
        } else if (cumMove > CONFIG.SCROLL_THRESHOLD_PX) {
          this.state = STATE.SCROLLING;
        }
      }

      if (this.state === STATE.SCROLLING) {
        this.onGesture("scroll", { dx: dx, dy: dy, phase: "changed" });
      } else if (this.state === STATE.ZOOMING) {
        const scale = dist / this.prevDistance;
        this.onGesture("zoom", { scale, phase: "changed" });
      }
    }

    this.prevCentroid = centroid;
    this.prevDistance = dist;
  }

  _handleThreeFinger(touches, eventType) {
    if (touches.length < 3) return;
    const centroid = this._centroid(touches);

    if (eventType === "move" && this.prevCentroid) {
      const dx = centroid.x - this.prevCentroid.x;
      const dy = centroid.y - this.prevCentroid.y;
      
      const cumMove = this._cumulativeMovement(touches);
      const duration = performance.now() - this.startTouches[0].startT;
      
      if (this.state === STATE.THREE_DOWN) {
        if (cumMove > CONFIG.SWIPE_MIN_DISTANCE_PX) {
          if (duration < CONFIG.SWIPE_MAX_DURATION_MS) {
             this._fireSwipe(3, dx, dy);
             this.state = STATE.SWIPE_CANDIDATE; // Locked to swipe, further move ignored
          } else {
             this.state = STATE.THREE_DRAG;
             this.onGesture("drag_start", 3);
             this.onHaptic("selection", null);
          }
        }
      }

      if (this.state === STATE.THREE_DRAG) {
        this.onGesture("drag_move", { dx: dx, dy: dy, fingers: 3 });
      }
    }

    this.prevCentroid = centroid;
  }
  
  _handleFourFinger(touches, eventType) {
    if (touches.length < 4) return;
    const centroid = this._centroid(touches);

    if (eventType === "move" && this.prevCentroid) {
      const dx = centroid.x - this.prevCentroid.x;
      const dy = centroid.y - this.prevCentroid.y;
      const cumMove = this._cumulativeMovement(touches);
      const duration = performance.now() - this.startTouches[0].startT;

      if (this.state === STATE.FOUR_DOWN) {
        if (cumMove > CONFIG.SWIPE_MIN_DISTANCE_PX && duration < CONFIG.SWIPE_MAX_DURATION_MS) {
          this._fireSwipe(4, dx, dy);
          this.state = STATE.SWIPE_CANDIDATE;
        }
      }
    }
    this.prevCentroid = centroid;
  }

  _fireSwipe(fingers, dx, dy) {
    let direction = "";
    if (Math.abs(dx) > Math.abs(dy)) {
      direction = dx > 0 ? "right" : "left";
    } else {
      direction = dy > 0 ? "down" : "up";
    }
    this.onGesture(`swipe${fingers}`, direction);
    this.onHaptic("impact", "medium");
  }

  _handleAllUp() {
    this.locked = false;
    
    if (this.state === STATE.ONE_DOWN) {
      const duration = performance.now() - this.startTouches[0].startT;
      if (duration < CONFIG.TAP_MAX_DURATION_MS) {
        this.onGesture("click", null);
        this.onHaptic("impact", "light");
        
        this.state = STATE.TAP_ARMED;
        if (this.tapArmTimer) clearTimeout(this.tapArmTimer);
        this.tapArmTimer = setTimeout(() => {
          if (this.state === STATE.TAP_ARMED) {
            this.state = STATE.IDLE;
          }
        }, CONFIG.DRAG_ARM_WINDOW_MS);
        return;
      }
    } else if (this.state === STATE.DRAGGING) {
      this.onGesture("drag_end", 1);
      this.onHaptic("impact", "light");
    } else if (this.state === STATE.TWO_DOWN) {
      const duration = performance.now() - this.startTouches[0].startT;
      if (duration < CONFIG.TAP_MAX_DURATION_MS) {
        this.onGesture("right_click", null);
        this.onHaptic("impact", "medium");
      }
    } else if (this.state === STATE.THREE_DRAG) {
      this.onGesture("drag_end", 3);
      this.onHaptic("impact", "light");
    }
    
    if (this.state !== STATE.TAP_ARMED) {
      this.state = STATE.IDLE;
    }
    
    this.prevCentroid = null;
    this.prevDistance = null;
  }
}
