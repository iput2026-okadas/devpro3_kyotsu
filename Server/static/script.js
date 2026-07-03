document.addEventListener('DOMContentLoaded', () => {
  // HTML側から引き渡されたグローバル変数を参照
  const COLUMNS = window.CSV_COLUMNS || [];
  const ROWS = window.CSV_ROWS || [];
  const SELECTED_FILE = window.SELECTED_FILE;

  let sortedRows = [...ROWS];
  let sortCol = null;
  let sortDir = 1; // 1 = 昇順, -1 = 降順

  // テーブルのデータをレンダリングする関数
  function renderTable(rowsList) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';
    
    rowsList.forEach(r => {
      const tr = document.createElement('tr');
      COLUMNS.forEach(col => {
        const td = document.createElement('td');
        td.textContent = r[col] !== undefined ? r[col] : '';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    document.getElementById('stats').textContent = `表示中: ${rowsList.length} / 全 ${ROWS.length} 件`;
  }

  // ソート処理を行う関数
  function sortRowsData() {
    if (!sortCol) return;
    sortedRows.sort((a, b) => {
      const va = a[sortCol];
      const vb = b[sortCol];
      const na = Number(String(va).replace(/,/g, ''));
      const nb = Number(String(vb).replace(/,/g, ''));
      
      if (Number.isFinite(na) && Number.isFinite(nb)) {
        return (na - nb) * sortDir;
      }
      return String(va).localeCompare(String(vb), undefined, { numeric: true }) * sortDir;
    });
  }

  // ソートインジケーター（▲▼記号）の表示を更新する関数
  function updateSortIndicators() {
    document.querySelectorAll('#table-header th').forEach(th => {
      const col = th.getAttribute('data-col');
      const icon = th.querySelector('.sort-icon');
      if (col === sortCol) {
        icon.textContent = sortDir === 1 ? ' ▲' : ' ▼';
        icon.style.color = 'var(--accent)';
      } else {
        icon.textContent = ' ↕';
        icon.style.color = '#94a3b8';
      }
    });
  }

  // ヘッダー要素の初期化とイベント設定
  function initHeader() {
    const thr = document.getElementById('table-header');
    thr.innerHTML = '';
    COLUMNS.forEach(col => {
      const th = document.createElement('th');
      th.setAttribute('data-col', col);
      th.innerHTML = `${col}<span class="sort-icon"> ↕</span>`;
      th.addEventListener('click', () => {
        if (sortCol === col) {
          sortDir = -sortDir;
        } else {
          sortCol = col;
          sortDir = 1;
        }
        sortRowsData();
        updateSortIndicators();
        renderTable(sortedRows);
      });
      thr.appendChild(th);
    });
  }

  // エクスポート用のCSV文字列生成
  function toCSV(rows) {
    const esc = v => `"${String(v || '').replace(/"/g, '""')}"`;
    const header = COLUMNS.map(esc).join(',');
    const body = rows.map(r => COLUMNS.map(c => esc(r[c])).join(',')).join('\n');
    return header + '\n' + body;
  }

  // CSVダウンロードボタンイベント
  document.getElementById('download').addEventListener('click', () => {
    const csv = toCSV(sortedRows);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = SELECTED_FILE || 'export.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
  });

  // JSONエクスポートボタンイベント
  document.getElementById('export-json').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(sortedRows, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const filename = SELECTED_FILE || 'export.json';
    a.download = filename.replace('.csv', '.json');
    document.body.appendChild(a);
    a.click();
    a.remove();
  });

  // 初期実行
  if (COLUMNS.length > 0) {
    initHeader();
    updateSortIndicators();
    renderTable(sortedRows);
  }
});