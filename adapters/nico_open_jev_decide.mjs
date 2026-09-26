#!/usr/bin/env node
/** Pinned nico-martin/open-jev CPU adapter for the weekly market JSONL protocol. */

import { createInterface } from "node:readline";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { performance } from "node:perf_hooks";

const SOURCE_REVISION = "52667199e8a55553e1865a41f43fcb7d4dd92779";
const MODEL = "onnx-community/open-jev-deberta-v3-large-ONNX";
const MODEL_REVISION = "7c79f25b5ac496089f448a969c801872ad59d31c";
const TASK = "next_7_day_price_direction";

// Some native runtimes log during load; stdout is reserved for decisions.
console.log = (...args) => console.error(...args);

async function main() {
  const sourceDir = process.env.NICO_OPEN_JEV_SOURCE_DIR;
  const modelPath = process.env.NICO_OPEN_JEV_MODEL_PATH;
  if (!sourceDir || !modelPath) {
    throw new Error("NICO_OPEN_JEV_SOURCE_DIR and NICO_OPEN_JEV_MODEL_PATH are required");
  }

  const { OpenJev, choice } = await import(
    pathToFileURL(resolve(sourceDir, "dist/index.js")).href
  );
  const jev = await OpenJev.load({
    model: resolve(modelPath),
    device: "cpu",
    dtype: "q4",
    maxLength: 512,
    maxStateTokens: 256,
    truncation: "error",
  });
  try {
    let lineNumber = 0;
    for await (const line of createInterface({ input: process.stdin })) {
      lineNumber += 1;
      if (!line.trim()) continue;
      const request = JSON.parse(line);
      if (typeof request?.id !== "string" || !request.id) {
        throw new Error(`line ${lineNumber}: id must be a nonempty string`);
      }
      if (typeof request.state !== "string" || !request.state.trim()) {
        throw new Error(`line ${lineNumber}: state must be a nonempty string`);
      }

      const started = performance.now();
      const [answer] = await jev.decide(request.state, [
        choice(TASK, ["up", "down"], {
          up: "The next seven-day return is strictly positive",
          down: "The next seven-day return is zero or negative",
        }),
      ]);
      const up = Number(answer.probabilities.up);
      const down = Number(answer.probabilities.down);
      if (!Number.isFinite(up) || !Number.isFinite(down) || up < 0 || down < 0) {
        throw new Error(`line ${lineNumber}: invalid model probabilities`);
      }
      const sum = up + down;
      if (!(sum > 0)) throw new Error(`line ${lineNumber}: zero probability mass`);
      const probabilities = { up: up / sum, down: down / sum };
      const prediction = probabilities.up > probabilities.down ? "up" : "down";
      process.stdout.write(JSON.stringify({
        id: request.id,
        prediction,
        probabilities,
        prob_up: probabilities.up,
        target_weight: prediction === "up" ? 1 : 0,
        latency_ms: Math.round((performance.now() - started) * 1000) / 1000,
        source: "nico-martin/open-jev",
        source_revision: SOURCE_REVISION,
        model: MODEL,
        model_revision: MODEL_REVISION,
        device: "cpu",
        dtype: "q4",
        temperature: 1.05,
        task: TASK,
      }) + "\n");
    }
  } finally {
    await jev.dispose();
  }
}

main().catch((error) => {
  console.error(`nico_open_jev_decide: ${error.stack ?? error}`);
  process.exitCode = 1;
});
