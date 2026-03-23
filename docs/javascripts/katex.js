function renderKatex() {
  if (typeof renderMathInElement !== "function") {
    console.warn("KaTeX auto-render not loaded");
    return;
  }

  renderMathInElement(document.body, {
    delimiters: [
      // Support both Markdown ($...$ / $$...$$) and arithmatex (\(...\) / \[...\])
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false },
      { left: "\\(", right: "\\)", display: false },
      { left: "\\[", right: "\\]", display: true },
    ],
    throwOnError: false,
    output: "htmlAndMathml",
  });
}

// MkDocs Material may use instant navigation: re-render math on each page swap.
if (typeof document$ !== "undefined" && document$.subscribe) {
  document$.subscribe(() => {
    renderKatex();
  });
} else {
  document.addEventListener("DOMContentLoaded", () => {
    renderKatex();
  });
}
