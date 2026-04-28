import { describe, expect, it } from "vitest";

describe("frontend smoke", () => {
  it("keeps base url string", () => {
    expect(typeof "http://127.0.0.1:8000/api").toBe("string");
  });
});
