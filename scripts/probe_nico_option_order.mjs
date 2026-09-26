#!/usr/bin/env node
/** One-event control for the pinned Nico Open-Jev option-order effect. */

import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const EVENT_SHA256 = "d17d4fb3bfcacd898e0a81a07ed704d598f931fc4db9ff683ba649646fdbbecc";
const TASK = "next_7_day_price_direction";
const descriptions = {
  up: "The next seven-day return is strictly positive",
  down: "The next seven-day return is zero or negative",
};

async function main() {
  const sourceDir = process.env.NICO_OPEN_JEV_SOURCE_DIR;
  const modelPath = process.env.NICO_OPEN_JEV_MODEL_PATH;
  if (!sourceDir || !modelPath) {
    throw new Error("NICO_OPEN_JEV_SOURCE_DIR and NICO_OPEN_JEV_MODEL_PATH are required");
  }
  const eventPath = resolve(process.env.NICO_OPEN_JEV_EVENTS_PATH ?? "data/weekly-v1/events.jsonl");
  const eventBytes = readFileSync(eventPath);
  const actualSha = createHash("sha256").update(eventBytes).digest("hex");
  if (actualSha !== EVENT_SHA256) {
    throw new Error(`event file SHA-256 mismatch: ${actualSha}`);
  }
  const event = JSON.parse(eventBytes.toString("utf8").split("\n", 1)[0]);
  if (event.id !== "e000001" || typeof event.state !== "string") {
    throw new Error("expected the first pinned event e000001 with text state");
  }

  const { OpenJev, choice } = await import(pathToFileURL(resolve(sourceDir, "dist/index.js")).href);
  const model = await OpenJev.load({
    model: resolve(modelPath),
    device: "cpu",
    dtype: "q4",
    maxLength: 512,
    maxStateTokens: 256,
    truncation: "error",
  });
  try {
    for (const order of [["up", "down"], ["down", "up"]]) {
      const [answer] = await model.decide(event.state, [choice(TASK, order, descriptions)]);
      process.stdout.write(JSON.stringify({ id: event.id, order, answer }) + "\n");
    }
  } finally {
    await model.dispose();
  }
}

main().catch((error) => {
  console.error(`probe_nico_option_order: ${error.stack ?? error}`);
  process.exitCode = 1;
});
