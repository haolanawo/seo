// ---- 常量 ----
const CONFIG_KEYS = ["diversity", "zhihu", "xiaohongshu", "x", "bilibili"];
const CATEGORY_LABELS = {
  persona: "人物定位",
  scene: "场景",
  angle: "论点切入角度",
  main_keywords: "主关键词",
  auxiliary_keywords: "辅助关键词",
};
let currentTab = "diversity";
let configCache = {};
let diversityOptions = {}; // { persona: [...], scene: [...], ... }

// ---- 初始化 ----
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  loadConfig();
  loadLogs();
  loadTemplates();
  loadKeywordOptions();
});

// ==================== Tab 切换 ====================

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

// ==================== 配置加载 / 保存 ====================

async function loadConfig() {
  for (const key of CONFIG_KEYS) {
    try {
      configCache[key] = await fetchConfig(key);
    } catch (e) {
      console.error(`加载配置失败: ${key}`, e);
    }
  }
  if (configCache[currentTab] !== undefined) {
    document.getElementById("config-textarea").value = configCache[currentTab];
  }
}

function loadConfigTab(key) {
  if (configCache[key] !== undefined) {
    document.getElementById("config-textarea").value = configCache[key];
  }
}

async function fetchConfig(key) {
  const url = key === "diversity"
    ? "/api/config/diversity"
    : `/api/config/platforms/${key}`;
  const resp = await fetch(url);
  const data = await resp.json();
  return data.yaml_text;
}

async function saveConfig() {
  const yamlText = document.getElementById("config-textarea").value;
  configCache[currentTab] = yamlText;

  const url = currentTab === "diversity"
    ? "/api/config/diversity"
    : `/api/config/platforms/${currentTab}`;

  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text: yamlText }),
  });

  const el = document.getElementById("config-status");
  el.textContent = resp.ok ? "保存成功" : "保存失败";
  el.className = `mini-status ${resp.ok ? "ok" : "err"}`;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2000);

  if (resp.ok) loadKeywordOptions();
}

// ==================== 关键词选择 ====================

async function loadKeywordOptions() {
  try {
    const resp = await fetch("/api/diversity/options");
    diversityOptions = await resp.json();
    renderKeywordGroups();
  } catch (e) {
    console.error("加载关键词选项失败", e);
  }
}

function renderKeywordGroups() {
  const container = document.getElementById("keyword-groups");
  container.innerHTML = "";

  for (const [key, label] of Object.entries(CATEGORY_LABELS)) {
    const items = diversityOptions[key];
    if (!items || items.length === 0) continue;

    const group = document.createElement("div");
    group.className = "kw-group";

    const title = document.createElement("div");
    title.className = "kw-group-title";
    title.textContent = label;

    const chips = document.createElement("div");
    chips.className = "kw-chips";

    for (const item of items) {
      const chip = document.createElement("label");
      chip.className = "kw-chip selected";
      chip.innerHTML = `<input type="checkbox" value="${escapeHtml(item)}" checked data-category="${key}"> <span>${escapeHtml(item)}</span>`;
      chips.appendChild(chip);
    }

    group.appendChild(title);
    group.appendChild(chips);
    container.appendChild(group);
  }
}

function getSelection() {
  const sel = {};
  const checkboxes = document.querySelectorAll("#keyword-groups input[type=checkbox]");
  for (const cb of checkboxes) {
    const cat = cb.dataset.category;
    if (!sel[cat]) sel[cat] = [];
    if (cb.checked) sel[cat].push(cb.value);
  }
  return sel;
}

function selectAll() {
  document.querySelectorAll("#keyword-groups input[type=checkbox]").forEach(cb => {
    cb.checked = true;
    cb.parentElement.classList.add("selected");
    cb.parentElement.classList.remove("deselected");
  });
}

function deselectAll() {
  document.querySelectorAll("#keyword-groups input[type=checkbox]").forEach(cb => {
    cb.checked = false;
    cb.parentElement.classList.add("deselected");
    cb.parentElement.classList.remove("selected");
  });
}

// checkbox 点击时更新 chip 样式
document.addEventListener("change", (e) => {
  if (e.target.matches("#keyword-groups input[type=checkbox]")) {
    const chip = e.target.parentElement;
    if (e.target.checked) {
      chip.classList.add("selected");
      chip.classList.remove("deselected");
    } else {
      chip.classList.add("deselected");
      chip.classList.remove("selected");
    }
  }
});

// ==================== 生成文章 ====================

async function startGenerate() {
  const platform = document.getElementById("platform").value;
  const count = parseInt(document.getElementById("count").value) || 1;
  const template = document.getElementById("template-select").value;
  const selection = getSelection();

  const btn = document.getElementById("btn-generate");
  const statusBar = document.getElementById("gen-status");

  btn.disabled = true;
  btn.textContent = "生成中...";
  statusBar.classList.remove("hidden", "error");
  statusBar.textContent = "正在生成...";
  document.getElementById("log-list").innerHTML = "";

  try {
    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, count, template, selection }),
    });

    if (!resp.ok) {
      statusBar.textContent = `请求失败 (${resp.status})`;
      statusBar.classList.add("error");
      btn.disabled = false;
      btn.textContent = "一键生成";
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let doneCount = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "progress") {
              if (data.status === "generating") {
                addLogItem(data.index, "generating", "生成中...");
              } else if (data.status === "ok") {
                doneCount++;
                const okFname = data.file.split("/").pop() || data.file.split("\\").pop();
addLogItem(data.index, "ok", `完成 (${data.elapsed}s) → ${okFname}`);
              } else if (data.status === "error") {
                doneCount++;
                addLogItem(data.index, "error", `失败: ${data.error}`);
              }
              statusBar.textContent = `进度: ${doneCount}/${count}`;
            } else if (data.type === "complete") {
              statusBar.textContent = `生成完成！共 ${data.count} 篇，文件夹: ${data.folder}`;
            }
          } catch {}
        }
      }
    }
  } catch (e) {
    statusBar.textContent = `连接中断: ${e.message}`;
    statusBar.classList.add("error");
  }

  btn.disabled = false;
  btn.textContent = "一键生成";
}

function addLogItem(index, status, msg) {
  const list = document.getElementById("log-list");
  if (list.textContent === "暂无日志") list.innerHTML = "";
  const div = document.createElement("div");
  div.className = `log-item ${status}`;
  div.textContent = `[${new Date().toLocaleTimeString()}] #${index} ${msg}`;
  list.prepend(div);
}

// ==================== 日志加载 ====================

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
    const fname = entry.file ? (entry.file.split("/").pop() || entry.file.split("\\").pop()) : "";
    div.textContent = `[${time}] #${entry.index} ${entry.status === "ok" ? "完成" : "失败"} (${entry.elapsed_s}s) ${fname} | ${entry.main_keyword}`;
    list.appendChild(div);
  }
}

// ==================== 模板列表 ====================

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

// ==================== 工具函数 ====================

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}
