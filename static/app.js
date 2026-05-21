// ---- 常量 ----
const PLATFORMS = ["diversity", "zhihu", "xiaohongshu", "x", "bilibili"];
let currentTab = "diversity";
let configCache = {}; // { key: yamlText }

// ---- 初始化 ----
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  loadConfig();
  loadLogs();
  loadTemplates();
});

// ---- Tab 切换 ----
function setupTabs() {
  document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentTab = tab.dataset.tab;
      loadConfigTab(currentTab);
    });
  });
}

// ---- 配置加载 ----
async function loadConfig() {
  for (const key of PLATFORMS) {
    try {
      const data = await fetchConfig(key);
      configCache[key] = data;
      if (key === currentTab) {
        document.getElementById("config-textarea").value = data;
      }
    } catch (e) {
      console.error(`加载配置失败: ${key}`, e);
    }
  }
}

function loadConfigTab(key) {
  if (configCache[key] !== undefined) {
    document.getElementById("config-textarea").value = configCache[key];
  }
}

async function fetchConfig(key) {
  let url;
  if (key === "diversity") {
    url = "/api/config/diversity";
  } else {
    url = `/api/config/platforms/${key}`;
  }
  const resp = await fetch(url);
  const data = await resp.json();
  return data.yaml_text;
}

// ---- 配置保存 ----
async function saveConfig() {
  const yamlText = document.getElementById("config-textarea").value;
  configCache[currentTab] = yamlText;

  // 需要把 YAML 文本发送给后端。但后端接收的是 parsed dict
  // 这里简化：发送原始文本，让后端解析
  const key = currentTab;
  let url, body;

  if (key === "diversity") {
    url = "/api/config/diversity";
  } else {
    url = `/api/config/platforms/${key}`;
  }

  // 将 YAML 文本作为 raw text 发送
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text: yamlText }),
  });

  const statusEl = document.getElementById("config-status");
  if (resp.ok) {
    statusEl.textContent = "保存成功";
    statusEl.className = "mini-status ok";
  } else {
    statusEl.textContent = "保存失败";
    statusEl.className = "mini-status err";
  }
  statusEl.classList.remove("hidden");
  setTimeout(() => statusEl.classList.add("hidden"), 2000);
}

// ---- 生成文章 ----
function startGenerate() {
  const platform = document.getElementById("platform").value;
  const count = parseInt(document.getElementById("count").value) || 1;
  const template = document.getElementById("template-select").value;

  const btn = document.getElementById("btn-generate");
  const statusBar = document.getElementById("gen-status");

  btn.disabled = true;
  btn.textContent = "生成中...";
  statusBar.classList.remove("hidden", "error");
  statusBar.textContent = "正在生成...";
  document.getElementById("log-list").innerHTML = "";

  const params = new URLSearchParams({ platform, count, template });
  const evtSource = new EventSource(`/api/generate?${params}`);

  evtSource.addEventListener("message", (e) => {
    try {
      const data = JSON.parse(e.data);
      handleSSE(data);
    } catch {}
  });

  let doneCount = 0;
  const totalCount = count;

  function handleSSE(data) {
    if (data.type === "progress") {
      if (data.status === "generating") {
        addLogItem(data.index, "generating", "生成中...");
      } else if (data.status === "ok") {
        doneCount++;
        addLogItem(data.index, "ok", `完成 (${data.elapsed}s) → ${data.file.split("/").pop()}`);
      } else if (data.status === "error") {
        doneCount++;
        addLogItem(data.index, "error", `失败: ${data.error}`);
      }
      statusBar.textContent = `进度: ${doneCount}/${totalCount}`;
    } else if (data.type === "complete") {
      statusBar.textContent = `生成完成！共 ${totalCount} 篇，文件夹: ${data.folder}`;
      btn.disabled = false;
      btn.textContent = "一键生成";
      evtSource.close();
    }
  }

  evtSource.addEventListener("error", () => {
    statusBar.textContent = "连接中断";
    statusBar.classList.add("error");
    btn.disabled = false;
    btn.textContent = "一键生成";
    evtSource.close();
  });
}

function addLogItem(index, status, msg) {
  const list = document.getElementById("log-list");
  if (list.textContent === "暂无日志") list.innerHTML = "";
  const div = document.createElement("div");
  div.className = `log-item ${status}`;
  div.textContent = `[${new Date().toLocaleTimeString()}] #${index} ${msg}`;
  list.prepend(div);
}

// ---- 日志加载 ----
async function loadLogs() {
  const resp = await fetch("/api/logs");
  const data = await resp.json();
  const list = document.getElementById("log-list");

  if (data.logs.length === 0) {
    list.innerHTML = "暂无日志";
    return;
  }

  list.innerHTML = "";
  for (const entry of data.logs.reverse()) {
    const div = document.createElement("div");
    div.className = `log-item ${entry.status}`;
    const time = entry.timestamp ? entry.timestamp.slice(11, 19) : "";
    const fname = entry.file ? entry.file.split("/").pop() || entry.file.split("\\").pop() : "";
    div.textContent = `[${time}] #${entry.index} ${entry.status === "ok" ? "完成" : "失败"} (${entry.elapsed_s}s) ${fname} | ${entry.main_keyword}`;
    list.appendChild(div);
  }
}

// ---- 模板列表 ----
async function loadTemplates() {
  const resp = await fetch("/api/templates");
  const data = await resp.json();
  const sel = document.getElementById("template-select");
  for (const t of data.templates) {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    sel.appendChild(opt);
  }
}
