import { describe, expect, it } from "vitest";
import { safeExternalUrl } from "@/lib/utils";

describe("safeExternalUrl", () => {
  it("allows http and https links", () => {
    expect(safeExternalUrl("https://example.com/story")).toBe("https://example.com/story");
    expect(safeExternalUrl("http://example.com/story")).toBe("http://example.com/story");
  });

  it("rejects executable and non-web schemes", () => {
    expect(safeExternalUrl("javascript:alert(1)")).toBeNull();
    expect(safeExternalUrl("data:text/html,<script>alert(1)</script>")).toBeNull();
    expect(safeExternalUrl("file:///etc/passwd")).toBeNull();
    expect(safeExternalUrl("")).toBeNull();
    expect(safeExternalUrl(null)).toBeNull();
  });
});
