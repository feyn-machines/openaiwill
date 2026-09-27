(() => {
  const values = { conservative: 32, central: 46, optimistic: 62 };
  const names = { conservative: "保守", central: "中心", optimistic: "乐观" };
  document.querySelectorAll('input[name="scenario"]').forEach((input) => {
    input.addEventListener("change", () => {
      const value = values[input.value];
      document.querySelector("#estimate-value").textContent = value.toFixed(1);
      document.querySelector("#estimate-label").textContent = `${names[input.value]}情景 · 虚构样本`;
      document.querySelector("#range-cursor").setAttribute("x", String(40 + value * 6.4 - 5));
      document.querySelector("#range-current").textContent = `${names[input.value]} ${value}`;
      document.querySelector("#range-current").setAttribute("x", String(40 + value * 6.4));
      document.querySelector("#range-cursor-mobile").setAttribute("x", String(20 + value * 3.2 - 5));
      document.querySelector("#range-current-mobile").textContent = `${names[input.value]} ${value}`;
      document.querySelector("#range-current-mobile").setAttribute("x", String(20 + value * 3.2));
    });
  });
  let timer;
  document.querySelector("#play-flow").addEventListener("click", () => {
    const flow = document.querySelector("#demo-flow");
    const status = document.querySelector("#motion-status");
    const button = document.querySelector("#play-flow");
    clearTimeout(timer);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      status.textContent = "已显示完整流程（跟随系统：减弱动画）。";
      return;
    }
    flow.classList.add("is-playing");
    button.disabled = true;
    status.textContent = "演示中：来源记录 → 事件归并 → 状态评估";
    const duration = parseFloat(getComputedStyle(document.body).getPropertyValue("--ah-motion-sequence"));
    timer = window.setTimeout(() => {
      flow.classList.remove("is-playing");
      button.disabled = false;
      status.textContent = "演示完成。虚线表示关系仍需评审。";
    }, duration);
  });
  document.querySelector("#source-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.querySelector("#source-url");
    const error = document.querySelector("#source-error");
    const result = document.querySelector("#source-status");
    let valid = false;
    try {
      const url = new URL(input.value);
      valid = url.protocol === "https:" && Boolean(url.hostname);
    } catch { /* Invalid URLs receive the same actionable message below. */ }
    input.setAttribute("aria-invalid", String(!valid));
    error.hidden = valid;
    result.textContent = valid ? "格式检查通过。本样本未发送或保存链接。" : "";
    if (!valid) input.focus();
  });
})();
