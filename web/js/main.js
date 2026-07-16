import { CONFIG } from "./config.js";
import { TouchTracker } from "./touch-tracker.js";
import { GestureRecognizer } from "./gesture-recognizer.js";
import * as haptics from "./haptics.js";
import * as protocol from "./protocol.js";

let ws = null;
let reconnectTimer = null;
let reconnectAttempts = 0;

const statusDot = document.getElementById("status");

function connectWS() {
  const wsUrl = window.location.origin.replace(/^http/, "ws") + CONFIG.WS_PATH;
  statusDot.className = "connecting";
  
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    statusDot.className = "connected";
    haptics.notification("success");
    reconnectAttempts = 0;
    ws.send(JSON.stringify(protocol.helloMsg()));
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "hello_ack") {
        console.log("Connected to server. Screen size:", msg.macScreen);
      }
    } catch (e) {
      console.error("Failed to parse WS message", e);
    }
  };

  ws.onclose = () => {
    statusDot.className = "";
    if (reconnectAttempts === 0) {
      haptics.notification("error");
    }
    scheduleReconnect();
  };

  ws.onerror = () => {
    // onclose will handle reconnection
  };
}

function scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  const backoff = Math.min(CONFIG.RECONNECT_BASE_MS * Math.pow(2, reconnectAttempts), CONFIG.RECONNECT_MAX_MS);
  reconnectAttempts++;
  reconnectTimer = setTimeout(connectWS, backoff);
}

function sendGesture(type, payload) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;

  let msg;
  if (type === "move") msg = protocol.moveMsg(payload.dx, payload.dy);
  else if (type === "click") msg = protocol.clickMsg();
  else if (type === "right_click") msg = protocol.rightClickMsg();
  else if (type === "drag_start") msg = protocol.dragStartMsg(payload.fingers);
  else if (type === "drag_move") msg = protocol.dragMoveMsg(payload.dx, payload.dy, payload.fingers);
  else if (type === "drag_end") msg = protocol.dragEndMsg(payload.fingers);
  else if (type === "scroll") msg = protocol.scrollMsg(payload.dx, payload.dy, payload.phase);
  else if (type === "zoom") msg = protocol.zoomMsg(payload.scale, payload.phase);
  else if (type === "swipe3") msg = protocol.swipeMsg(3, payload.direction);
  else if (type === "swipe4") msg = protocol.swipeMsg(4, payload.direction);
  
  if (msg) {
    ws.send(JSON.stringify(msg));
  }
}

function init() {
  const surface = document.getElementById("surface");
  
  const recognizer = new GestureRecognizer(
    (type, payload) => sendGesture(type, payload),
    (kind, style) => {
      if (kind === "impact") haptics.impact(style);
      else if (kind === "selection") haptics.selection();
      else if (kind === "prepare") haptics.prepare();
    }
  );

  const tracker = new TouchTracker(surface);
  tracker.onChange((touches, eventType) => {
    recognizer.handleTouchesChanged(touches, eventType);
  });

  connectWS();
}

window.addEventListener("DOMContentLoaded", init);
