var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
var $$ = function (sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); };

// ─── Session ID (header-based, avoids cookie/proxy issues) ─────
var SESSION_HEADER = "X-Session-ID";
var SESSION_KEY = "rag_session_id";

function getSessionId() {
  var id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : _fallbackUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

function _fallbackUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    var r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function sessionHeaders(extra) {
  var h = {};
  h[SESSION_HEADER] = getSessionId();
  if (extra) { for (var k in extra) { h[k] = extra[k]; } }
  return h;
}

var Toast = {
  container: null,
  init: function () {
    if (!this.container) {
      this.container = document.createElement("div");
      this.container.className = "toast-container";
      document.body.appendChild(this.container);
    }
  },
  show: function (msg, type, duration) {
    this.init();
    duration = duration || 3500;
    var el = document.createElement("div");
    el.className = "toast " + (type || "info");
    el.textContent = msg;
    this.container.appendChild(el);
    setTimeout(function () { if (el.parentNode) { el.remove(); } }, duration);
  },
};

function setLoading(btn, loading) {
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn.dataset.text = btn.textContent.trim();
    btn.innerHTML = '<span class="spinner-sm inline-block"></span>';
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.text || "Send";
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function formatTimestamp(iso) {
  if (!iso) return "\u2014";
  var d = new Date(iso);
  var now = new Date();
  var diff = (now - d) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return Math.floor(diff / 60) + "m ago";
  if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
  return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ─── Upload Page ───────────────────────────────────────────

function initUploadPage() {
  var zone = $(".drop-zone");
  var input = $("#file-input");
  var status = $(".upload-status");
  var listBody = $(".doc-list-body");
  var docCount = $(".doc-count");
  if (!zone) return;

  zone.addEventListener("click", function () { if (!zone.classList.contains("disabled")) input.click(); });

  zone.addEventListener("dragover", function (e) {
    e.preventDefault();
    if (!zone.classList.contains("disabled")) zone.classList.add("drag-over");
  });

  zone.addEventListener("dragleave", function () {
    zone.classList.remove("drag-over");
  });

  zone.addEventListener("drop", function (e) {
    e.preventDefault();
    zone.classList.remove("drag-over");
    if (zone.classList.contains("disabled")) return;
    var files = e.dataTransfer.files;
    if (files.length) handleFile(files[0]);
  });

  input.addEventListener("change", function () {
    if (input.files.length) handleFile(input.files[0]);
    input.value = "";
  });

  function handleFile(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      Toast.show("Only PDF files are allowed", "error");
      return;
    }
    zone.classList.add("has-file", "disabled");
    var html = '<div class="text-left">';
    html += '<div class="flex items-center gap-2 text-green-600 mb-1">';
    html += '<svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>';
    html += '<span class="font-medium text-gray-800 truncate">' + file.name + '</span>';
    html += '</div>';
    html += '<div class="flex items-center gap-3 text-sm text-gray-500">';
    html += '<span>' + formatFileSize(file.size) + '</span>';
    html += '<span class="spinner inline-block"></span>';
    html += '<span class="upload-status-text">Uploading...</span>';
    html += '</div>';
    html += '<div class="upload-progress-bar"><div class="progress-fill" id="progressFill"></div></div>';
    html += '</div>';
    status.innerHTML = html;

    uploadFile(file);
  }

  function updateProgress(pct) {
    var fill = $("#progressFill");
    if (fill) fill.style.width = Math.min(pct, 100) + "%";
  }

  function uploadFile(file) {
    updateProgress(10);
    var fd = new FormData();
    fd.append("file", file);
    var xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", function (e) {
      if (e.lengthComputable) {
        var pct = Math.round((e.loaded / e.total) * 80) + 10;
        updateProgress(pct);
      }
    });

    xhr.addEventListener("load", function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        updateProgress(100);
        var data = JSON.parse(xhr.responseText);
        var html = '<div class="bg-green-50 border border-green-200 rounded-lg p-3 text-sm">';
        html += '<div class="flex items-center gap-2 text-green-700 font-medium">';
        html += '<svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';
        html += data.chunks_created + " chunks created";
        html += "</div>";
        html += '<div class="mt-1 text-gray-600">' + data.filename + ' &middot; uploaded ' + formatTimestamp(new Date().toISOString()) + '</div>';
        html += "</div>";
        status.innerHTML = html;
        Toast.show(data.filename + " uploaded successfully", "success");
        resetZone();
        loadDocuments();
      } else {
        handleUploadError(xhr);
      }
    });

    xhr.addEventListener("error", function () {
      handleUploadError(null);
    });

    xhr.open("POST", "/upload");
    xhr.setRequestHeader(SESSION_HEADER, getSessionId());
    xhr.send(fd);
  }

  function handleUploadError(xhr) {
    var msg = "Upload failed. Please try again.";
    if (xhr) {
      try {
        var err = JSON.parse(xhr.responseText);
        if (err.detail) msg = err.detail;
      } catch (e) {}
    }
    status.innerHTML =
      '<div class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm">' +
      '<div class="flex items-center gap-2 text-red-600 font-medium">' +
      '<svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>' +
      "Upload failed" +
      "</div>" +
      '<div class="mt-1 text-gray-600">' + msg + '</div>' +
      '<div class="mt-2 text-gray-500 text-xs">Make sure the file is a valid PDF under 20MB.</div>' +
      "</div>";
    Toast.show(msg, "error");
    resetZone();
  }

  function resetZone() {
    zone.classList.remove("has-file", "disabled");
    zone.querySelector("p").textContent = "Drop PDF here or click to browse";
  }

  function deleteDoc(filename) {
    if (!confirm('Delete "' + filename + '" and all its chunks?')) return;
    fetch("/documents/" + encodeURIComponent(filename), { method: "DELETE", headers: sessionHeaders() })
      .then(function (r) {
        if (!r.ok) { return r.json().then(function (j) { throw new Error(j.detail || "Delete failed"); }); }
        return r.json();
      })
      .then(function () {
        Toast.show("Deleted " + filename, "success");
        loadDocuments();
      })
      .catch(function (err) { Toast.show(err.message, "error"); });
  }

  function loadDocuments() {
    fetch("/documents", { headers: sessionHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.documents || !data.documents.length) {
          listBody.innerHTML =
            '<tr><td colspan="4" class="text-center py-12"><div class="text-gray-400"><svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg><p class="font-medium">No documents uploaded yet</p><p class="text-sm mt-1">Drag and drop a PDF above to get started</p></div></td></tr>';
          if (docCount) docCount.textContent = "0 documents";
          return;
        }
        listBody.innerHTML = data.documents.map(function (d) {
          var ts = formatTimestamp(d.uploaded_at);
          return '<tr class="border-b hover:bg-gray-50 transition" data-filename="' +
            (d.filename || "").replace(/"/g, "&quot;") +
            '"><td class="py-3 px-4"><div class="flex items-center gap-2 min-w-0"><svg class="w-4 h-4 text-red-500 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"/></svg><span class="font-medium truncate" title="' +
            (d.filename || "").replace(/"/g, "&quot;") + '">' + (d.filename || "unknown") + '</span></div></td>' +
            '<td class="py-3 px-4 text-gray-600 whitespace-nowrap">' + (d.chunks || 0) + ' chunks</td>' +
            '<td class="py-3 px-4 text-gray-500 text-sm whitespace-nowrap">' + ts + '</td>' +
            '<td class="py-3 px-4"><button class="delete-doc-btn text-red-500 hover:text-red-700 text-sm font-medium transition">Delete</button></td></tr>';
        }).join("");
        if (docCount) docCount.textContent = data.total + " document" + (data.total !== 1 ? "s" : "");
      })
      .catch(function () {
        listBody.innerHTML =
          '<tr><td colspan="4" class="text-center py-8 text-red-500">Failed to load documents. <button class="underline font-medium refresh-docs-btn">Retry</button></td></tr>';
      });
  }

  listBody.addEventListener("click", function (e) {
    var btn = e.target.closest(".delete-doc-btn");
    if (btn) {
      var row = btn.closest("tr");
      if (row && row.dataset.filename) deleteDoc(row.dataset.filename);
      return;
    }
    var retry = e.target.closest(".refresh-docs-btn");
    if (retry) loadDocuments();
  });

  var refreshBtn = $(".refresh-docs-btn-header");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "Refreshing...";
      loadDocuments();
      setTimeout(function () { refreshBtn.disabled = false; refreshBtn.textContent = "Refresh"; }, 1000);
    });
  }

  loadDocuments();
}

// ─── Chat Page ─────────────────────────────────────────────

function initChatPage() {
  var form = $(".chat-form");
  var input = $(".chat-input");
  var messages = $(".chat-messages");
  var sendBtn = $(".send-btn");
  var cancelBtn = $(".cancel-btn");
  var fileInput = $(".chat-file-input");
  var emptyState = $(".chat-empty-state");
  if (!form) return;

  if (fileInput) {
    fileInput.addEventListener("change", function () {
      if (fileInput.files.length) uploadAndRedirect(fileInput.files[0]);
    });
  }

  var _asking = false;
  var _abortController = null;
  var _timeoutId = null;
  var pendingAnswer = null;
  var _streamStartTime = 0;
  var _firstTokenTime = 0;
  var _llmStats = null;

  function scrollToBottom() {
    requestAnimationFrame(function () {
      messages.scrollTop = messages.scrollHeight;
    });
  }

  function addMessage(content, role, sources, stats) {
    if (emptyState) emptyState.style.display = "none";
    var row = document.createElement("div");
    row.className = "message-row " + role + " mb-4";

    var avatar = document.createElement("div");
    avatar.className = "avatar " + role;
    avatar.textContent = role === "assistant" ? "AI" : "U";
    row.appendChild(avatar);

    var bubble = document.createElement("div");
    bubble.className = "message-bubble " + role;

    if (role === "assistant") {
      var inner = '<div class="answer-text">';
      if (content) {
        inner += marked.parse(content);
      } else {
        inner += '<div class="typing-dots"><span></span><span></span><span></span></div>';
      }
      inner += "</div>";

      if (sources && sources.length) {
        inner += '<div class="mt-3 pt-3 border-t border-gray-200">';
        inner += '<div class="text-xs text-gray-500 font-medium mb-2 flex items-center gap-1.5">';
        inner += '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>';
        inner += sources.length + " source" + (sources.length !== 1 ? "s" : "");
        inner += "</div>";
        sources.forEach(function (s) {
          inner += '<div class="source-card mb-1.5">';
          inner += '<div class="source-card-header" data-chunk-id="' + (s.chunk_id || "").replace(/"/g, "&quot;") + '">';
          inner += '<svg class="w-3.5 h-3.5 text-blue-500 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"/></svg>';
          inner += '<span class="text-gray-700 truncate flex-1">' + (s.filename || "unknown") + '</span>';
          inner += '<span class="text-gray-400 text-xs shrink-0">chunk ' + (s.chunk_id ? s.chunk_id.slice(0, 8) : "?") + '</span>';
          inner += '<svg class="w-3.5 h-3.5 text-gray-400 expand-icon transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>';
          inner += "</div>";
          inner += '<div class="source-card-body">Loading preview...</div>';
          inner += "</div>";
        });
        inner += "</div>";
      }

      if (stats) {
        inner += '<div class="mt-3 flex flex-wrap gap-1.5">';
        inner += '<span class="stat-badge"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Vec: ' + stats.vector_candidates + '</span>';
        inner += '<span class="stat-badge"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg> BM25: ' + stats.bm25_candidates + '</span>';
        inner += '<span class="stat-badge"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg> Rerank: ' + stats.reranked_chunks + '</span>';
        if (stats.retrieval_latency_ms) {
          inner += '<span class="stat-badge"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Retrieval: ' + stats.retrieval_latency_ms + 'ms</span>';
        }
        if (stats.rerank_latency_ms) {
          inner += '<span class="stat-badge"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg> Rerank: ' + stats.rerank_latency_ms + 'ms</span>';
        }
        if (_llmStats && _llmStats.latency) {
          inner += '<span class="stat-badge text-blue-700 bg-blue-50 border-blue-200"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> LLM: ' + _llmStats.latency + 'ms</span>';
        }
        inner += "</div>";
      }

      bubble.innerHTML = inner;
    } else {
      bubble.textContent = content;
    }

    row.appendChild(bubble);
    messages.appendChild(row);
    scrollToBottom();
    return row;
  }

  function appendToken(text) {
    var el = pendingAnswer ? $(".answer-text", pendingAnswer) : null;
    if (!el) return;
    var dots = el.querySelector(".typing-dots");
    if (dots) {
      dots.insertAdjacentText("beforebegin", text);
      dots.remove();
    } else {
      el.appendChild(document.createTextNode(text));
    }
    if (!el.querySelector(".cursor-blink")) {
      var s = document.createElement("span");
      s.className = "cursor-blink";
      el.appendChild(s);
    }
    scrollToBottom();
  }

  function removeCursor() {
    var el = pendingAnswer ? $(".answer-text", pendingAnswer) : null;
    if (!el) return;
    var cursor = el.querySelector(".cursor-blink");
    if (cursor) cursor.remove();
  }

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event("submit"));
    }
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q) return;
    if (q.length <= 3) { Toast.show("Question must be longer than 3 characters", "error"); return; }
    ask(q);
    input.value = "";
    input.style.height = "auto";
  });

  input.addEventListener("input", function () {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 200) + "px";
  });

  if (cancelBtn) {
    cancelBtn.addEventListener("click", function () {
      if (_timeoutId) clearTimeout(_timeoutId);
      if (_abortController) {
        _abortController.abort();
        _abortController = null;
      }
      if (_asking) {
        _asking = false;
        setLoading(sendBtn, false);
        if (sendBtn) sendBtn.disabled = false;
        if (cancelBtn) cancelBtn.classList.add("hidden");
        removeCursor();
        var el = pendingAnswer ? $(".answer-text", pendingAnswer) : null;
        if (el) {
          var dots = el.querySelector(".typing-dots");
          if (dots) dots.remove();
          if (!el.textContent.trim()) {
            el.textContent = "Generation cancelled.";
          }
        }
        scrollToBottom();
      }
    });
  }

  function uploadAndRedirect(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) { Toast.show("Only PDF files allowed", "error"); return; }
    var fd = new FormData();
    fd.append("file", file);
    var btn = $(".upload-quick-btn");
    if (btn) { btn.disabled = true; btn.textContent = "Uploading..."; }
    fetch("/upload", { method: "POST", body: fd, headers: sessionHeaders() })
      .then(function (r) {
        if (!r.ok) { return r.json().then(function (j) { throw new Error(j.detail || "Upload failed"); }); }
        return r.json();
      })
      .then(function () {
        Toast.show(file.name + " uploaded \u2014 ask a question!", "success");
        if (btn) { btn.disabled = false; btn.textContent = "Upload PDF"; }
      })
      .catch(function (err) { Toast.show(err.message, "error"); if (btn) { btn.disabled = false; btn.textContent = "Upload PDF"; } });
  }

  var ask = function (question) {
    if (_asking) return;
    _asking = true;
    _streamStartTime = performance.now();
    _firstTokenTime = 0;
    _llmStats = null;

    setLoading(sendBtn, true);
    if (sendBtn) sendBtn.disabled = true;
    if (cancelBtn) cancelBtn.classList.remove("hidden");

    addMessage(question, "user");
    var assistantEl = addMessage("", "assistant", [], null);
    pendingAnswer = assistantEl;

    _abortController = new AbortController();
    _timeoutId = setTimeout(function () {
      _abortController.abort();
      Toast.show("LLM did not respond within 30s. Check your HF API key or try again.", "error");
    }, 30000);

    fetch("/ask/stream", {
      method: "POST",
      headers: sessionHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ question: question }),
      signal: _abortController.signal,
    })
      .then(function (r) {
        if (!r.ok) { return r.json().then(function (j) { throw new Error(j.detail || "Request failed"); }); }
        return r.body.getReader();
      })
      .then(function (reader) {
        var decoder = new TextDecoder();
        var buffer = "";
        var headerParsed = false;
        var sources = [];
        var stats = null;

        function processBuffer() {
          if (!headerParsed) {
            var idx = buffer.indexOf('"tokens":[');
            if (idx !== -1) {
              var headerStr = buffer.slice(0, idx + 10);
              try {
                var parsed = JSON.parse(headerStr + "]}");
                sources = parsed.sources || [];
                stats = parsed.retrieval_stats || null;
                var newEl = addMessage("", "assistant", sources, stats);
                if (pendingAnswer) pendingAnswer.remove();
                pendingAnswer = newEl;
              } catch (e) {}
              buffer = buffer.slice(idx + 10);
              headerParsed = true;
            }
          }

          if (headerParsed) {
            var tokenRegex = /,"((?:[^"\\]|\\.)*)"/g;
            var m;
            while ((m = tokenRegex.exec(buffer)) !== null) {
              if (_firstTokenTime === 0) _firstTokenTime = performance.now();
              try {
                appendToken(JSON.parse('"' + m[1] + '"'));
              } catch (e) {
                appendToken(m[1]);
              }
            }
            var lastQuote = buffer.lastIndexOf('"');
            buffer = lastQuote !== -1 ? buffer.slice(lastQuote) : "";
          }
        }

        function pump() {
          return reader.read().then(function (result) {
            if (result.done) {
              clearTimeout(_timeoutId);
              removeCursor();
              var endTime = performance.now();
              if (_firstTokenTime > 0) {
                var llmLatency = Math.round(endTime - _streamStartTime);
                _llmStats = { latency: llmLatency };
                var statsContainer = pendingAnswer ? $(".stat-badge:last-child", pendingAnswer) : null;
                if (stats && statsContainer) {
                  var existingStats = pendingAnswer ? $(".mt-3.flex-wrap", pendingAnswer) : null;
                  if (existingStats && !pendingAnswer.querySelector(".stat-badge.text-blue-700")) {
                    var badge = document.createElement("span");
                    badge.className = "stat-badge text-blue-700 bg-blue-50 border-blue-200";
                    badge.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> LLM: ' + llmLatency + 'ms';
                    existingStats.appendChild(badge);
                  }
                }
              }
              return;
            }
            buffer += decoder.decode(result.value, { stream: true });
            processBuffer();
            return pump();
          });
        }

        return pump();
      })
      .catch(function (err) {
        if (_timeoutId) clearTimeout(_timeoutId);
        if (err.name === "AbortError") return;
        removeCursor();
        if (pendingAnswer) {
          var textEl = $(".answer-text", pendingAnswer);
          if (textEl) {
            var dots = textEl.querySelector(".typing-dots");
            if (dots) dots.remove();
            if (!textEl.textContent.trim()) {
              textEl.textContent = "Error: " + err.message;
            }
          }
        } else {
          addMessage("Error: " + err.message, "assistant");
        }
        Toast.show(err.message, "error");
      })
      .finally(function () {
        if (_timeoutId) clearTimeout(_timeoutId);
        _asking = false;
        _abortController = null;
        setLoading(sendBtn, false);
        if (sendBtn) sendBtn.disabled = false;
        if (cancelBtn) cancelBtn.classList.add("hidden");
        scrollToBottom();
      });
  };

  // Source card expansion
  messages.addEventListener("click", function (e) {
    var header = e.target.closest(".source-card-header");
    if (!header) return;
    var card = header.closest(".source-card");
    if (!card) return;
    card.classList.toggle("expanded");
    var icon = header.querySelector(".expand-icon");
    if (icon) {
      icon.style.transform = card.classList.contains("expanded") ? "rotate(180deg)" : "rotate(0deg)";
    }
    var body = card.querySelector(".source-card-body");
    if (body && body.textContent === "Loading preview..." && card.classList.contains("expanded")) {
      var chunkId = header.dataset.chunkId;
      if (chunkId) {
        body.textContent = "Stored in vector database.\nChunk ID: " + chunkId;
      }
    }
  });

  // Auto-resize on paste
  document.addEventListener("paste", function () {
    if (input === document.activeElement) {
      setTimeout(function () {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 200) + "px";
      }, 0);
    }
  });
}
