const api = {
  async getTransactions() {
    const r = await fetch('/transactions');
    if (!r.ok) throw new Error('Failed to load transactions');
    return r.json();
  },
  async getSummary() {
    const r = await fetch('/transactions/summary');
    if (!r.ok) throw new Error('Failed to load summary');
    return r.json();
  },
  async createTransaction(payload) {
    const r = await fetch('/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) throw new Error('Failed to create transaction');
    return r.json();
  },
  async deleteTransaction(id) {
    const r = await fetch(`/transactions/${id}`, { method: 'DELETE' });
    if (!r.ok) throw new Error('Failed to delete transaction');
  },
};

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

function fmt(amount) {
  return '£' + Number(amount).toFixed(2);
}

function renderSummary(data) {
  const el = document.getElementById('summary');
  if (data.total === 0) {
    el.innerHTML = '<p class="summary-empty">No expenses yet.</p>';
    return;
  }
  const rows = Object.entries(data.by_category)
    .sort((a, b) => b[1] - a[1])
    .map(([cat, amt]) => `
      <li class="category-row">
        <span class="category-name">${cat}</span>
        <span class="category-amount">${fmt(amt)}</span>
      </li>`)
    .join('');
  el.innerHTML = `
    <p class="summary-total">${fmt(data.total)}</p>
    <ul class="category-list">${rows}</ul>`;
}

function renderTransactions(txs) {
  const el = document.getElementById('transactions');
  if (txs.length === 0) {
    el.innerHTML = '<p class="tx-empty">No transactions yet. Add one above.</p>';
    return;
  }
  const rows = [...txs].reverse().map(tx => `
    <tr>
      <td>${escapeHtml(tx.description)}</td>
      <td><span class="tx-category">${escapeHtml(tx.category)}</span></td>
      <td class="tx-amount">${escapeHtml(fmt(tx.amount))}</td>
      <td>
        <button class="btn-delete" data-id="${tx.id}" title="Delete">&#x2715;</button>
      </td>
    </tr>`).join('');
  el.innerHTML = `
    <table class="tx-table">
      <thead>
        <tr>
          <th>Description</th>
          <th>Category</th>
          <th>Amount</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  el.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = Number(btn.dataset.id);
      const td = btn.parentElement;

      const confirmEl = document.createElement('span');
      confirmEl.className = 'confirm-delete';
      confirmEl.innerHTML =
        '<button class="btn-confirm">Confirm?</button>' +
        '<button class="btn-cancel">Cancel</button>';
      td.replaceChild(confirmEl, btn);

      const timer = setTimeout(() => td.replaceChild(btn, confirmEl), 4000);

      confirmEl.querySelector('.btn-cancel').addEventListener('click', () => {
        clearTimeout(timer);
        td.replaceChild(btn, confirmEl);
      });

      confirmEl.querySelector('.btn-confirm').addEventListener('click', async () => {
        clearTimeout(timer);
        try {
          await api.deleteTransaction(id);
          await refresh();
        } catch {
          td.replaceChild(btn, confirmEl);
        }
      });
    });
  });
}

async function refresh() {
  const [txs, summary] = await Promise.all([
    api.getTransactions(),
    api.getSummary(),
  ]);
  renderTransactions(txs);
  renderSummary(summary);
}

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('toast-visible'));
  setTimeout(() => {
    toast.classList.remove('toast-visible');
    toast.addEventListener('transitionend', () => toast.remove());
  }, 2500);
}

document.getElementById('add-form').addEventListener('submit', async e => {
  e.preventDefault();
  const errEl = document.getElementById('form-error');
  errEl.classList.add('hidden');

  const amount = parseFloat(document.getElementById('amount').value);
  const description = document.getElementById('description').value.trim();
  const category = document.getElementById('category').value.trim().toLowerCase();

  if (!amount || amount <= 0 || !description || !category) {
    errEl.textContent = 'Please fill in all fields with valid values.';
    errEl.classList.remove('hidden');
    return;
  }

  const btn = e.target.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.textContent = 'Adding…';

  try {
    await api.createTransaction({ amount, description, category });
    e.target.reset();
    await refresh();
    showToast('Expense added');
  } catch {
    errEl.textContent = 'Failed to add expense. Please try again.';
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Add Expense';
  }
});

refresh();
