const state = {
  apiKey: localStorage.getItem("agentops.apiKey") || "",
  bearerToken: localStorage.getItem("agentops.bearerToken") || "",
  channelToken: localStorage.getItem("agentops.channelToken") || "",
};

const resultBox = document.querySelector("#resultBox");
const resultMeta = document.querySelector("#resultMeta");
const serviceStatus = document.querySelector("#serviceStatus");

function setResult(payload, meta = "请求完成") {
  resultMeta.textContent = meta;
  resultBox.textContent = JSON.stringify(payload, null, 2);
}

function parseContext(raw) {
  if (!raw.trim()) return {};
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error("上下文 JSON 格式不正确");
  }
}

function headersFor(kind) {
  const headers = {"Content-Type": "application/json"};
  if (kind === "internal") {
    if (state.apiKey) headers["X-API-Key"] = state.apiKey;
    if (state.bearerToken) headers.Authorization = `Bearer ${state.bearerToken}`;
  }
  if (kind === "customer" && state.channelToken) {
    headers["X-Channel-Token"] = state.channelToken;
  }
  return headers;
}

async function postJSON(path, payload, kind) {
  const started = performance.now();
  const response = await fetch(path, {
    method: "POST",
    headers: headersFor(kind),
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  const duration = Math.round(performance.now() - started);
  if (!response.ok) {
    const detail = data.detail || response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return {data, duration};
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("health failed");
    serviceStatus.textContent = "服务在线";
    serviceStatus.classList.add("ok");
    serviceStatus.classList.remove("fail");
  } catch (error) {
    serviceStatus.textContent = "服务离线";
    serviceStatus.classList.add("fail");
    serviceStatus.classList.remove("ok");
  }
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".module").forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`#${tab.dataset.tab}`).classList.add("active");
  });
});

document.querySelectorAll(".agent-form").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const kind = form.dataset.kind;
    const submitButton = form.querySelector("button[type='submit']");
    submitButton.disabled = true;
    submitButton.textContent = "运行中";
    resultMeta.textContent = "请求处理中";

    try {
      const context = parseContext(formData.get("context") || "{}");
      let payload;
      let endpoint;
      if (kind === "customer") {
        endpoint = "/api/customer/qa";
        payload = {
          customer_user_id: formData.get("customer_user_id"),
          contact: formData.get("contact"),
          channel: "web",
          message: formData.get("message"),
          context,
        };
      } else {
        endpoint = "/api/chat";
        payload = {
          employee_id: formData.get("employee_id"),
          role: formData.get("role"),
          message: formData.get("message"),
          context,
        };
      }
      const {data, duration} = await postJSON(endpoint, payload, kind);
      setResult(data, `${endpoint} · ${duration}ms`);
    } catch (error) {
      setResult({error: error.message}, "请求失败");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = submitButton.dataset.originalText || submitButton.textContent.replace("运行中", "提交");
    }
  });
  const button = form.querySelector("button[type='submit']");
  button.dataset.originalText = button.textContent;
});

document.querySelector("#saveSettings").addEventListener("click", () => {
  state.apiKey = document.querySelector("#apiKey").value.trim();
  state.bearerToken = document.querySelector("#bearerToken").value.trim();
  state.channelToken = document.querySelector("#channelToken").value.trim();
  localStorage.setItem("agentops.apiKey", state.apiKey);
  localStorage.setItem("agentops.bearerToken", state.bearerToken);
  localStorage.setItem("agentops.channelToken", state.channelToken);
  setResult({saved: true}, "设置已保存");
});

document.querySelector("#clearResult").addEventListener("click", () => {
  setResult({}, "等待请求");
});

document.querySelector("#apiKey").value = state.apiKey;
document.querySelector("#bearerToken").value = state.bearerToken;
document.querySelector("#channelToken").value = state.channelToken;
checkHealth();
