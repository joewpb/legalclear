// Shared SSE (Server-Sent Events) byte-stream reader.
//
// Parses the wire format per the SSE spec: an optional `event:` line sets the
// frame's type (default "message" when absent, matching every current
// LegalClear backend stream — none of them set `event:` today), one or more
// `data:` lines carry the payload, and a blank line terminates the frame.
// Unrecognized SSE fields (`id:`, `retry:`, `:comment`) are skipped, never
// thrown on — a backend adding a new field or a new `event:` type must never
// crash the stream or drop the rest of the payload.
export interface SSEFrame {
  event: string;
  data: string;
}

// Best-effort extraction of disclaimer text from an SSE "disclaimer" frame.
// The backend sends either structured JSON ({"disclaimer": "..."}) or plain
// text; on JSON parse failure or a missing key, the raw frame text is used
// verbatim. Never throws — a malformed frame must not crash the stream.
export function parseDisclaimerPayload(raw: string): string {
  try {
    const parsed = JSON.parse(raw);
    return parsed.disclaimer ?? raw;
  } catch {
    return raw;
  }
}

export async function* readSSE(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): AsyncGenerator<SSEFrame, void, unknown> {
  const decoder = new TextDecoder();
  let buffer = "";
  let eventType = "message";
  let dataLines: string[] = [];

  const reset = () => {
    eventType = "message";
    dataLines = [];
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line === "" || line === "\r") {
        if (dataLines.length) {
          yield { event: eventType, data: dataLines.join("\n") };
        }
        reset();
      } else if (line.startsWith("event:")) {
        eventType = line.slice(6).replace(/^ /, "");
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).replace(/^ /, ""));
      }
      // id:, retry:, comment lines (leading ':') are valid SSE fields we
      // don't act on yet — ignored, not an error.
    }
  }

  if (dataLines.length) {
    yield { event: eventType, data: dataLines.join("\n") };
  }
}
