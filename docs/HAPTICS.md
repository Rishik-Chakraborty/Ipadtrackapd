# Haptics Bridge

The native iOS wrapper bridges WebKit messages to Taptic Engine haptics. The message schema is as follows:

```json
{ "type": "impact", "style": "light" | "medium" | "heavy" | "rigid" | "soft" }
{ "type": "selection" }
{ "type": "notification", "style": "success" | "warning" | "error" }
{ "type": "prepare" }
```

These messages are posted to `window.webkit.messageHandlers.haptics`.
