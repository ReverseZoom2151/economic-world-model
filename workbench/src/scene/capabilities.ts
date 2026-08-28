export function supportsWebGL(): boolean {
  try {
    if (
      typeof window.WebGLRenderingContext === "undefined" &&
      typeof window.WebGL2RenderingContext === "undefined"
    ) {
      return false;
    }
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}
