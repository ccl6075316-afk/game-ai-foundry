import assert from "node:assert/strict";
import test from "node:test";
import { isConfigNoiseReply, prepareAgentDisplay } from "./agentReply.ts";

test("isConfigNoiseReply detects long config dumps", () => {
  const noise =
    "review diff of config.json\n" +
    "x".repeat(700) +
    "\nreview diff again";
  assert.equal(isConfigNoiseReply(noise), true);
});

test("prepareAgentDisplay replaces config noise only for product_host", () => {
  const noise =
    "review diff of config.json\n" +
    "x".repeat(700) +
    "\nreview diff again";
  const host = prepareAgentDisplay(noise, { role: "product_host" });
  assert.equal(host.weak, true);
  assert.equal(host.reason, "config_noise");
  assert.match(host.display, /未按用户要求改配置/);

  const it = prepareAgentDisplay(noise, { role: "it" });
  assert.equal(it.weak, false);
  assert.equal(it.reason, null);
  assert.match(it.display, /review diff/);
});

test("prepareAgentDisplay without role keeps IT-safe passthrough", () => {
  const noise =
    "review diff of config.json\n" +
    "x".repeat(700) +
    "\nreview diff again";
  const plain = prepareAgentDisplay(noise);
  assert.equal(plain.weak, false);
  assert.match(plain.display, /review diff/);
});
