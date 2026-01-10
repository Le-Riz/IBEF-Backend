document.addEventListener("DOMContentLoaded", () => {
  if (typeof renderMathInElement !== "function") {
    return;
  }

  renderMathInElement(document.body, {
    delimiters: [
      { left: "$", right: "$", display: false },
      { left: "$$", right: "$$", display: true },
    ],
  });
});
