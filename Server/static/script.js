document.addEventListener('DOMContentLoaded', () => {
  const COLUMNS = window.CSV_COLUMNS || [];
  const ROWS = window.CSV_ROWS || [];
  const SELECTED_FILE = window.SELECTED_FILE;

  let sortedRows = [...ROWS];
  let sortCol = null;
  let sortDir = 1;

  function renderTable(rowsList) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    rowsList.forEach(row => {
      const tableRow = document.createElement('tr');
      COLUMNS.forEach(column => {
        const cell = document.createElement('td');
        cell.textContent = row[column] !== undefined ? row[column] : '';
        tableRow.appendChild(cell);
      });
      tbody.appendChild(tableRow);
    });

    document.getElementById('stats').textContent =
      `表示中: ${rowsList.length} / 全 ${ROWS.length} 件`;
  }

  function sortRowsData() {
    if (!sortCol) {
      return;
    }
    sortedRows.sort((firstRow, secondRow) => {
      const firstValue = firstRow[sortCol];
      const secondValue = secondRow[sortCol];
      const firstNumber = Number(String(firstValue).replace(/,/g, ''));
      const secondNumber = Number(String(secondValue).replace(/,/g, ''));

      if (
        Number.isFinite(firstNumber)
        && Number.isFinite(secondNumber)
      ) {
        return (firstNumber - secondNumber) * sortDir;
      }
      return String(firstValue).localeCompare(
        String(secondValue),
        undefined,
        { numeric: true },
      ) * sortDir;
    });
  }

  function updateSortIndicators() {
    document.querySelectorAll('#table-header th').forEach(header => {
      const column = header.getAttribute('data-col');
      const icon = header.querySelector('.sort-icon');
      if (column === sortCol) {
        icon.textContent = sortDir === 1 ? ' ▲' : ' ▼';
        icon.style.color = 'var(--accent)';
      } else {
        icon.textContent = ' ↕';
        icon.style.color = '#94a3b8';
      }
    });
  }

  function initHeader() {
    const headerRow = document.getElementById('table-header');
    headerRow.innerHTML = '';
    COLUMNS.forEach(column => {
      const header = document.createElement('th');
      header.setAttribute('data-col', column);
      header.innerHTML = `${column}<span class="sort-icon"> ↕</span>`;
      header.addEventListener('click', () => {
        if (sortCol === column) {
          sortDir = -sortDir;
        } else {
          sortCol = column;
          sortDir = 1;
        }
        sortRowsData();
        updateSortIndicators();
        renderTable(sortedRows);
      });
      headerRow.appendChild(header);
    });
  }

  function toCSV(rows) {
    const escapeValue = value =>
      `"${String(value || '').replace(/"/g, '""')}"`;
    const header = COLUMNS.map(escapeValue).join(',');
    const body = rows
      .map(row => COLUMNS.map(column => escapeValue(row[column])).join(','))
      .join('\n');
    return `${header}\n${body}`;
  }

  document.getElementById('download').addEventListener('click', () => {
    const blob = new Blob(
      [toCSV(sortedRows)],
      { type: 'text/csv;charset=utf-8;' },
    );
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = SELECTED_FILE || 'export.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
  });

  document.getElementById('export-json').addEventListener('click', () => {
    const blob = new Blob(
      [JSON.stringify(sortedRows, null, 2)],
      { type: 'application/json' },
    );
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const filename = SELECTED_FILE || 'export.json';
    link.download = filename.replace('.csv', '.json');
    document.body.appendChild(link);
    link.click();
    link.remove();
  });

  if (COLUMNS.length > 0) {
    initHeader();
    updateSortIndicators();
    renderTable(sortedRows);
  }

  initAddData();
  initChatbot();

  function initAddData() {
    const dialog = document.getElementById('add-data-dialog');
    const form = document.getElementById('add-data-form');
    const openButton = document.getElementById('open-add-dialog');
    const cancelButton = document.getElementById('cancel-add-data');
    const submitButton = document.getElementById('submit-add-data');
    const errorMessage = document.getElementById('add-data-error');
    const timestampInput = document.getElementById('timestamp');

    const currentLocalTimestamp = () => {
      const now = new Date();
      const pad = value => String(value).padStart(2, '0');
      return [
        now.getFullYear(),
        pad(now.getMonth() + 1),
        pad(now.getDate()),
      ].join('-') + 'T' + [
        pad(now.getHours()),
        pad(now.getMinutes()),
        pad(now.getSeconds()),
      ].join(':');
    };

    openButton.addEventListener('click', () => {
      form.reset();
      errorMessage.textContent = '';
      timestampInput.value = currentLocalTimestamp();
      dialog.showModal();
    });

    cancelButton.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target === dialog) {
        dialog.close();
      }
    });

    form.addEventListener('submit', async event => {
      event.preventDefault();
      errorMessage.textContent = '';
      const formValues = Object.fromEntries(new FormData(form).entries());
      submitButton.disabled = true;
      submitButton.textContent = '追加中…';

      try {
        const response = await fetch('/api/data', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file: SELECTED_FILE,
            ...formValues,
          }),
        });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(
            result.error || 'データを追加できませんでした',
          );
        }

        const nextUrl = new URL(window.location.href);
        nextUrl.searchParams.set('file', SELECTED_FILE);
        window.location.assign(nextUrl);
      } catch (error) {
        errorMessage.textContent =
          error.message || 'データを追加できませんでした';
        submitButton.disabled = false;
        submitButton.textContent = 'データを追加';
      }
    });
  }

  function initChatbot() {
    const panel = document.getElementById('chatbot-panel');
    const toggle = document.getElementById('chatbot-toggle');
    const close = document.getElementById('chatbot-close');
    const reset = document.getElementById('chatbot-reset');
    const form = document.getElementById('chatbot-form');
    const input = document.getElementById('chatbot-input');
    const messages = document.getElementById('chatbot-messages');
    const status = document.getElementById('chatbot-status');
    const send = document.getElementById('chatbot-send');
    const storageKey = `csv-ai-chat:${SELECTED_FILE || 'no-file'}`;
    let conversation = loadConversation(storageKey);

    conversation.forEach(item => {
      appendChatMessage(messages, item.role, item.content);
    });

    const setOpen = open => {
      panel.classList.toggle('open', open);
      panel.setAttribute('aria-hidden', String(!open));
      toggle.setAttribute('aria-expanded', String(open));
      if (open) {
        input.focus();
      }
    };

    toggle.addEventListener('click', () => {
      setOpen(!panel.classList.contains('open'));
    });
    close.addEventListener('click', () => setOpen(false));
    reset.addEventListener('click', () => {
      conversation = [];
      saveConversation(storageKey, conversation);
      messages.innerHTML = '';
      appendChatMessage(messages, 'assistant', '会話履歴を削除しました。');
      input.focus();
    });

    input.addEventListener('keydown', event => {
      if (
        event.key === 'Enter'
        && !event.shiftKey
        && !event.isComposing
      ) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const question = input.value.trim();
      if (!question) {
        return;
      }
      if (!SELECTED_FILE) {
        appendChatMessage(
          messages,
          'assistant',
          '分析するCSVが選択されていません。',
          true,
        );
        return;
      }

      const previousConversation = conversation.slice(-10);
      appendChatMessage(messages, 'user', question);
      conversation.push({ role: 'user', content: question });
      conversation = conversation.slice(-20);
      saveConversation(storageKey, conversation);
      input.value = '';
      input.disabled = true;
      send.disabled = true;
      status.textContent = '回答を生成しています…';

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: question,
            file: SELECTED_FILE,
            conversation: previousConversation,
          }),
        });
        const body = await response.json();
        if (!response.ok) {
          throw new Error(body.error || `HTTP ${response.status}`);
        }

        appendChatMessage(messages, 'assistant', body.response);
        conversation.push({
          role: 'assistant',
          content: body.response,
        });
        conversation = conversation.slice(-20);
        saveConversation(storageKey, conversation);
      } catch (error) {
        appendChatMessage(
          messages,
          'assistant',
          `通信エラー: ${error.message}`,
          true,
        );
      } finally {
        input.disabled = false;
        send.disabled = false;
        status.textContent = '';
        input.focus();
      }
    });
  }
});

function appendChatMessage(container, role, text, error = false) {
  const wrapper = document.createElement('div');
  const label = document.createElement('div');
  const bubble = document.createElement('div');
  wrapper.className = `chat-message ${role}${error ? ' error' : ''}`;
  label.className = 'chat-message-label';
  label.textContent = role === 'user' ? 'あなた' : 'AI';
  bubble.className = 'chat-message-bubble';
  bubble.textContent = text;
  wrapper.append(label, bubble);
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
}

function loadConversation(storageKey) {
  try {
    const value = JSON.parse(localStorage.getItem(storageKey) || '[]');
    if (!Array.isArray(value)) {
      return [];
    }
    return value.filter(item => (
      item
      && ['user', 'assistant'].includes(item.role)
      && typeof item.content === 'string'
    )).slice(-20);
  } catch {
    return [];
  }
}

function saveConversation(storageKey, conversation) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(conversation));
  } catch {
    // localStorageが無効でも、現在の画面内では会話を継続する。
  }
}
