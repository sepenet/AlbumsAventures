import { describe, expect, it } from "vitest";

import {
  CHUNK_SIZE_CEILING,
  CHUNK_SIZE_FLOOR,
  buildUploadConfigQuery,
  clampChunkSize,
  computeCompressionMetric,
  formatBytes,
  selectChunkSize,
} from "./upload";

describe("clampChunkSize", () => {
  it("never returns below the 256 KB floor", () => {
    expect(clampChunkSize(1024)).toBe(CHUNK_SIZE_FLOOR);
    expect(clampChunkSize(0)).toBe(CHUNK_SIZE_FLOOR);
    expect(clampChunkSize(-5)).toBe(CHUNK_SIZE_FLOOR);
    expect(clampChunkSize(Number.NaN)).toBe(CHUNK_SIZE_FLOOR);
  });

  it("caps at the 8 MB ceiling", () => {
    expect(clampChunkSize(64 * 1024 * 1024)).toBe(CHUNK_SIZE_CEILING);
  });

  it("passes through an in-range value", () => {
    expect(clampChunkSize(1024 * 1024)).toBe(1024 * 1024);
  });
});

describe("selectChunkSize", () => {
  it("floors when there is no connection info", () => {
    expect(selectChunkSize(null)).toBe(CHUNK_SIZE_FLOOR);
    expect(selectChunkSize(undefined)).toBe(CHUNK_SIZE_FLOOR);
  });

  it("floors when the user requested data saver, regardless of link", () => {
    expect(selectChunkSize({ effectiveType: "4g", downlink: 50, saveData: true })).toBe(
      CHUNK_SIZE_FLOOR,
    );
  });

  it("floors on 2g / slow-2g", () => {
    expect(selectChunkSize({ effectiveType: "slow-2g" })).toBe(CHUNK_SIZE_FLOOR);
    expect(selectChunkSize({ effectiveType: "2g" })).toBe(CHUNK_SIZE_FLOOR);
  });

  it("scales up on faster effective types but stays within bounds", () => {
    expect(selectChunkSize({ effectiveType: "3g" })).toBe(512 * 1024);
    expect(selectChunkSize({ effectiveType: "4g" })).toBe(2 * 1024 * 1024);
    const fast = selectChunkSize({ effectiveType: "5g", downlink: 1000 });
    expect(fast).toBeLessThanOrEqual(CHUNK_SIZE_CEILING);
    expect(fast).toBeGreaterThanOrEqual(CHUNK_SIZE_FLOOR);
  });

  it("honors a high downlink but never exceeds the ceiling", () => {
    expect(selectChunkSize({ effectiveType: "4g", downlink: 1000 })).toBe(CHUNK_SIZE_CEILING);
  });
});

describe("computeCompressionMetric", () => {
  it("reports the bytes saved by client compression (#380)", () => {
    const metric = computeCompressionMetric([
      { originalBytes: 1000, sentBytes: 400 },
      { originalBytes: 2000, sentBytes: 1000 },
    ]);
    expect(metric.originalBytes).toBe(3000);
    expect(metric.sentBytes).toBe(1400);
    expect(metric.compressedSavedBytes).toBe(1600);
  });

  it("never reports negative savings", () => {
    const metric = computeCompressionMetric([{ originalBytes: 100, sentBytes: 250 }]);
    expect(metric.compressedSavedBytes).toBe(0);
  });

  it("returns zeros for an empty batch", () => {
    expect(computeCompressionMetric([])).toEqual({
      originalBytes: 0,
      sentBytes: 0,
      compressedSavedBytes: 0,
    });
  });
});

describe("formatBytes", () => {
  it("formats across unit boundaries in French", () => {
    expect(formatBytes(512)).toBe("512 o");
    expect(formatBytes(2048)).toBe("2.0 Ko");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 Mo");
    expect(formatBytes(3 * 1024 * 1024 * 1024)).toBe("3.00 Go");
  });
});

describe("buildUploadConfigQuery", () => {
  it("serializes present connection hints", () => {
    expect(buildUploadConfigQuery({ effectiveType: "4g", downlink: 12, saveData: true })).toBe(
      "effective_type=4g&downlink=12&save_data=true",
    );
  });

  it("omits absent hints and skips save_data when false", () => {
    expect(buildUploadConfigQuery({ effectiveType: "3g", saveData: false })).toBe(
      "effective_type=3g",
    );
    expect(buildUploadConfigQuery(null)).toBe("");
  });
});
